#!/usr/bin/env python3
"""Combine several reports into one PDF with a cover page, a table of contents and bookmarks.

Usage:
    python build_book.py book.md out.pdf

book.md holds the cover values as front matter and lists the reports in reading order, one
`- path/report.md` per line (paths relative to book.md). Every report is built fresh with
build_report.py, so the combined file always matches its sources. The theme is resolved the
same way as for a report (skill theme.yml, then report-theme.yml next to book.md, then the
front matter), so the cover and contents pages match the report pages.
See ../SKILL.md ("Combining reports") and ../references/example-book.md.
Requires: pip install -r requirements.txt (adds pypdf to the report requirements).
"""
import argparse, difflib, io, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.annotations import Link
    from pypdf.generic import Fit
except ImportError:
    sys.exit("pypdf missing: pip install -r requirements.txt (in the skill folder)")
from PIL import Image as PILImage
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

import build_report  # registers the fonts (Sans, Sans-Bold, ...) on import
import report_figs
from svglib.svglib import svg2rlg

BOOK_KEYS = ("title", "subtitle", "short_title", "date", "revision", "paper", "theme",
             "kicker", "project", "specs", "note", "license", "cover_logo", "page_stamp")
ML = MR = 22 * mm
RULE_W = build_report.HEADER_RULE_W


def fail(msg):
    sys.exit(f"Book error: {msg}")


def read_book(path):
    text = open(path, encoding="utf-8").read()
    meta, body = build_report.read_front_matter(text)
    for k in meta:
        if k not in BOOK_KEYS + report_figs.THEME_KEYS:
            near = difflib.get_close_matches(k, BOOK_KEYS + report_figs.THEME_KEYS, n=1)
            fail(f"unknown key '{k}' in {os.path.basename(path)}" + (f" (did you mean '{near[0]}'?)" if near else
                 f"; book keys: {', '.join(BOOK_KEYS)}, plus the theme keys"))
    base = os.path.dirname(os.path.abspath(path))
    reports = []
    for line in body.split("\n"):
        m = re.match(r"^\s*[-*]\s+(\S.*?\.md)\s*$", re.sub(r"\s+#.*$", "", line))
        if m:
            p = os.path.normpath(os.path.join(base, m.group(1)))
            if not os.path.exists(p):
                fail(f"report not found: {m.group(1)} (listed in {os.path.basename(path)})")
            reports.append(p)
    if not reports:
        fail(f"no reports listed in {os.path.basename(path)}; add lines like '- 01_Intro/report.md'")
    return meta, reports


def fix_svg_gradients(drawing, path):
    """svglib ignores gradientTransform on a userSpaceOnUse linearGradient, so a gradient defined
    on a unit vector and placed by its transform (as Affinity exports it) collapses to its last
    colour. Apply the matrix to the gradient end points; gradients are matched by their stops."""
    import xml.etree.ElementTree as ET
    fixes = {}
    for g in ET.parse(path).getroot().iter("{http://www.w3.org/2000/svg}linearGradient"):
        m = re.match(r"\s*matrix\(([^)]*)\)", g.get("gradientTransform", ""))
        if not m or g.get("gradientUnits") != "userSpaceOnUse":
            continue
        a, b, c, d, e, f = (float(v) for v in re.split(r"[\s,]+", m.group(1).strip()))
        x1, y1, x2, y2 = (float(g.get(k, dflt)) for k, dflt in (("x1", 0), ("y1", 0), ("x2", 1), ("y2", 0)))
        stops = tuple(round(float(s.get("offset", 0)), 4) for s in g.iter("{http://www.w3.org/2000/svg}stop"))
        fixes[stops] = (a * x1 + c * y1 + e, b * x1 + d * y1 + f, a * x2 + c * y2 + e, b * x2 + d * y2 + f)

    def walk(node):
        for ch in getattr(node, "contents", []):
            if type(ch).__name__ == "LinearGradientShape":
                end = fixes.get(tuple(round(p, 4) for p in ch._positions))
                if end:
                    ch._x0, ch._y0, ch._x1, ch._y1 = end
            walk(ch)
    if fixes:
        walk(drawing)


def plain(s):
    """Heading text as it appears in the PDF: no Markdown marks, single spaces."""
    s = re.sub(r"[*`]|\\(?=[|_])", "", s)
    s = re.sub(r"_\{([^}]*)\}", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def build_reports(paths, work):
    out = []
    for i, md_path in enumerate(paths):
        meta, body = build_report.read_front_matter(open(md_path, encoding="utf-8").read())
        title = meta.get("title") or next((l[2:] for l in body.split("\n") if l.startswith("# ")), "Report")
        pdf = os.path.join(work, f"{i:02d}.pdf")
        build_report.build(md_path, pdf)
        reader = PdfReader(pdf)
        texts = [re.sub(r"\s+", " ", p.extract_text() or "") for p in reader.pages]
        sections, page = [], 0
        for num, head in re.findall(r"^## (\d+)\.\s+(.+)$", body, flags=re.M):
            key = plain(f"{num}. {head}")[:32]
            page = next((j for j in range(page, len(texts)) if key in texts[j]), page)
            sections.append((plain(f"{num}. {head}"), page))
        out.append(dict(pdf=pdf, title=plain(title), doc=meta.get("doc_no", ""),
                        pages=len(reader.pages), sections=sections))
    return out


class Book:
    def __init__(self, meta, th, paper):
        self.m, self.th = meta, th
        self.W, self.H = paper
        self.ink = colors.HexColor(th["text_color"])
        self.acc = colors.HexColor(th["accent_color"])
        self.muted = colors.HexColor(th["muted_color"])
        self.tint = colors.HexColor(th["tint_light"])
        self.rule = colors.HexColor(th["header_rule_color"]) if th["header_rule_color"] else None
        self.logo = th["logo"]
        # Cover logo: cover_logo key, else the vector assets/logo.svg while the theme uses the
        # skill's own logo, else the theme logo (a custom theme keeps its own logo).
        cl = meta.get("cover_logo")
        assets = os.path.join(report_figs.SKILL_DIR, "assets")
        if cl:
            self.cover_logo = os.path.normpath(os.path.join(meta["_base"], cl))
        elif self.logo and os.path.samefile(self.logo, os.path.join(assets, "logo.png")) \
                and os.path.exists(os.path.join(assets, "logo.svg")):
            self.cover_logo = os.path.join(assets, "logo.svg")
        else:
            self.cover_logo = self.logo
        if self.cover_logo and not os.path.exists(self.cover_logo):
            fail(f"cover_logo not found: {self.cover_logo}")
        self.short = meta.get("short_title") or meta.get("title", "")
        if meta.get("revision"):
            self.short += f"  ·  " + " ".join(x for x in (meta.get("project"), f"Rev. {meta['revision']}") if x)
        self.left_foot = th["footer"] or " · ".join(x for x in (th["author"], meta.get("date")) if x)

    def _img(self, c, path, x, y_top, w=None, h=None):
        """Draw a PNG/JPG, or an SVG as vector graphics, with its top-left corner at (x, y_top)."""
        if path.lower().endswith(".svg"):
            d = svg2rlg(path)
            if d is None:
                fail(f"cannot read SVG: {path}")
            fix_svg_gradients(d, path)
            pw, ph = d.width, d.height
        else:
            pw, ph = PILImage.open(path).size
        if w is None:
            w = h * pw / ph
        h = w * ph / pw
        if path.lower().endswith(".svg"):
            d.scale(w / pw, h / ph); d.width, d.height = w, h
            renderPDF.draw(d, c, x, y_top - h)
        else:
            c.drawImage(path, x, y_top - h, w, h, mask="auto")
        return h

    def rule_line(self, c, y):
        if self.rule:
            c.setStrokeColor(self.rule); c.setLineWidth(RULE_W); c.line(ML, y, self.W - MR, y)

    def header_footer(self, c, n, total):
        W, H = self.W, self.H
        lh = 9.5 * mm
        y_logo = H - 10 * mm - lh
        if self.th["header"]:
            if self.logo:
                self._img(c, self.logo, ML, y_logo + lh, h=lh)
            c.setFont("Sans", 8); c.setFillColor(self.muted)
            c.drawRightString(W - MR, y_logo + 2.2 * mm, self.short)
            self.rule_line(c, y_logo - 2.6 * mm)
        self.rule_line(c, 13 * mm)
        c.setFont("Sans", 7.8); c.setFillColor(self.muted)
        c.drawString(ML, 9 * mm, self.left_foot)
        c.drawRightString(W - MR, 9 * mm, f"{n} / {total}")

    def wrap(self, text, font, size, width):
        lines, cur = [], ""
        for w in text.split():
            t = f"{cur} {w}".strip()
            if pdfmetrics.stringWidth(t, font, size) <= width or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        return lines + ([cur] if cur else [])

    def cover(self, c, n_reports, total):
        m, W, H = self.m, self.W, self.H
        tw = W - ML - MR
        c.setFillColor(self.acc); c.rect(0, 0, 7 * mm, H, stroke=0, fill=1)
        if self.cover_logo:
            self._img(c, self.cover_logo, ML, H - 28 * mm, w=46 * mm)
        if m.get("project"):
            c.setFont("Sans", 9); c.setFillColor(self.muted)
            c.drawRightString(W - MR, H - 24 * mm, f"Project {m['project']}")
        y = H - 118 * mm
        if m.get("kicker"):
            c.setFont("Sans-Bold", 10); c.setFillColor(self.acc); c.drawString(ML, y, m["kicker"].upper())
            y -= 14 * mm
        c.setFont("Sans-Bold", 27); c.setFillColor(colors.HexColor(self.th["title_color"]))
        for line in self.wrap(m.get("title", ""), "Sans-Bold", 27, tw)[:3]:
            c.drawString(ML, y, line); y -= 11.5 * mm
        y += 2.5 * mm
        c.setFont("Sans", 11.5); c.setFillColor(self.muted)
        for line in self.wrap(m.get("subtitle", ""), "Sans", 11.5, tw)[:2]:
            c.drawString(ML, y, line); y -= 6 * mm
        y -= 1 * mm
        self.rule_line(c, y)
        specs = [s.split("=", 1) for s in m.get("specs", "").split("|") if "=" in s]
        if specs:
            y -= 30 * mm
            c.setFillColor(self.tint); c.rect(ML, y, tw, 24 * mm, stroke=0, fill=1)
            c.setFillColor(self.acc); c.rect(ML, y, 1.2 * mm, 24 * mm, stroke=0, fill=1)
            colw = (tw - 6 * mm) / len(specs)
            for i, (k, v) in enumerate(specs):
                x = ML + 6 * mm + i * colw
                c.setFont("Sans", 8.5); c.setFillColor(self.muted); c.drawString(x, y + 15 * mm, k.strip())
                size = 11.5
                while size > 8 and pdfmetrics.stringWidth(v.strip(), "Sans-Bold", size) > colw - 3 * mm:
                    size -= 0.5
                c.setFont("Sans-Bold", size); c.setFillColor(self.ink); c.drawString(x, y + 8 * mm, v.strip())
        y -= 22 * mm
        rows = [("Revision", m.get("revision")), ("Date", m.get("date")), ("Author", self.th["author"]),
                ("Contents", f"{n_reports} reports, {total} pages")]
        for k, v in rows:
            if v:
                c.setFont("Sans", 9); c.setFillColor(self.muted); c.drawString(ML, y, k)
                c.setFont("Sans", 10); c.setFillColor(self.ink); c.drawString(ML + 28 * mm, y, v)
                y -= 6.5 * mm
        self.rule_line(c, 22 * mm)
        c.setFont("Sans", 8); c.setFillColor(self.muted)
        if m.get("note"):
            c.drawString(ML, 16 * mm, m["note"])
        if m.get("license"):
            c.drawRightString(W - MR, 16 * mm, m["license"])

    # contents layout
    ROW_R, ROW_S, GAP = 8.2 * mm, 5.6 * mm, 3.0 * mm

    def paginate(self, reps):
        top, bottom = self.H - 40 * mm, 20 * mm
        pages, cur, y = [], [], top - 14 * mm
        for r in reps:
            h = self.ROW_R + self.GAP + self.ROW_S * len(r["sections"])
            if y - h < bottom and cur:
                pages.append(cur); cur, y = [], top
            cur.append(r); y -= h
        pages.append(cur)
        return pages

    def leader(self, c, x1, x2, y):
        c.setFillColor(colors.HexColor(self.th["hairline"])); c.setFont("Sans", 8)
        dot = pdfmetrics.stringWidth(". ", "Sans", 8)
        x = x1
        while x + dot < x2:
            c.drawString(x, y, ". "); x += dot

    def contents(self, c, pages, start, total, links):
        W = self.W
        for pi, reps in enumerate(pages):
            self.header_footer(c, start + pi + 1, total)
            y = self.H - 40 * mm
            if pi == 0:
                c.setFont("Sans-Bold", 20); c.setFillColor(self.ink); c.drawString(ML, y, "Contents")
                y -= 14 * mm
            for r in reps:
                y -= self.GAP
                c.setFillColor(self.tint); c.rect(ML, y - 2.6 * mm, W - ML - MR, self.ROW_R, stroke=0, fill=1)
                c.setFillColor(self.acc); c.rect(ML, y - 2.6 * mm, 1.0 * mm, self.ROW_R, stroke=0, fill=1)
                room = W - MR - 16 * mm - pdfmetrics.stringWidth(r["doc"], "Sans", 8) - (ML + 4 * mm) - 4 * mm
                size = 10.5
                while size > 8 and pdfmetrics.stringWidth(r["title"], "Sans-Bold", size) > room:
                    size -= 0.5
                c.setFont("Sans-Bold", size); c.setFillColor(self.ink)
                c.drawString(ML + 4 * mm, y, r["title"])
                c.setFont("Sans", 8); c.setFillColor(self.muted)
                c.drawRightString(W - MR - 14 * mm, y, r["doc"])
                c.setFont("Sans-Bold", 10.5); c.setFillColor(self.ink)
                c.drawRightString(W - MR - 2 * mm, y, str(r["start"] + 1))
                links.append((start + pi, (ML, y - 2.6 * mm, W - MR, y - 2.6 * mm + self.ROW_R), r["start"]))
                y -= self.ROW_R
                for txt, p in r["sections"]:
                    c.setFont("Sans", 9.5); c.setFillColor(self.ink)
                    c.drawString(ML + 10 * mm, y, txt)
                    self.leader(c, ML + 12 * mm + pdfmetrics.stringWidth(txt, "Sans", 9.5), W - MR - 10 * mm, y)
                    c.setFont("Sans", 9.5); c.setFillColor(self.ink)
                    c.drawRightString(W - MR - 2 * mm, y, str(r["start"] + p + 1))
                    links.append((start + pi, (ML + 8 * mm, y - 1.6 * mm, W - MR, y + 3.8 * mm), r["start"] + p))
                    y -= self.ROW_S
            c.showPage()

    def stamp(self, n, total):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(self.W, self.H))
        c.setFont("Sans", 7.8); c.setFillColor(self.muted)
        c.drawCentredString(self.W / 2, 9 * mm, f"{n} / {total}")
        c.save(); buf.seek(0)
        return PdfReader(buf).pages[0]


def build_book(book_md, out_pdf):
    meta, paths = read_book(book_md)
    meta["_base"] = os.path.dirname(os.path.abspath(book_md))
    theme_meta = {k: v for k, v in meta.items() if k in report_figs.THEME_KEYS or k == "theme"}
    th, _ = build_report.report_theme(book_md, theme_meta)
    paper = letter if meta.get("paper", "a4").lower() == "letter" else A4
    stamp = meta.get("page_stamp", "on").lower() not in ("off", "false", "no")

    with tempfile.TemporaryDirectory(prefix="book_") as work:
        reps = build_reports(paths, work)
        book = Book(meta, th, paper)
        pages = book.paginate(reps)
        front = 1 + len(pages)
        n = front
        for r in reps:
            r["start"] = n; n += r["pages"]
        total = n

        buf, links = io.BytesIO(), []
        c = canvas.Canvas(buf, pagesize=paper)
        book.cover(c, len(reps), total); c.showPage()
        book.contents(c, pages, 1, total, links)
        c.save(); buf.seek(0)

        w = PdfWriter()
        for p in PdfReader(buf).pages:
            w.add_page(p)
        for r in reps:
            for p in PdfReader(r["pdf"]).pages:
                w.add_page(p)
        if stamp:
            for i in range(front, total):
                w.pages[i].merge_page(book.stamp(i + 1, total))
        for page_idx, rect, target in links:
            w.add_annotation(page_number=page_idx, annotation=Link(rect=rect, target_page_index=target, fit=Fit.fit()))
        w.add_outline_item("Cover", 0)
        w.add_outline_item("Contents", 1)
        for r in reps:
            parent = w.add_outline_item(r["title"], r["start"])
            for txt, p in r["sections"]:
                w.add_outline_item(txt, r["start"] + p, parent=parent)
        w.add_metadata({"/Title": meta.get("title", "Reports"), "/Author": th["author"] or ""})
        with open(out_pdf, "wb") as f:
            w.write(f)
    print(f"Wrote {out_pdf}: {total} pages, {len(reps)} reports, {len(pages)} contents page(s)")
    for r in reps:
        print(f"  p{r['start'] + 1:>3}  {r['title']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book"); ap.add_argument("output")
    a = ap.parse_args()
    build_book(a.book, a.output)
