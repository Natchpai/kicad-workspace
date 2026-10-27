#!/usr/bin/env python3
"""Build a branded engineering-report PDF from a Markdown file.

Usage:
    python build_report.py report.md out.pdf
    python build_report.py report.md out.pdf --cover on    # override the cover key for this build
    python build_report.py report.md --show-theme          # resolved theme and the source of each key

See ../SKILL.md for the Markdown dialect (front matter, equations, figures, tables, notes).
Page geometry, the header, footer and cover page, and fixed words live in page_layout.py.
Requires: pip install -r requirements.txt  (reportlab, matplotlib, svglib, pillow, numpy, fonttools).
Fonts (IBM Plex Sans and Mono, DejaVu Sans fallback) are bundled in ../assets/fonts, so it runs the same on Linux, macOS and Windows.
"""
import argparse, hashlib, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, ListFlowable,
                                ListItem, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle, XPreformatted)

try:
    import svglib  # noqa: F401 (page_layout draws SVG with it)
except ImportError:
    sys.exit("svglib missing: pip install -r requirements.txt (in the skill folder)")

os.environ["REPORT_FIGS_SKILL_THEME_ONLY"] = "1"  # see report_figs.default_layers
import report_figs
import page_layout  # registers the fonts (Sans, Sans-Bold, Mono, Fallback) on import
from page_layout import LABELS, LAYOUT, MONO_CMAP, with_fallback

# ---------------------------------------------------------------- theme
# Colours, logo and switches come from report_figs.load_theme() (theme.yml, report-theme.yml,
# front matter). apply_theme() fills TH and SS before a report is parsed.
TH = {}                                 # resolved theme of the report being built
SS = {}                                 # paragraph styles built from TH
SUB = '<sub rise="20%" size="72%">'     # ReportLab's default drops a subscript by half the font size
SUP = '<super rise="38%" size="72%">'
EQ_NUM_W = 14 * mm                      # width of the equation-number column (and its mirror on the left)
EQ_SIZE = 11.5                          # display equation font size in pt (body text is 10 pt)


def C(key):
    return colors.HexColor(TH[key])


def apply_theme(th):
    TH.clear(); TH.update(th)
    ink, muted, head = C("text_color"), C("muted_color"), C("heading_color")
    SS.clear(); SS.update({
        "title": ParagraphStyle("title", fontName="Sans-Bold", fontSize=19, leading=24, textColor=C("title_color"), spaceAfter=3),
        "subtitle": ParagraphStyle("subtitle", fontName="Sans", fontSize=11.5, leading=15, textColor=muted, spaceAfter=4),
        "meta": ParagraphStyle("meta", fontName="Sans", fontSize=9, leading=12, textColor=muted, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName="Sans-Bold", fontSize=13.5, leading=18, textColor=head, spaceBefore=16, spaceAfter=6, keepWithNext=1),
        "h3": ParagraphStyle("h3", fontName="Sans-Bold", fontSize=11, leading=15, textColor=head, spaceBefore=10, spaceAfter=4, keepWithNext=1),
        "h4": ParagraphStyle("h4", fontName="Sans-Bold", fontSize=10, leading=14, textColor=C("accent_dark"), spaceBefore=8, spaceAfter=3, keepWithNext=1),
        "body": ParagraphStyle("body", fontName="Sans", fontSize=10, leading=14.8, textColor=ink, spaceAfter=6.5),
        "cell": ParagraphStyle("cell", fontName="Sans", fontSize=9, leading=12.4, textColor=ink),
        "cellh": ParagraphStyle("cellh", fontName="Sans-Bold", fontSize=9, leading=12.4, textColor=ink),
        "cap": ParagraphStyle("cap", fontName="Sans", fontSize=8.5, leading=11.5, textColor=muted,
                              alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
        "tcap": ParagraphStyle("tcap", fontName="Sans", fontSize=8.5, leading=11.5, textColor=muted, spaceBefore=4, spaceAfter=4,
                               keepWithNext=1),
        "code": ParagraphStyle("code", fontName="Mono", fontSize=8.3, leading=11.2, textColor=ink),
        "note": ParagraphStyle("note", fontName="Sans", fontSize=9.4, leading=13.6, textColor=ink),
        "eqno": ParagraphStyle("eqno", fontName="Sans", fontSize=9.5, leading=12, textColor=muted, alignment=TA_RIGHT),
    })


# ---------------------------------------------------------------- inline markup
class Inline:
    def __init__(self, auto_subs, italic_phrases):
        self.subs = sorted({s for s in auto_subs if len(s) >= 2}, key=len, reverse=True)
        self.re = (re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, self.subs)) + r")(?![A-Za-z0-9])")
                   if self.subs else None)
        self.italic = italic_phrases

    def __call__(self, t, italic_phrases=True):
        t = t.replace("\\|", "|").replace("\\*", "\u0000AST\u0000").replace("\\_", "\u0000US\u0000")
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        codes, urls = [], []  # kept out of the markup passes below, put back at the end
        t = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or f"\u0000C{len(codes) - 1}\u0000", t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: urls.append(m.group(2)) or
                   f'<link href="\u0000U{len(urls) - 1}\u0000" color="{TH["accent_color"]}"><u>{m.group(1)}</u></link>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", t)
        t = re.sub(r"_\{([^}]*)\}", SUB + r"\1</sub>", t)
        t = re.sub(r"\^\{([^}]*)\}", SUP + r"\1</super>", t)
        if self.re:
            t = self.re.sub(lambda m: f"{m.group(1)[0]}{SUB}{m.group(1)[1:]}</sub>", t)
        if italic_phrases:
            for ph in self.italic:
                t = t.replace(ph, f"<i>{ph}</i>")
        t = with_fallback(t.replace("\u0000AST\u0000", "*").replace("\u0000US\u0000", "_"))
        t = re.sub(r"\u0000U(\d+)\u0000", lambda m: urls[int(m.group(1))], t)
        return re.sub(r"\u0000C(\d+)\u0000",  # code: Plex Mono lacks some glyphs Plex Sans has (\u03a9)
                      lambda m: f'<font name="Mono">{with_fallback(codes[int(m.group(1))], MONO_CMAP)}</font>', t)


# ---------------------------------------------------------------- flowables
class Svg(Flowable):
    def __init__(self, path, width=None, scale=None):
        super().__init__()
        self.d = page_layout.load_svg(path)
        self.s = scale if scale else width / self.d.width
        self.w, self.h = self.d.width * self.s, self.d.height * self.s
        self.hAlign = "CENTER"

    def wrap(self, aw, ah):
        if self.w > aw:
            self.s *= aw / self.w
            self.w, self.h = self.d.width * self.s, self.d.height * self.s
        return self.w, self.h

    def draw(self):
        from reportlab.graphics import renderPDF
        self.canv.saveState(); self.canv.scale(self.s, self.s)
        renderPDF.draw(self.d, self.canv, 0, 0); self.canv.restoreState()


class TitleRule(Flowable):
    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 10

    def draw(self):
        c = self.canv  # same full-width line as the header rule above the title
        c.setStrokeColor(colors.HexColor(TH["header_rule_color"]))
        c.setLineWidth(LAYOUT.rule_w); c.line(0, 6, self.aw, 6)


def panel(content, tw, pad=7, number=None):
    """Equation or code panel, drawn per eq_style: panel = tint + bar, bar = bar only, plain = neither.
    With `number`, an equation number sits on the right and an equal empty column on the left
    keeps the content centred."""
    if number is None:
        t = Table([[content]], colWidths=[tw])
    else:
        t = Table([["", content, Paragraph(f"({number})", SS["eqno"])]],
                  colWidths=[EQ_NUM_W, tw - 2 * EQ_NUM_W, EQ_NUM_W])
    sty = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]
    if TH["eq_style"] == "panel":
        sty.append(("BACKGROUND", (0, 0), (-1, -1), C("eq_fill")))
    if TH["eq_style"] in ("panel", "bar"):
        sty.append(("LINEBEFORE", (0, 0), (0, -1), 2.2, C("eq_color")))
    t.setStyle(TableStyle(sty))
    t.spaceBefore, t.spaceAfter = 3, 8
    return t


def note_box(content, tw):
    """Outlined white box, so a note never looks like an equation panel."""
    t = Table([[content]], colWidths=[tw])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, C("hairline")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    t.spaceBefore, t.spaceAfter = 3, 9
    return t


def cap_label(kind, n):
    return f'<font name="Sans-Bold" color="{TH["text_color"]}">{LABELS[kind]} {n}.</font>&nbsp; '


# ---------------------------------------------------------------- builder
class Report:
    def __init__(self, md_path, meta, tw, workdir, line0=0):
        self.base = os.path.dirname(os.path.abspath(md_path))
        self.meta, self.tw, self.work = meta, tw, workdir
        self.line0 = line0  # source lines before the body (front matter), for error messages
        subs = [s.strip() for s in meta.get("subscripts", "").split(",") if s.strip()]
        italic = [s.strip() for s in meta.get("italic_titles", "").split("|") if s.strip()]
        self.inline = Inline(subs, italic)
        self.n_fig = self.n_tab = self.n_eq = 0

    def equation(self, tex):
        numbered = TH["eq_numbers"] and not re.search(r"\\(nonumber|notag)(?![a-zA-Z])", tex)
        tex = re.sub(r"\\(nonumber|notag)(?![a-zA-Z])", "", tex).strip()
        p = os.path.join(self.work, hashlib.md5(tex.encode()).hexdigest() + ".svg")
        max_w = self.tw - 2 * EQ_NUM_W - 8 * mm
        try:
            if not os.path.exists(p):
                report_figs.equation(tex, p, size=EQ_SIZE, color=TH["text_color"])
            e = Svg(p, scale=1.0)
            if e.w > max_w:
                e = Svg(p, width=max_w)
        except Exception as ex:  # mathtext could not parse: show the source rather than fail
            print(f"WARNING: equation not rendered ({ex.__class__.__name__}): {tex}", file=sys.stderr)
            e = Preformatted(tex, SS["code"])
        if numbered:
            self.n_eq += 1
        return panel(e, self.tw, number=self.n_eq if numbered else None)

    def figure(self, path, cap, width_pct, line):
        src = path
        path = path if os.path.isabs(path) else os.path.join(self.base, path)
        if not os.path.isfile(path):
            sys.exit(f"Figure not found: {src} (line {line}; paths are relative to the Markdown file)")
        w = self.tw * (width_pct / 100.0)
        if path.lower().endswith(".svg"):
            img = Svg(path, width=w)
        else:
            iw, ih = page_layout.image_size(path)
            img = Image(path, width=w, height=w * ih / iw)
        parts = [Spacer(1, 2), img]
        if cap:
            self.n_fig += 1
            parts.append(Paragraph(cap_label("figure", self.n_fig) + self.inline(cap), SS["cap"]))
        else:
            parts.append(Spacer(1, 8))
        return KeepTogether(parts)

    def table(self, rows, caption):
        """Flowables for one table (a list; empty, with a warning, if the table has no rows)."""
        if not rows:
            print(f"WARNING: table with no rows skipped{f' ({caption})' if caption else ''}", file=sys.stderr)
            return []
        n = max(len(r) for r in rows)
        rows = [r + [""] * (n - len(r)) for r in rows]
        data = [[Paragraph(self.inline(c), SS["cellh"] if i == 0 else SS["cell"]) for c in r]
                for i, r in enumerate(rows)]
        lens = [max(6, max(len(r[j]) for r in rows)) for j in range(n)]
        full = sum(lens) > 60 or n > 2
        tw = self.tw if full else min(self.tw, 95 * mm)
        # Column widths: each column gets at least its longest unbreakable token (a number keeps its
        # unit: "0.11 W"), then the space left goes to the columns with the most text.
        def text_w(s, font):
            return pdfmetrics.stringWidth(re.sub(r"\*\*|\\|_\{|\}", "", s), font, SS["cell"].fontSize) + 12
        fonts = ["Sans-Bold"] + ["Sans"] * (len(rows) - 1)
        lo = [max(text_w(tok, f) for r, f in zip(rows, fonts) for tok in re.split(r"(?<![\d.]) ", r[j]))
              for j in range(n)]
        hi = [max(text_w(r[j], f) for r, f in zip(rows, fonts)) for j in range(n)]
        if sum(hi) <= tw or sum(lo) >= tw:
            base = hi if sum(hi) <= tw else lo
            cw = [tw * b / sum(base) for b in base]
        else:
            k = (tw - sum(lo)) / (sum(hi) - sum(lo))
            cw = [l + k * (h - l) for l, h in zip(lo, hi)]
        t = Table(data, colWidths=cw, hAlign="LEFT", repeatRows=1)
        sty = [("BACKGROUND", (0, 0), (-1, 0), C("tint")), ("LINEBELOW", (0, 0), (-1, 0), 1.0, C("accent_color")),
               ("LINEBELOW", (0, 1), (-1, -1), 0.4, C("hairline")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
               ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
        sty += [("BACKGROUND", (0, i), (-1, i), C("tint_light")) for i in range(2, len(data), 2)]
        t.setStyle(TableStyle(sty))
        t.spaceBefore, t.spaceAfter = 2, 10
        parts = []
        if caption:
            self.n_tab += 1
            parts.append(Paragraph(cap_label("table", self.n_tab) + self.inline(caption), SS["tcap"]))
        parts.append(t)
        return [KeepTogether(parts)] if len(rows) <= 10 else parts

    def lst(self, items, ordered, start=1):
        fl = [ListItem(Paragraph(self.inline(x), SS["body"]), leftIndent=16) for x in items]
        kw = dict(bulletFontName="Sans-Bold", bulletFontSize=9.4, bulletColor=C("number_color"), leftIndent=16)
        if ordered:
            f = ListFlowable(fl, bulletType="1", start=start, bulletFormat="%s.", **kw)
        else:
            f = ListFlowable(fl, bulletType="bullet", start="\u2022", **kw)
        f._md_items, f._md_ordered, f._md_start = items, ordered, start  # bind_blocks() may split off the last item
        f._lead_in = items[-1].rstrip().endswith(":")
        return f

    def title_block(self, title):
        m = self.meta
        out = [Paragraph(self.inline(title, False), SS["title"])]
        if m.get("subtitle"):
            out.append(Paragraph(self.inline(m["subtitle"], False), SS["subtitle"]))
        bits = [x for x in (TH["author"], m.get("date")) if x]
        if m.get("doc_no"):
            bits.append(LABELS["doc_no"].format(doc_no=m["doc_no"]))
        if m.get("revision"):
            bits.append(LABELS["rev"].format(revision=m["revision"]))
        if bits:
            esc = " \u00b7 ".join(bits).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append(Paragraph(with_fallback(esc), SS["meta"]))
        out.append(TitleRule() if TH["title_rule"] and TH["header_rule_color"] else Spacer(1, 4))
        return out

    def parse(self, body):
        L = body.split("\n")
        story, i, title_done = [], 0, False
        para = []

        def flush():
            if para:
                text = " ".join(para)
                p = Paragraph(self.inline(text), SS["body"])
                p._lead_in = text.rstrip().endswith(":")
                story.append(p)
                para.clear()

        while i < len(L):
            s = L[i].strip()
            if not s:
                flush(); i += 1; continue
            if s.startswith("# ") and not title_done:
                flush(); story += self.title_block(s[2:]); title_done = True; i += 1; continue
            if not title_done and self.meta.get("title"):
                story += self.title_block(self.meta["title"]); title_done = True
            if s in ("\\pagebreak", "<!-- pagebreak -->"):
                flush(); story.append(PageBreak()); i += 1; continue
            hm = re.match(r"^(#{2,4}) (.*)", s)
            if hm:
                flush()
                txt = re.sub(r"^(\d+(?:\.\d+)*\.?)\s+",  # section number in number_color
                             lambda m: f'<font color="{TH["number_color"]}">{m.group(1)}</font>&nbsp;&nbsp;',
                             self.inline(hm.group(2), False))
                story.append(Paragraph(txt, SS["h" + str(len(hm.group(1)))]))
                i += 1; continue
            if s.startswith("```"):
                flush(); lang = s[3:].strip().lower(); j = i + 1; buf = []
                while j < len(L) and not L[j].strip().startswith("```"):
                    buf.append(L[j]); j += 1
                if lang in ("latex", "math", "tex"):
                    for eq in [e for e in "\n".join(buf).split("\n\n") if e.strip()]:
                        story.append(self.equation(" ".join(eq.split("\n"))))
                else:
                    code = "\n".join(buf).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(panel(XPreformatted(with_fallback(code, MONO_CMAP), SS["code"]), self.tw, pad=6))  # Plex Mono lacks Ω, µ
                i = j + 1; continue
            if s.startswith("$$"):
                flush(); buf = [s[2:]]; j = i
                while not buf[-1].rstrip().endswith("$$"):
                    j += 1
                    if j >= len(L):
                        sys.exit(f"Unclosed $$ starting at line {self.line0 + i + 1}")
                    buf.append(L[j].strip())
                tex = " ".join(buf).rstrip()[:-2]
                story.append(self.equation(tex)); i = j + 1; continue
            im = re.match(r"^!\[(.*?)\]\((.+?)\)(\{width=(\d+)%\})?$", s)
            if im:
                flush(); story.append(self.figure(im.group(2), im.group(1), int(im.group(4) or 88), self.line0 + i + 1))
                i += 1; continue
            cap, j = None, i
            if s.startswith("Table:") and i + 1 < len(L):
                cap, j = s[6:].strip(), i + 1
                while j < len(L) and not L[j].strip():
                    j += 1
            if j < len(L) and L[j].strip().startswith("|"):
                flush(); first, rows = j, []
                while j < len(L) and L[j].strip().startswith("|"):
                    r = L[j].strip()
                    if not (j == first + 1 and re.match(r"^\|[\s:|-]+\|?$", r)):  # header separator: 2nd row only
                        rows.append([c.strip() for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))])
                    j += 1
                i = j
                story += self.table(rows, cap)
                continue
            if s.startswith(">"):
                flush(); buf = []
                while i < len(L) and L[i].strip().startswith(">"):
                    buf.append(L[i].strip()[1:].strip()); i += 1
                text = " ".join(buf)
                label = "" if text.startswith("**") else f'<font name="Sans-Bold" color="{TH["accent_dark"]}">{LABELS["note"]}</font>&nbsp; '
                story.append(note_box(Paragraph(label + self.inline(text), SS["note"]), self.tw))
                continue
            om = re.match(r"^(\d+)[.)] (.*)", s)
            if om:
                flush(); start = int(om.group(1)); items = []
                while i < len(L) and re.match(r"^\d+[.)] ", L[i].strip()):
                    items.append(re.sub(r"^\d+[.)] ", "", L[i].strip())); i += 1
                    while i < len(L) and L[i].startswith("   ") and L[i].strip() and not re.match(r"^\d+[.)] ", L[i].strip()):
                        items[-1] += " " + L[i].strip(); i += 1
                story.append(self.lst(items, True, start)); continue
            if re.match(r"^[-*] ", s):
                flush(); items = []
                while i < len(L) and re.match(r"^[-*] ", L[i].strip()):
                    items.append(L[i].strip()[2:]); i += 1
                    while i < len(L) and L[i].startswith("  ") and L[i].strip() and not re.match(r"^[-*] ", L[i].strip()):
                        items[-1] += " " + L[i].strip(); i += 1
                story.append(self.lst(items, False)); continue
            para.append(s); i += 1
        flush()
        if not title_done and self.meta.get("title"):
            story = self.title_block(self.meta["title"]) + story
        return self.bind_blocks(story)

    def bind_blocks(self, story):
        """Keep a lead-in that ends with ':' on the same page as the equation, figure, table or
        code block after it. For a list, only its last item moves with the block."""
        is_block = lambda f: isinstance(f, (Table, KeepTogether, Preformatted)) or \
            (isinstance(f, Paragraph) and f.style.name == "tcap")
        out, i = [], 0
        while i < len(story):
            f = story[i]
            if getattr(f, "_lead_in", False) and i + 1 < len(story) and is_block(story[i + 1]):
                nxt = story[i + 1]
                if isinstance(f, ListFlowable) and len(f._md_items) > 1:
                    head = f._md_items[:-1]
                    out.append(self.lst(head, f._md_ordered, f._md_start))
                    f = self.lst(f._md_items[-1:], f._md_ordered, f._md_start + len(head))
                out.append(KeepTogether([f] + (nxt._content if isinstance(nxt, KeepTogether) else [nxt])))
                i += 2
            else:
                out.append(f); i += 1
        return self.bind_headings(out)

    @staticmethod
    def bind_headings(story):
        """Never leave a heading at the foot of a page: glue it (and a following lead
        paragraph) to the next block."""
        out, i = [], 0
        is_head = lambda f: isinstance(f, Paragraph) and f.style.name in ("h2", "h3", "h4")
        while i < len(story):
            f = story[i]
            if is_head(f) and i + 1 < len(story):
                group = [f]
                j = i + 1
                while j < len(story) and is_head(story[j]):
                    group.append(story[j]); j += 1
                if j < len(story):
                    nxt = story[j]
                    group += nxt._content if isinstance(nxt, KeepTogether) else [nxt]
                    if isinstance(nxt, Paragraph) and j + 1 < len(story) and not is_head(story[j + 1]):
                        nn = story[j + 1]
                        if isinstance(nn, KeepTogether):
                            group += nn._content; j += 1
                out.append(KeepTogether(group)); i = j + 1
            else:
                out.append(f); i += 1
        return out


def make_canvas(meta, page_w, page_h, cover=False):
    """Canvas class that draws the header and footer on every page once the page count is known.
    With a cover, the first page gets neither and "Page 1 of N" starts on the page after it."""
    th, skip = dict(TH), 1 if cover else 0
    short, left_foot = page_layout.short_title(meta), page_layout.left_footer(th, meta)

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k); self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__)); self._startPage()

        def save(self):
            n = len(self._saved) - skip
            for i, st in enumerate(self._saved):
                self.__dict__.update(st)
                if i >= skip:
                    page_layout.draw_header_footer(self, th, page_w, page_h, short, left_foot,
                                                   LABELS["page"].format(n=i + 1 - skip, total=n))
                super().showPage()
            super().save()
    return NumberedCanvas


def read_front_matter(md):
    meta = {}
    md = md.lstrip("﻿")
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end > 0:
            meta = report_figs.parse_kv(md[3:end])
            md = md[end + 4:]
    return meta, md


def theme_layers(md_path, meta):
    """The theme layers a Markdown file adds above the skill theme: the file named by `theme:` in
    its front matter, or report-theme.yml next to it, then its front matter."""
    base = os.path.dirname(os.path.abspath(md_path))
    layers = []
    proj = meta.get("theme")
    if proj:
        proj = proj if os.path.isabs(proj) else os.path.join(base, proj)
        if not os.path.exists(proj):
            sys.exit(f"Theme error: theme file not found: {proj} (theme: in the front matter)")
    elif os.path.exists(os.path.join(base, report_figs.PROJECT_THEME)):
        proj = os.path.join(base, report_figs.PROJECT_THEME)
    if proj:
        proj = os.path.normpath(proj)
        layers.append((proj, os.path.dirname(proj), report_figs.read_theme_file(proj)))
    layers.append((f"front matter of {os.path.basename(md_path)}", base, meta))
    return layers


def report_theme(md_path, meta, base_layers=()):
    """Resolved theme of one report: skill theme.yml, then base_layers (a book passes its own
    layers), then the report's theme_layers(). A theme file already in base_layers is used once."""
    default = (report_figs.DEFAULT_THEME, report_figs.SKILL_DIR, report_figs.read_theme_file(report_figs.DEFAULT_THEME))
    seen = {name for name, _, _ in base_layers}
    own = [l for l in theme_layers(md_path, meta) if l[0] not in seen]
    return report_figs.load_theme([default, *base_layers, *own])


def show_theme(th, src):
    def short(p):
        if p == report_figs.DEFAULT_THEME:
            return "skill theme.yml"
        if os.path.isabs(p) and os.path.normcase(p).startswith(os.path.normcase(report_figs.SKILL_DIR) + os.sep):
            return "skill " + os.path.relpath(p, report_figs.SKILL_DIR).replace(os.sep, "/")
        try:
            return os.path.relpath(p) if os.path.isabs(p) else p
        except ValueError:  # other drive on Windows
            return p
    for k in report_figs.THEME_KEYS:
        v = th[k]
        v = "on" if v is True else "off" if v is False else "none" if v is None else v
        if k == "logo" and th[k]:
            v = "skill assets/logo.png" if os.path.samefile(v, os.path.join(report_figs.SKILL_DIR, "assets", "logo.png")) else short(v)
        if k == "cover_logo":
            v = "none" if th[k] == "" else short(th[k]) if th[k] else f"(auto: {short(page_layout.cover_logo(th) or 'none')})"
        if k == "footer" and not v:
            v = "(author · date)"
        print(f"{k:18} {v!s:24} {short(src[k])}")


def build(md_path, out_pdf, cover=None, base_layers=()):
    """Build one report. cover=None follows the `cover` theme key; True or False overrides it (a
    book passes False). base_layers sit between the skill theme and the report's own theme."""
    md = open(md_path, encoding="utf-8-sig").read()
    meta, body = read_front_matter(md)
    th, _ = report_theme(md_path, meta, base_layers)
    apply_theme(th)
    cover = th["cover"] if cover is None else cover
    line0 = md[:len(md) - len(body)].count("\n")
    paper = page_layout.parse_paper(meta, f"front matter of {os.path.basename(md_path)}")
    W, H = paper
    L = LAYOUT
    tw = W - L.margin_l - L.margin_r
    with tempfile.TemporaryDirectory(prefix="report_eq_") as work:  # equation SVGs, deleted after the build
        rep = Report(md_path, meta, tw, work, line0)
        story = rep.parse(body)
    title = meta.get("title") or next((l[2:] for l in body.split("\n") if l.startswith("# ")), "Report")
    meta.setdefault("title", title)
    doc = BaseDocTemplate(out_pdf, pagesize=paper, leftMargin=L.margin_l, rightMargin=L.margin_r,
                          topMargin=L.margin_t, bottomMargin=L.margin_b, title=title, author=TH["author"])
    frame = Frame(L.margin_l, L.margin_b, tw, H - L.margin_t - L.margin_b,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    templates = [PageTemplate(id="p", frames=[frame])]
    if cover:  # the cover is drawn by its page template; the story starts on the next page
        th_cover = dict(TH)
        rows = [(LABELS["document"], meta.get("doc_no")), (LABELS["revision"], meta.get("revision")),
                (LABELS["date"], meta.get("date")), (LABELS["author"], TH["author"])]
        templates.insert(0, PageTemplate(id="cover", frames=[frame], onPage=lambda c, d:
                                         page_layout.draw_cover(c, th_cover, meta, W, H, rows)))
        story = [NextPageTemplate("p"), PageBreak()] + story
    doc.addPageTemplates(templates)
    doc.build(story, canvasmaker=make_canvas(meta, W, H, cover))
    print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown"); ap.add_argument("output", nargs="?")
    ap.add_argument("--show-theme", action="store_true", help="print the resolved theme and where each key came from, then exit")
    ap.add_argument("--cover", choices=("on", "off"), help="cover page on or off for this build (default: the cover key)")
    a = ap.parse_args()
    if a.show_theme:
        show_theme(*report_theme(a.markdown, read_front_matter(open(a.markdown, encoding="utf-8-sig").read())[0]))
    elif a.output:
        build(a.markdown, a.output, cover=None if a.cover is None else a.cover == "on")
    else:
        ap.error("give an output PDF path, or --show-theme")
