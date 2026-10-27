#!/usr/bin/env python3
"""Combine several reports into one PDF with a cover page, a table of contents and bookmarks.

Usage:
    python build_book.py book.md out.pdf
    python build_book.py book.md --show-theme     # resolved theme and the source of each key

book.md holds the cover values as front matter and lists the reports in reading order, one
`- path/report.md` per line (paths relative to book.md). Every report is built fresh with
build_report.py, so the combined file always matches its sources. The book's theme (skill
theme.yml, then report-theme.yml next to book.md or `theme:`, then the front matter) styles the
cover and contents pages and sits under each report's own theme, so one setting in book.md
reaches every page. Page geometry and fixed words live in page_layout.py.
See ../SKILL.md ("Combining reports") and ../references/example-book.md.
Requires: pip install -r requirements.txt (adds pypdf to the report requirements).
"""
import argparse, io, math, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.annotations import Link
    from pypdf.generic import Fit
except ImportError:
    sys.exit("pypdf missing: pip install -r requirements.txt (in the skill folder)")
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

import build_report
import page_layout
import report_figs
from page_layout import LABELS, LAYOUT, draw_text, fit_size, text_w

BOOK_KEYS = ("page_stamp",)  # book only; the report keys (title, cover fields ...) and theme keys also apply


def fail(msg):
    sys.exit(f"Book error: {msg}")


def read_book(path):
    meta, body = build_report.read_front_matter(open(path, encoding="utf-8-sig").read())
    report_figs.check_keys(meta, os.path.basename(path), extra=BOOK_KEYS)
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


def theme_meta(meta):
    return {k: v for k, v in meta.items() if k in report_figs.THEME_KEYS or k == "theme"}


# ---------------------------------------------------------------- section pages
def plain(s):
    """Heading text as it reads in the PDF: no Markdown marks, single spaces."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*`]|\\(?=[|_*])", "", s)
    s = re.sub(r"[_^]\{([^}]*)\}", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    """Letters and digits only, so subscripts, spacing and punctuation do not affect a match."""
    return re.sub(r"[\W_]+", "", s).lower()


def headings(body):
    """`## N. Heading` lines outside fenced code blocks, as plain text."""
    out, fence = [], False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
        elif not fence:
            m = re.match(r"^## (\d+)\.\s+(.+)$", line)
            if m:
                out.append(plain(f"{m.group(1)}. {m.group(2)}"))
    return out


def find_page(pages, key, start):
    """First page from `start` with a text line equal to the heading, or to its start (a heading
    that wraps, or whose subscript the PDF text puts on a line of its own)."""
    for j in range(start, len(pages)):
        if any(ln == key or (len(ln) >= 6 and key.startswith(ln)) for ln in pages[j]):
            return j
    return None


def build_reports(paths, work, base_layers):
    out = []
    for i, md_path in enumerate(paths):
        meta, body = build_report.read_front_matter(open(md_path, encoding="utf-8-sig").read())
        title = meta.get("title") or next((l[2:] for l in body.split("\n") if l.startswith("# ")), "Report")
        pdf = os.path.join(work, f"{i:02d}.pdf")
        build_report.build(md_path, pdf, cover=False, base_layers=base_layers)
        reader = PdfReader(pdf)
        lines = [[n for n in map(norm, (p.extract_text() or "").split("\n")) if n] for p in reader.pages]
        sections, page = [], 0
        for txt in headings(body):
            j = find_page(lines, norm(txt), page)
            if j is None:
                print(f"WARNING: section '{txt}' not found in the PDF of {os.path.basename(md_path)}; "
                      f"the contents gives it page {page + 1} of that report", file=sys.stderr)
            else:
                page = j
            sections.append((txt, page))
        box = reader.pages[0].mediabox
        out.append(dict(pdf=pdf, md=md_path, title=plain(title), doc=meta.get("doc_no", ""),
                        pages=len(reader.pages), sections=sections, size=(float(box.width), float(box.height))))
    return out


# ---------------------------------------------------------------- contents pages
class Contents:
    def __init__(self, meta, th, paper):
        self.th = th
        self.W, self.H = paper
        self.short = page_layout.short_title(meta)
        self.left_foot = page_layout.left_footer(th, meta)

    def paginate(self, reps):
        """Contents rows per page, each {rep, sections, cont}: a report row, then its section rows. A report that does not fit
        moves to the next page whole; one longer than a page continues under a '(cont.)' row."""
        L = LAYOUT
        top, bottom, head = self.H - L.toc_top, L.toc_bottom, L.row_r + L.row_gap
        pages, cur, y = [], [], top - L.toc_gap
        for r in reps:
            secs, cont = list(r["sections"]), False
            h = head + L.row_s * len(secs)
            if y - h < bottom and cur and h <= top - bottom:
                pages.append(cur); cur, y = [], top
            while True:
                fit = math.floor((y - head - bottom) / L.row_s + 1e-9)  # section rows under the report row
                if cur and (fit < 0 or (secs and fit < 1)):
                    pages.append(cur); cur, y = [], top
                    continue
                part, secs = secs[:max(fit, 1)], secs[max(fit, 1):]
                cur.append(dict(rep=r, sections=part, cont=cont)); y -= head + L.row_s * len(part)
                if not secs:
                    break
                pages.append(cur); cur, y, cont = [], top, True
        pages.append(cur)
        return pages

    def leader(self, c, x1, x2, y):
        size = LAYOUT.leader_size
        c.setFillColor(colors.HexColor(self.th["hairline"])); c.setFont("Sans", size)
        dot = pdfmetrics.stringWidth(". ", "Sans", size)
        x = x1
        while x + dot < x2:
            c.drawString(x, y, ". "); x += dot

    def draw(self, c, pages, first, links):
        """Draw the contents pages; `first` is the index of the first one. Appends
        (page index, rect, target page index) to links."""
        L, W, th = LAYOUT, self.W, self.th
        ink, acc = colors.HexColor(th["text_color"]), colors.HexColor(th["accent_color"])
        muted, tint = colors.HexColor(th["muted_color"]), colors.HexColor(th["tint_light"])
        doc_x, num_x = W - L.margin_r - L.doc_right, W - L.margin_r - L.num_right
        sec_x, lead_end = L.margin_l + L.sec_x, W - L.margin_r - L.leader_right
        for pi, reps in enumerate(pages):
            page_layout.draw_header_footer(c, th, W, self.H, self.short, self.left_foot)  # number: the book stamp
            y = self.H - L.toc_top
            if pi == 0:
                draw_text(c, L.margin_l, y, LABELS["contents"], "Sans-Bold", L.toc_size, ink)
                y -= L.toc_gap
            for row in reps:
                r = row["rep"]
                y -= L.row_gap
                band = y - L.row_pad
                c.setFillColor(tint); c.rect(L.margin_l, band, W - L.margin_l - L.margin_r, L.row_r, stroke=0, fill=1)
                c.setFillColor(acc); c.rect(L.margin_l, band, L.row_bar, L.row_r, stroke=0, fill=1)
                cont = f" {LABELS['cont']}" if row["cont"] else ""
                room = doc_x - text_w(r["doc"], "Sans", L.doc_size) - L.rep_gap - (L.margin_l + L.rep_x)
                size = fit_size(r["title"] + cont, "Sans-Bold", L.rep_size, L.rep_min, room)
                title = page_layout.ellipsis(r["title"], "Sans-Bold", size, room - text_w(cont, "Sans-Bold", size))
                draw_text(c, L.margin_l + L.rep_x, y, title + cont, "Sans-Bold", size, ink)
                draw_text(c, doc_x, y, r["doc"], "Sans", L.doc_size, muted, align="right")
                draw_text(c, num_x, y, str(r["start"] + 1), "Sans-Bold", L.rep_size, ink, align="right")
                links.append((first + pi, (L.margin_l, band, W - L.margin_r, band + L.row_r), r["start"]))
                y -= L.row_r
                for txt, p in row["sections"]:
                    w = draw_text(c, sec_x, y, txt, "Sans", L.sec_size, ink, max_w=lead_end - L.leader_gap - sec_x)
                    self.leader(c, sec_x + w + L.leader_gap, lead_end, y)
                    draw_text(c, num_x, y, str(r["start"] + p + 1), "Sans", L.sec_size, ink, align="right")
                    links.append((first + pi, (L.margin_l + L.link_x, y - L.link_below, W - L.margin_r,
                                               y + L.link_above), r["start"] + p))
                    y -= L.row_s
            c.showPage()


def stamp_page(th, w, h, n, total):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    page_layout.draw_stamp(c, w, th, n, total)
    c.save(); buf.seek(0)
    return PdfReader(buf).pages[0]


# ---------------------------------------------------------------- book
def build_book(book_md, out_pdf):
    meta, paths = read_book(book_md)
    where = f"front matter of {os.path.basename(book_md)}"
    layers = build_report.theme_layers(book_md, theme_meta(meta))
    th, _ = build_report.report_theme(book_md, theme_meta(meta))
    paper = page_layout.parse_paper(meta, where)
    stamp = report_figs.parse_switch(meta.get("page_stamp", "on"), "page_stamp", where)

    with tempfile.TemporaryDirectory(prefix="book_") as work:
        reps = build_reports(paths, work, layers)
        for r in reps:
            if any(abs(a - b) > 1 for a, b in zip(r["size"], paper)):
                print(f"WARNING: {os.path.basename(r['md'])} has a different paper size from the book "
                      f"(set paper: in its front matter)", file=sys.stderr)
        toc = Contents(meta, th, paper)
        pages = toc.paginate(reps)
        front = 1 + len(pages)
        n = front
        for r in reps:
            r["start"] = n; n += r["pages"]
        total = n

        buf, links = io.BytesIO(), []
        c = canvas.Canvas(buf, pagesize=paper)
        rows = [(LABELS["revision"], meta.get("revision")), (LABELS["date"], meta.get("date")),
                (LABELS["author"], th["author"]),
                (LABELS["contents"], LABELS["book_size"].format(n=len(reps), total=total))]
        page_layout.draw_cover(c, th, meta, *paper, rows); c.showPage()
        toc.draw(c, pages, 1, links)
        c.save(); buf.seek(0)

        w = PdfWriter()
        for p in PdfReader(buf).pages:
            w.add_page(p)
        for r in reps:
            for p in PdfReader(r["pdf"]).pages:
                w.add_page(p)
        if stamp:  # every page but the cover
            for i in range(1, total):
                box = w.pages[i].mediabox
                w.pages[i].merge_page(stamp_page(th, float(box.width), float(box.height), i + 1, total))
        for page_idx, rect, target in links:
            w.add_annotation(page_number=page_idx, annotation=Link(rect=rect, target_page_index=target, fit=Fit.fit()))
        w.add_outline_item(LABELS["cover"], 0)
        w.add_outline_item(LABELS["contents"], 1)
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
    ap.add_argument("book"); ap.add_argument("output", nargs="?")
    ap.add_argument("--show-theme", action="store_true", help="print the resolved book theme and where each key came from, then exit")
    a = ap.parse_args()
    if a.show_theme:
        build_report.show_theme(*build_report.report_theme(a.book, theme_meta(read_book(a.book)[0])))
    elif a.output:
        build_book(a.book, a.output)
    else:
        ap.error("give an output PDF path, or --show-theme")
