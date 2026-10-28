#!/usr/bin/env python3
"""Build a branded engineering-report PDF from a Markdown file.

Usage:
    python build_report.py report.md out.pdf                     # cover, contents, report (pages: full)
    python build_report.py report.md out.pdf --pages content     # the report only (or cover: cover + report)
    python build_report.py report.md out.pdf --set eq_style=bar --set header=off
    python build_report.py report.md out.pdf --strict --preview preview
    python build_report.py report.md --show-theme                # resolved theme and the source of each key

--set KEY=VALUE takes any theme or front-matter key for this build only, above every file.
--strict exits with code 1 when the build printed a warning. --preview DIR renders the pages
(--sheet N tiles them N per image).

See ../SKILL.md for the Markdown dialect (front matter, equations, figures, tables, notes).
Sizes, distances, the header, footer and cover page, and fixed words live in page_layout.py.
Requires: pip install -r requirements.txt  (reportlab, matplotlib, svglib, pillow, numpy, fonttools).
Fonts (IBM Plex Sans and Mono, DejaVu Sans fallback) are bundled in ../assets/fonts, so it runs the same on Linux, macOS and Windows.
"""
import argparse, hashlib, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
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
from page_layout import BLOCKS, LABELS, LAYOUT, MONO_CMAP, STYLES, warn, with_fallback

# ---------------------------------------------------------------- theme
# Colours, logo and switches come from report_figs.load_theme() (theme.yml, report-theme.yml,
# front matter, --set). apply_theme() fills TH and SS before a report is parsed.
TH = {}                                 # resolved theme of the report being built
SS = {}                                 # paragraph styles built from TH and page_layout.STYLES
B = BLOCKS
SUB = f'<sub rise="{B.sub_rise}" size="{B.script_size}">'   # ReportLab's default drops a subscript by half the font size
SUP = f'<super rise="{B.sup_rise}" size="{B.script_size}">'
EQ_LANGS = ("latex", "math", "tex")     # fenced blocks that hold equations
NONUMBER = r"\\(nonumber|notag)(?![a-zA-Z])"
LABEL = r"\\label\{([^}]*)\}"           # \label{key} in an equation ...
REF = r"\(@([\w:.-]+)\)"                # ... and (@key) in the text becomes its number, (3)
EQ_CITE = r"\b(?:Eqs?\.|Equations?)\s*\((?:(\d+)\.)?(\d+)\)"   # a number written by hand, (7) or (3.7), checked against the count
CMDLINE = "command line (--set)"


def C(key):
    return colors.HexColor(TH[key])


def apply_theme(th):
    TH.clear(); TH.update(th)
    ink, muted, head = C("text_color"), C("muted_color"), C("heading_color")
    color = dict(title=C("title_color"), h2=head, h3=head, h4=C("accent_dark"),
                 **{k: muted for k in ("subtitle", "meta", "cap", "tcap", "eqno")})
    extra = dict(h2=dict(keepWithNext=1), h3=dict(keepWithNext=1), h4=dict(keepWithNext=1),
                 tcap=dict(keepWithNext=1), cap=dict(alignment=TA_CENTER), eqno=dict(alignment=TA_RIGHT))
    SS.clear()
    for name, s in STYLES.items():
        SS[name] = ParagraphStyle(name, fontName=s["font"], fontSize=s["size"], leading=s["leading"],
                                  spaceBefore=s.get("before", 0), spaceAfter=s.get("after", 0),
                                  textColor=color.get(name, ink), **extra.get(name, {}))
    SS["cellh"] = ParagraphStyle("cellh", parent=SS["cell"], fontName="Sans-Bold")


# ---------------------------------------------------------------- inline markup
class Inline:
    def __init__(self, auto_subs, italic_phrases):
        self.subs = sorted({s for s in auto_subs if len(s) >= 2}, key=len, reverse=True)
        self.re = (re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, self.subs)) + r")(?![A-Za-z0-9])")
                   if self.subs else None)
        self.italic = italic_phrases
        self.labels = {}  # equation label -> number, filled by Report.number_equations

    def ref(self, m):
        n = self.labels.get(m.group(1))
        if n is None:
            warn(f"equation label (@{m.group(1)}) not found; printed as (??)")
            return "(??)"
        return f"({n})"

    def __call__(self, t, italic_phrases=True):
        t = re.sub(REF, self.ref, t)
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


# ---------------------------------------------------------------- block readers
# Shared by Report.parse and the equation pre-pass, so both see the same equations in the same order.
def read_fence(L, i, line0):
    """Fenced block opening at line i: (lang, lines inside, index after the closing fence)."""
    lang, j = L[i].strip()[3:].strip().lower(), i + 1
    while j < len(L) and not L[j].strip().startswith("```"):
        j += 1
    if j >= len(L):
        sys.exit(f"Unclosed ``` starting at line {line0 + i + 1}")
    return lang, L[i + 1:j], j + 1


def read_dollars(L, i, line0):
    """$$ ... $$ equation opening at line i: (TeX, index after the closing $$)."""
    buf, j = [L[i].strip()[2:]], i
    while not buf[-1].rstrip().endswith("$$"):
        j += 1
        if j >= len(L):
            sys.exit(f"Unclosed $$ starting at line {line0 + i + 1}")
        buf.append(L[j].strip())
    return " ".join(buf).rstrip()[:-2], j + 1


def split_equations(buf):
    """Equations of a latex block: separated by a blank line, each joined into one line."""
    return [" ".join(eq.split("\n")) for eq in "\n".join(buf).split("\n\n") if eq.strip()]


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
        return aw, B.title_rule_h

    def draw(self):
        c = self.canv  # same full-width line as the header rule above the title
        c.setStrokeColor(colors.HexColor(TH["header_rule_color"]))
        c.setLineWidth(LAYOUT.rule_w); c.line(0, B.title_rule_y, self.aw, B.title_rule_y)


def num_w(number):
    """Width of the equation-number column: B.eq_num_w, or wider for a long number like (3.12)."""
    if number is None:
        return B.eq_num_w
    w = pdfmetrics.stringWidth(f"({number})", SS["eqno"].fontName, SS["eqno"].fontSize)
    return max(B.eq_num_w, w + 2 * B.panel_side + 1)


def panel(content, tw, pad=B.eq_pad, number=None):
    """Equation or code panel, drawn per eq_style: panel = tint + bar, bar = bar only, plain = neither.
    With `number`, an equation number sits on the right and an equal empty column on the left
    keeps the content centred."""
    if number is None:
        t = Table([[content]], colWidths=[tw])
    else:
        nw = num_w(number)
        t = Table([["", content, Paragraph(f"({number})", SS["eqno"])]], colWidths=[nw, tw - 2 * nw, nw])
    sty = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
           ("LEFTPADDING", (0, 0), (-1, -1), B.panel_side), ("RIGHTPADDING", (0, 0), (-1, -1), B.panel_side)]
    if TH["eq_style"] == "panel":
        sty.append(("BACKGROUND", (0, 0), (-1, -1), C("eq_fill")))
    if TH["eq_style"] in ("panel", "bar"):
        sty.append(("LINEBEFORE", (0, 0), (0, -1), B.eq_bar, C("eq_color")))
    t.setStyle(TableStyle(sty))
    t.spaceBefore, t.spaceAfter = B.panel_before, B.panel_after
    return t


def note_box(content, tw):
    """Outlined white box, so a note never looks like an equation panel."""
    t = Table([[content]], colWidths=[tw])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), B.note_line, C("hairline")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), B.note_pad), ("BOTTOMPADDING", (0, 0), (-1, -1), B.note_pad),
        ("LEFTPADDING", (0, 0), (-1, -1), B.note_side), ("RIGHTPADDING", (0, 0), (-1, -1), B.note_side)]))
    t.spaceBefore, t.spaceAfter = B.note_before, B.note_after
    return t


def cap_label(kind, n):
    return f'<font name="Sans-Bold" color="{TH["text_color"]}">{LABELS[kind]} {n}.</font>&nbsp; '


# ---------------------------------------------------------------- builder
class Report:
    def __init__(self, md_path, meta, tw, workdir, line0=0, prefix=None):
        self.base = os.path.dirname(os.path.abspath(md_path))
        self.prefix = prefix  # report number in a book: equations (3.1), Figure 3.1, Table 3.1
        self.meta, self.tw, self.work = meta, tw, workdir
        self.line0 = line0  # source lines before the body (front matter), for error messages
        subs = [s.strip() for s in meta.get("subscripts", "").split(",") if s.strip()]
        italic = [s.strip() for s in meta.get("italic_titles", "").split("|") if s.strip()]
        self.inline = Inline(subs, italic)
        self.n_fig = self.n_tab = self.n_eq = 0

    def num(self, n):
        return f"{self.prefix}.{n}" if self.prefix else str(n)

    def number_equations(self, L):
        """Pre-pass: the number of every \\label{key}, so (@key) works before its equation too, and
        a check of numbers written by hand ("Eq. (7)") against the equation count."""
        n, i, text = 0, 0, []
        while i < len(L):
            s, ln = L[i].strip(), self.line0 + i + 1
            if s.startswith("```"):
                lang, buf, i = read_fence(L, i, self.line0)
                eqs = split_equations(buf) if lang in EQ_LANGS else []
            elif s.startswith("$$"):
                tex, i = read_dollars(L, i, self.line0)
                eqs = [tex]
            else:
                text.append((ln, L[i])); i += 1
                continue
            for tex in eqs:
                numbered = TH["eq_numbers"] and not re.search(NONUMBER, tex)
                n += numbered
                for key in re.findall(LABEL, tex):
                    if not numbered:
                        warn(f"line {ln}: \\label{{{key}}} is on an unnumbered equation; (@{key}) cannot cite it")
                    elif key in self.inline.labels:
                        warn(f"line {ln}: \\label{{{key}}} is used twice; (@{key}) gives the first")
                    else:
                        self.inline.labels[key] = self.num(n)
        for ln, t in text:
            for m in re.finditer(EQ_CITE, t):
                if self.prefix and m.group(1) is None:
                    warn(f"line {ln}: '{m.group(0)}' has no report number, but in the book this report's "
                         f"equations read ({self.prefix}.n) (cite with \\label{{key}} and (@key))")
                elif m.group(1) in (None, self.prefix) and int(m.group(2)) > n:
                    warn(f"line {ln}: '{m.group(0)}' but the report has {n} numbered equations "
                         f"(cite with \\label{{key}} and (@key) to keep numbers right)")

    def equation(self, tex):
        numbered = TH["eq_numbers"] and not re.search(NONUMBER, tex)
        tex = re.sub(LABEL, "", re.sub(NONUMBER, "", tex)).strip()
        p = os.path.join(self.work, hashlib.md5(tex.encode()).hexdigest() + ".svg")
        number = self.num(self.n_eq + 1) if numbered else None
        max_w = self.tw - 2 * num_w(number) - B.eq_room
        try:
            if not os.path.exists(p):
                report_figs.equation(tex, p, size=B.eq_size, color=TH["text_color"])
            e = Svg(p, scale=1.0)
            if e.w > max_w:
                e = Svg(p, width=max_w)
        except Exception as ex:  # mathtext could not parse: show the source rather than fail
            warn(f"equation not rendered ({ex.__class__.__name__}): {tex}")
            e = Preformatted(tex, SS["code"])
        self.n_eq += numbered
        return panel(e, self.tw, number=number)

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
        parts = [Spacer(1, B.fig_before), img]
        if cap:
            self.n_fig += 1
            parts.append(Paragraph(cap_label("figure", self.num(self.n_fig)) + self.inline(cap), SS["cap"]))
        else:
            parts.append(Spacer(1, B.fig_after))
        return KeepTogether(parts)

    def table(self, rows, caption):
        """Flowables for one table (a list; empty, with a warning, if the table has no rows)."""
        if not rows:
            warn(f"table with no rows skipped{f' ({caption})' if caption else ''}")
            return []
        n = max(len(r) for r in rows)
        rows = [r + [""] * (n - len(r)) for r in rows]
        data = [[Paragraph(self.inline(c), SS["cellh"] if i == 0 else SS["cell"]) for c in r]
                for i, r in enumerate(rows)]
        lens = [max(6, max(len(r[j]) for r in rows)) for j in range(n)]
        full = sum(lens) > B.narrow_chars or n > 2
        tw = self.tw if full else min(self.tw, B.narrow_w)
        # Column widths: each column gets at least its longest unbreakable token (a number keeps its
        # unit: "0.11 W"), then the space left goes to the columns with the most text.
        def text_w(s, font):
            return pdfmetrics.stringWidth(re.sub(r"\*\*|\\|_\{|\}", "", s), font, SS["cell"].fontSize) + 2 * B.cell_pad_h
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
        sty = [("BACKGROUND", (0, 0), (-1, 0), C("tint")), ("LINEBELOW", (0, 0), (-1, 0), B.head_line, C("accent_color")),
               ("LINEBELOW", (0, 1), (-1, -1), B.row_line, C("hairline")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
               ("TOPPADDING", (0, 0), (-1, -1), B.cell_pad_v), ("BOTTOMPADDING", (0, 0), (-1, -1), B.cell_pad_v),
               ("LEFTPADDING", (0, 0), (-1, -1), B.cell_pad_h), ("RIGHTPADDING", (0, 0), (-1, -1), B.cell_pad_h)]
        sty += [("BACKGROUND", (0, i), (-1, i), C("tint_light")) for i in range(2, len(data), 2)]
        t.setStyle(TableStyle(sty))
        t.spaceBefore, t.spaceAfter = B.table_before, B.table_after
        parts = []
        if caption:
            self.n_tab += 1
            parts.append(Paragraph(cap_label("table", self.num(self.n_tab)) + self.inline(caption), SS["tcap"]))
        parts.append(t)
        return [KeepTogether(parts)] if len(rows) <= B.table_keep else parts

    def lst(self, items, ordered, start=1):
        fl = [ListItem(Paragraph(self.inline(x), SS["body"]), leftIndent=B.list_indent) for x in items]
        kw = dict(bulletFontName="Sans-Bold", bulletFontSize=B.bullet_size, bulletColor=C("number_color"),
                  leftIndent=B.list_indent)
        if ordered:
            f = ListFlowable(fl, bulletType="1", start=start, bulletFormat="%s.", **kw)
        else:
            f = ListFlowable(fl, bulletType="bullet", start="\u2022", **kw)
        f._md_items, f._md_ordered, f._md_start = items, ordered, start  # bind_blocks() may split off the last item
        f._lead_in = items[-1].rstrip().endswith(":")
        return f

    def title_block(self, title):
        m = self.meta
        num = f'<font color="{TH["number_color"]}">{self.prefix}</font>&nbsp;&nbsp;' if self.prefix else ""
        out = [Paragraph(num + self.inline(title, False), SS["title"])]
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
        out.append(TitleRule() if TH["title_rule"] and TH["header_rule_color"] else Spacer(1, B.title_gap))
        return out

    def parse(self, body):
        L = body.split("\n")
        self.number_equations(L)
        story, i, title_done = [], 0, False
        para = []

        def flush():
            if para:
                text = " ".join(para)
                p = Paragraph(self.inline(text), SS["body"])
                p._lead_in = text.rstrip().endswith(":")
                story.append(p)
                para.clear()

        def nested(k, item_re):
            if re.match(item_re, L[k].strip()):
                warn(f"line {self.line0 + k + 1}: nested list item flattened (only one list level is "
                     f"supported): {L[k].strip()}")

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
                p = Paragraph(txt, SS["h" + str(len(hm.group(1)))])
                if len(hm.group(1)) == 2:
                    p._heading = hm.group(2)  # ReportDoc records its page
                story.append(p)
                i += 1; continue
            if s.startswith("```"):
                flush(); lang, buf, i = read_fence(L, i, self.line0)
                if lang in EQ_LANGS:
                    story += [self.equation(eq) for eq in split_equations(buf)]
                else:
                    code = "\n".join(buf).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(panel(XPreformatted(with_fallback(code, MONO_CMAP), SS["code"]), self.tw, pad=B.code_pad))  # Plex Mono lacks Ω, µ
                continue
            if s.startswith("$$"):
                flush(); tex, i = read_dollars(L, i, self.line0)
                story.append(self.equation(tex)); continue
            im = re.match(r"^!\[(.*?)\]\((.+?)\)(\{width=(\d+(?:\.\d+)?)%\})?$", s)
            if im:
                flush(); story.append(self.figure(im.group(2), im.group(1), float(im.group(4) or B.fig_width), self.line0 + i + 1))
                i += 1; continue
            if s.startswith("!["):
                warn(f"line {self.line0 + i + 1}: image line not understood, printed as text "
                     f"(write ![caption](file.svg) or ![caption](file.svg){{width=NN%}} alone on the line)")
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
                    if L[i][:1].isspace():
                        nested(i, r"^\d+[.)] ")
                    items.append(re.sub(r"^\d+[.)] ", "", L[i].strip())); i += 1
                    while i < len(L) and L[i].startswith("   ") and L[i].strip() and not re.match(r"^\d+[.)] ", L[i].strip()):
                        nested(i, r"^[-*] ")
                        items[-1] += " " + L[i].strip(); i += 1
                story.append(self.lst(items, True, start)); continue
            if re.match(r"^[-*] ", s):
                flush(); items = []
                while i < len(L) and re.match(r"^[-*] ", L[i].strip()):
                    if L[i][:1].isspace():
                        nested(i, r"^[-*] ")
                    items.append(L[i].strip()[2:]); i += 1
                    while i < len(L) and L[i].startswith("  ") and L[i].strip() and not re.match(r"^[-*] ", L[i].strip()):
                        nested(i, r"^\d+[.)] ")
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


class ReportDoc(BaseDocTemplate):
    """Records the page index of every ## heading as it is drawn (the book's contents use it)."""
    def afterFlowable(self, f):
        if hasattr(f, "_heading"):
            self.headings.append((f._heading, self.page - 1))


def make_canvas(meta, page_w, page_h, cover=False, offset=0):
    """Canvas class that draws the header and footer on every page once the page count is known.
    With a cover, the first page gets neither and "Page 1 of N" starts on the page after it.
    offset: pages that come before this PDF in the final file (cover and contents of pages: full),
    counted in "Page X of Y"."""
    th, skip = dict(TH), 1 if cover else 0
    short, left_foot = page_layout.short_title(meta), page_layout.left_footer(th, meta)

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k); self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__)); self._startPage()

        def save(self):
            n = len(self._saved) - skip + offset
            for i, st in enumerate(self._saved):
                self.__dict__.update(st)
                if i >= skip:
                    page_layout.draw_header_footer(self, th, page_w, page_h, short, left_foot,
                                                   LABELS["page"].format(n=i + 1 - skip + offset, total=n))
                super().showPage()
            super().save()
    return NumberedCanvas


def read_front_matter(md):
    meta = {}
    md = md.lstrip("\ufeff")
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end > 0:
            meta = report_figs.parse_kv(md[3:end])
            md = md[end + 4:]
    return meta, md


def doc_title(meta, body):
    """Front matter title, else the first `# ` line outside code fences, else 'Report'."""
    if meta.get("title"):
        return meta["title"]
    fence = False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
        elif not fence and line.startswith("# "):
            return line[2:].strip()
    return "Report"


def split_set(top):
    """--set values -> (theme keys, other keys): the first go on top of the theme layers, the
    second into the front matter."""
    report_figs.check_keys(top, CMDLINE)
    th = {k: v for k, v in top.items() if k in report_figs.THEME_KEYS}
    return th, {k: v for k, v in top.items() if k not in th}


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


def report_theme(md_path, meta, base_layers=(), top=None):
    """Resolved theme of one report: skill theme.yml, then base_layers (a book passes its own
    layers), then the report's theme_layers(), then `top` (--set theme keys, paths relative to the
    current folder). A theme file already in base_layers is used once."""
    default = (report_figs.DEFAULT_THEME, report_figs.SKILL_DIR, report_figs.read_theme_file(report_figs.DEFAULT_THEME))
    seen = {name for name, _, _ in base_layers}
    own = [l for l in theme_layers(md_path, meta) if l[0] not in seen]
    cmd = [(CMDLINE, os.getcwd(), top)] if top else []
    return report_figs.load_theme([default, *base_layers, *own, *cmd])


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
            v = "skill assets/logo.png" if page_layout.is_skill_logo(v) else short(v)
        if k == "cover_logo":
            v = "none" if th[k] == "" else short(th[k]) if th[k] else f"(auto: {short(page_layout.cover_logo(th) or 'none')})"
        if k == "footer" and not v:
            v = "(author · date)"
        print(f"{k:18} {v!s:24} {short(src[k])}")


def load_report(md_path, base_layers=(), top=None):
    """(meta with the --set front-matter keys, body, resolved theme, source lines before the body)."""
    md = open(md_path, encoding="utf-8-sig").read()
    meta, body = read_front_matter(md)
    top_th, top_meta = split_set(top or {})
    meta.update(top_meta)
    th, _ = report_theme(md_path, meta, base_layers, top_th)
    meta.setdefault("title", doc_title(meta, body))
    return meta, body, th, md[:len(md) - len(body)].count("\n")


def build(md_path, out_pdf, pages=None, base_layers=(), top=None, offset=0, number_prefix=None):
    """Build one report and return [(## heading text, page index), ...] for its ## headings.
    pages=None follows the `pages` theme key: full (cover, contents, report; assembled by
    build_book.single), cover (cover page and report) or content (the report only; a book passes it).
    base_layers sit between the skill theme and the report's own theme; top is the --set dict;
    offset is the number of pages before the report in the final file; number_prefix (a book
    passes the report's place, "3") numbers equations, figures and tables (3.1), Figure 3.1."""
    meta, body, th, line0 = load_report(md_path, base_layers, top)
    pages = th["pages"] if pages is None else pages
    if pages == "full":
        import build_book
        return build_book.single(md_path, out_pdf, base_layers, top)
    apply_theme(th)
    cover = pages == "cover"
    W, H = paper = page_layout.PAPERS[TH["paper"]]
    L = LAYOUT
    tw = W - L.margin_l - L.margin_r
    with tempfile.TemporaryDirectory(prefix="report_eq_") as work:  # equation SVGs, deleted after the build
        rep = Report(md_path, meta, tw, work, line0, number_prefix)
        story = rep.parse(body)
    title = meta["title"]
    doc = ReportDoc(out_pdf, pagesize=paper, leftMargin=L.margin_l, rightMargin=L.margin_r,
                    topMargin=L.margin_t, bottomMargin=L.margin_b, title=title, author=TH["author"])
    doc.headings = []
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
    doc.build(story, canvasmaker=make_canvas(meta, W, H, cover, offset))
    return [(h, p - (1 if cover else 0)) for h, p in doc.headings]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown"); ap.add_argument("output", nargs="?")
    ap.add_argument("--pages", choices=report_figs.CHOICES["pages"],
                    help="full = cover, contents and report (default); cover = cover and report; "
                         "content = the report only (short for --set pages=...)")
    page_layout.add_options(ap)
    a = ap.parse_args()
    top = page_layout.parse_set(a.set)
    if a.pages:
        top["pages"] = a.pages
    if a.show_theme:
        meta = read_front_matter(open(a.markdown, encoding="utf-8-sig").read())[0]
        top_th, top_meta = split_set(top)
        show_theme(*report_theme(a.markdown, {**meta, **top_meta}, top=top_th))
    elif a.output:
        build(a.markdown, a.output, top=top)
        print(f"Wrote {a.output}")
        page_layout.finish(a, a.output)
    else:
        ap.error("give an output PDF path, or --show-theme")
