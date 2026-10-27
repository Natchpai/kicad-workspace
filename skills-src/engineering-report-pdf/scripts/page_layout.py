"""Page drawing shared by build_report.py and build_book.py: fonts, header and footer, images,
the cover page, warnings and the command-line options both builders share.

LAYOUT, STYLES, BLOCKS and LABELS below are the only place sizes, distances and fixed words are
written. Change a value there and both builders follow. User choices (colours, logo, paper,
pages) are theme keys in ../theme.yml, not values here.
"""
import os, re, sys
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from PIL import Image as PILImage
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from svglib.svglib import svg2rlg

import report_figs

# ---------------------------------------------------------------- geometry
# Distances from the page top are named *_top; all others are from the page bottom or left edge.
LAYOUT = SimpleNamespace(
    # page (reports, cover and contents)
    margin_l=22 * mm, margin_r=22 * mm,
    margin_t=28 * mm, margin_b=20 * mm,     # report text frame
    rule_w=0.9,                             # header line, footer line and the line under the title block
    # header: logo top-left, short title top-right, rule below
    logo_h=9.5 * mm, logo_top=10 * mm,
    head_size=8, head_raise=2.2 * mm,       # short title size, and its baseline above the logo bottom
    head_rule_gap=2.6 * mm,                 # header rule below the logo bottom
    head_gap=6 * mm,                        # least space between the logo and the short title
    # footer: author · date left, page label right
    foot_rule_y=13 * mm, foot_y=9 * mm, foot_size=7.8,
    # cover page
    strip_w=7 * mm,                         # accent strip on the left edge
    cover_logo_w=46 * mm, cover_logo_top=28 * mm,
    project_top=24 * mm, project_size=9,    # "Project X", top-right
    kicker_top=118 * mm, kicker_size=10, kicker_gap=14 * mm,
    title_size=27, title_lead=11.5 * mm, title_lines=3,
    subtitle_size=11.5, subtitle_lead=6 * mm, subtitle_lines=2,
    subtitle_rise=2.5 * mm,                 # subtitle pulled up toward the last title line
    title_rule_gap=1 * mm,                  # rule below the last subtitle line
    specs_drop=30 * mm, specs_h=24 * mm,    # key-figure panel: top gap below the rule, height
    specs_bar=1.2 * mm, specs_pad=6 * mm,
    specs_key_size=8.5, specs_key_y=15 * mm,
    specs_val_size=11.5, specs_val_min=8, specs_val_y=8 * mm, specs_val_pad=3 * mm,
    rows_drop=22 * mm,                      # first meta row below the specs panel (or the rule)
    row_label_size=9, row_value_size=10, row_value_x=28 * mm, row_lead=6.5 * mm,
    cover_rule_y=22 * mm, cover_note_y=16 * mm, cover_note_size=8,
    # contents pages (book)
    toc_top=40 * mm, toc_size=20, toc_gap=14 * mm,
    toc_bottom=20 * mm,                     # lowest row baseline
    row_r=8.2 * mm, row_s=5.6 * mm, row_gap=3 * mm,   # report row, section row, gap above a report row
    row_pad=2.6 * mm, row_bar=1 * mm,       # report row band: depth below the baseline, accent bar width
    rep_x=4 * mm, rep_size=10.5, rep_min=8, # report title: indent, size, smallest size before ellipsis
    rep_gap=6 * mm,                         # least space between the report title and its doc no.
    doc_size=8, doc_right=14 * mm,          # doc no.: size, right edge before the page column
    num_right=2 * mm,                       # page numbers: right edge inside the right margin
    sec_x=10 * mm, sec_size=9.5,
    leader_gap=2 * mm, leader_right=10 * mm, leader_size=8,
    link_x=8 * mm, link_below=1.6 * mm, link_above=3.8 * mm,   # click area of a section row
    # book page number ("n / N"), centred in the footer
    stamp_y=9 * mm, stamp_size=7.8,
)

# ---------------------------------------------------------------- report body text
# Paragraph styles: font, size and leading in pt, space before and after in pt. Colours come from
# the theme (build_report.apply_theme).
STYLES = dict(
    title=dict(font="Sans-Bold", size=19, leading=24, after=3),             # report title, page 1
    subtitle=dict(font="Sans", size=11.5, leading=15, after=4),
    meta=dict(font="Sans", size=9, leading=12, after=8),                    # author · date · doc no. line
    h2=dict(font="Sans-Bold", size=13.5, leading=18, before=16, after=6),
    h3=dict(font="Sans-Bold", size=11, leading=15, before=10, after=4),
    h4=dict(font="Sans-Bold", size=10, leading=14, before=8, after=3),
    body=dict(font="Sans", size=10, leading=14.8, after=6.5),
    cell=dict(font="Sans", size=9, leading=12.4),                           # table cells; header row in bold
    cap=dict(font="Sans", size=8.5, leading=11.5, before=4, after=10),      # figure caption, centred
    tcap=dict(font="Sans", size=8.5, leading=11.5, before=4, after=4),      # table caption, above the table
    code=dict(font="Mono", size=8.3, leading=11.2),
    note=dict(font="Sans", size=9.4, leading=13.6),
    eqno=dict(font="Sans", size=9.5, leading=12),                           # equation number, right
)

# Blocks in the report body (pt unless marked mm)
BLOCKS = SimpleNamespace(
    sub_rise="20%", sup_rise="38%", script_size="72%",   # inline X_{sub} and x^{sup}
    title_rule_h=10, title_rule_y=6,        # line under the title block: its row height, line height in it
    title_gap=4,                            # space instead of that line when it is off
    eq_size=11.5,                           # display equation size (body text is 10 pt)
    eq_num_w=14 * mm,                       # equation-number column, mirrored empty on the left
    eq_room=8 * mm,                         # an equation wider than the middle column less this is scaled down
    eq_bar=2.2,                             # bar on the left of equation and code panels
    eq_pad=7, code_pad=6, panel_side=10,    # panel padding: equation top/bottom, code top/bottom, sides
    panel_before=3, panel_after=8,
    note_line=0.8, note_pad=7, note_side=10, note_before=3, note_after=9,
    cell_pad_v=4, cell_pad_h=6,             # table cell padding
    head_line=1.0, row_line=0.4,            # line under the table header row, hairlines between rows
    table_before=2, table_after=10,
    table_keep=10,                          # tables with this many rows or fewer are kept on one page
    narrow_w=95 * mm,                       # width of a two-column table ...
    narrow_chars=60,                        # ... whose columns hold at most this many characters together
    fig_width=88,                           # default figure width, % of the text width
    fig_before=2, fig_after=8,              # space above a figure, and below one without a caption
    list_indent=16, bullet_size=9.4,
)

# ---------------------------------------------------------------- fixed words
LABELS = dict(
    page="Page {n} of {total}",             # report footer, right
    stamp="{n} / {total}",                  # book page number, footer centre
    rev="Rev. {revision}",                  # header tag after doc_no or project
    doc_no="Doc. No. {doc_no}",             # title-block meta line
    figure="Figure", table="Table",         # caption labels
    note="Note.",                           # note-box label
    project="Project {project}",            # cover, top-right
    document="Document", revision="Revision", date="Date", author="Author",   # cover rows
    contents="Contents",                    # contents heading, cover row, bookmark
    book_size="{n} reports, {total} pages", # cover row of a book
    cover="Cover",                          # bookmark
    cont="(cont.)",                         # report row repeated on the next contents page
)

PAPERS = {"a4": A4, "letter": letter}   # sizes for the `paper` theme key (names checked in report_figs.CHOICES)


def fail(msg):
    sys.exit(f"Layout error: {msg}")


# ---------------------------------------------------------------- console, warnings, options
def utf8_console():
    """Print UTF-8 even when the output goes to a pipe on a Windows console whose code page lacks
    a character (cp874 has no '·'), so a heading or path never crashes a print."""
    for f in (sys.stdout, sys.stderr):
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8", errors="replace")


utf8_console()
WARNINGS = []


def warn(msg):
    """Print a build warning and keep it for the summary (finish)."""
    WARNINGS.append(msg)
    print(f"WARNING: {msg}", file=sys.stderr)


def add_options(ap):
    """Command-line options both builders take."""
    ap.add_argument("--show-theme", action="store_true", help="print the resolved theme and where each key came from, then exit")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="theme or front-matter key for this build only (repeatable); wins over every file")
    ap.add_argument("--strict", action="store_true", help="exit with code 1 if the build printed any warning")
    ap.add_argument("--preview", metavar="DIR", help="after the build, render the pages to DIR (as preview.py)")
    ap.add_argument("--sheet", type=int, default=0, metavar="N", help="with --preview: N pages per contact sheet")


def parse_set(items):
    """--set values -> dict; the keys are checked with the theme layers."""
    out = {}
    for it in items:
        if "=" not in it:
            sys.exit(f"--set '{it}' must be KEY=VALUE")
        k, v = it.split("=", 1)
        out[k.strip().lower()] = v.strip()
    return out


def finish(a, out_pdf):
    """After a build: the optional preview, the warning count, and exit code 1 under --strict."""
    if a.preview:
        import preview
        for n in preview.preview(out_pdf, a.preview, sheet=a.sheet):
            print(os.path.join(a.preview, n))
    if WARNINGS:
        print(f"{len(WARNINGS)} warning(s)", file=sys.stderr)
        if a.strict:
            sys.exit(1)


# ---------------------------------------------------------------- fonts
FONT_DIR = os.path.join(report_figs.SKILL_DIR, "assets", "fonts")


def find_font(file):
    p = os.path.join(FONT_DIR, file)
    if os.path.exists(p):
        return p
    sys.exit(f"Font file missing: {p}. Re-copy the skill's assets/fonts folder.")


def register_fonts():
    """IBM Plex Sans for all text; DejaVu Sans as a per-character fallback; IBM Plex Mono for code."""
    faces = {"Sans": "IBMPlexSans-Regular.ttf", "Sans-Bold": "IBMPlexSans-SemiBold.ttf",
             "Sans-Oblique": "IBMPlexSans-Italic.ttf", "Sans-BoldOblique": "IBMPlexSans-SemiBoldItalic.ttf",
             "Fallback": "DejaVuSans.ttf", "Mono": "IBMPlexMono-Regular.ttf"}
    for k, f in faces.items():
        pdfmetrics.registerFont(TTFont(k, find_font(f)))
    addMapping("Sans", 0, 0, "Sans"); addMapping("Sans", 1, 0, "Sans-Bold")
    addMapping("Sans", 0, 1, "Sans-Oblique"); addMapping("Sans", 1, 1, "Sans-BoldOblique")
    addMapping("Fallback", 0, 0, "Fallback"); addMapping("Fallback", 1, 0, "Fallback")
    addMapping("Fallback", 0, 1, "Fallback"); addMapping("Fallback", 1, 1, "Fallback")


def _cmap(file):
    from fontTools.ttLib import TTFont as FTFont
    return set(FTFont(find_font(file)).getBestCmap())


register_fonts()
MAIN_CMAP = _cmap("IBMPlexSans-Regular.ttf")
MONO_CMAP = _cmap("IBMPlexMono-Regular.ttf")
FALLBACK_CMAP = _cmap("DejaVuSans.ttf")


def _needs_fallback(ch, cmap):
    return ord(ch) > 0x7f and ord(ch) not in cmap and ord(ch) in FALLBACK_CMAP


def with_fallback(t, cmap=MAIN_CMAP):
    """Paragraph markup: wrap characters the font lacks (e.g. ≫) in the DejaVu fallback font."""
    return re.sub(r"[^\x00-\x7f]", lambda m: f'<font name="Fallback">{m.group(0)}</font>'
                  if _needs_fallback(m.group(0), cmap) else m.group(0), t)


def _runs(text, font):
    """Split canvas text into (text, font) runs, with the fallback font for missing glyphs."""
    cmap = MONO_CMAP if font == "Mono" else MAIN_CMAP
    runs = []
    for ch in text:
        f = "Fallback" if _needs_fallback(ch, cmap) else font
        if runs and runs[-1][1] == f:
            runs[-1][0] += ch
        else:
            runs.append([ch, f])
    return runs


def text_w(text, font, size):
    return sum(pdfmetrics.stringWidth(t, f, size) for t, f in _runs(text, font))


def ellipsis(text, font, size, width):
    """Cut text to fit width, ending in '…'. Returns the text unchanged if it fits."""
    if text_w(text, font, size) <= width:
        return text
    while text and text_w(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def fit_size(text, font, size, min_size, width):
    """Largest size from `size` down to `min_size` (0.5 pt steps) at which text fits width."""
    while size > min_size and text_w(text, font, size) > width:
        size -= 0.5
    return size


def draw_text(c, x, y, text, font, size, color=None, align="left", max_w=None):
    """Canvas text with the glyph fallback; align is left, right or centre; max_w cuts with '…'."""
    if max_w:
        text = ellipsis(text, font, size, max_w)
    w = text_w(text, font, size)
    x = x - w if align == "right" else x - w / 2 if align == "centre" else x
    if color is not None:
        c.setFillColor(color)
    for t, f in _runs(text, font):
        c.setFont(f, size); c.drawString(x, y, t)
        x += pdfmetrics.stringWidth(t, f, size)
    return w


def wrap(text, font, size, width):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if text_w(t, font, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


# ---------------------------------------------------------------- images
def fix_svg_gradients(drawing, path):
    """svglib ignores gradientTransform on a userSpaceOnUse linearGradient, so a gradient defined
    on a unit vector and placed by its transform (as Affinity exports it) collapses to its last
    colour. Apply the matrix to the gradient end points. Gradients are matched by their stop
    offsets and colours, in document order."""
    ns = "{http://www.w3.org/2000/svg}"

    def offset(s):
        v = s.get("offset", "0").strip()
        return round(float(v[:-1]) / 100 if v.endswith("%") else float(v), 4)

    def stop_color(s):
        v = s.get("stop-color") or dict(
            p.split(":", 1) for p in s.get("style", "").replace(" ", "").split(";") if ":" in p).get("stop-color")
        try:
            return colors.toColor(v).hexval() if v else None
        except ValueError:
            return None

    def key(offsets, cols):
        return tuple(offsets), tuple(cols) if all(cols) else None

    fixes = {}
    for g in ET.parse(path).getroot().iter(ns + "linearGradient"):
        m = re.match(r"\s*matrix\(([^)]*)\)", g.get("gradientTransform", ""))
        if not m or g.get("gradientUnits") != "userSpaceOnUse":
            continue
        a, b, c, d, e, f = (float(v) for v in re.split(r"[\s,]+", m.group(1).strip()))
        x1, y1, x2, y2 = (float(g.get(k, dflt)) for k, dflt in (("x1", 0), ("y1", 0), ("x2", 1), ("y2", 0)))
        stops = list(g.iter(ns + "stop"))
        k = key([offset(s) for s in stops], [stop_color(s) for s in stops])
        fixes.setdefault(k, []).append((a * x1 + c * y1 + e, b * x1 + d * y1 + f,
                                        a * x2 + c * y2 + e, b * x2 + d * y2 + f))

    def walk(node):
        for ch in getattr(node, "contents", []):
            if type(ch).__name__ == "LinearGradientShape":
                k = key([round(p, 4) for p in ch._positions], [x.hexval() for x in ch._rl_colors])
                k = k if k in fixes else (k[0], None)
                if fixes.get(k):
                    ch._x0, ch._y0, ch._x1, ch._y1 = fixes[k].pop(0)
            walk(ch)
    if fixes:
        walk(drawing)


_SVG = {}


def load_svg(path):
    """svglib drawing of an SVG file (cached), with the gradient fix; exits with the path if unreadable."""
    if path not in _SVG:
        d = svg2rlg(path) if os.path.isfile(path) else None
        if d is None:
            fail(f"cannot read SVG: {path}")
        fix_svg_gradients(d, path)
        _SVG[path] = d
    return _SVG[path]


def image_size(path):
    if path.lower().endswith(".svg"):
        d = load_svg(path)
        return d.width, d.height
    try:
        return PILImage.open(path).size
    except Exception as ex:
        fail(f"cannot read image {path} ({ex.__class__.__name__})")


def draw_image(c, path, x, y_top, w=None, h=None):
    """Draw a PNG/JPG, or an SVG as vector graphics, with its top-left corner at (x, y_top).
    Give w or h; the other follows the aspect ratio. Returns (w, h)."""
    pw, ph = image_size(path)
    w = w if w is not None else h * pw / ph
    h = w * ph / pw
    if path.lower().endswith(".svg"):
        c.saveState(); c.translate(x, y_top - h); c.scale(w / pw, h / ph)
        renderPDF.draw(load_svg(path), c, 0, 0); c.restoreState()
    else:
        c.drawImage(path, x, y_top - h, w, h, mask="auto")
    return w, h


# ---------------------------------------------------------------- header and footer
def short_title(meta):
    """Header text, top-right: short title, then doc_no (or project) and the revision."""
    short = meta.get("short_title") or meta.get("title", "")
    ident = meta.get("doc_no") or meta.get("project")
    if ident:
        rev = LABELS["rev"].format(revision=meta["revision"]) if meta.get("revision") else ""
        short = f"{short}  ·  " + " ".join(x for x in (ident, rev) if x)
    return short


def left_footer(th, meta):
    return th["footer"] or " · ".join(x for x in (th["author"], meta.get("date")) if x)


def rule_line(c, th, page_w, y):
    if th["header_rule_color"]:
        c.setStrokeColor(colors.HexColor(th["header_rule_color"])); c.setLineWidth(LAYOUT.rule_w)
        c.line(LAYOUT.margin_l, y, page_w - LAYOUT.margin_r, y)


def draw_header_footer(c, th, page_w, page_h, short, left_foot, page_label=None):
    """Logo, short title and rule at the top (theme switch `header`); rule, author · date and the
    page label at the bottom."""
    L, muted = LAYOUT, colors.HexColor(th["muted_color"])
    y_logo = page_h - L.logo_top - L.logo_h
    if th["header"]:  # the top margin stays the same without it, so the layout does not move
        logo_w = draw_image(c, th["logo"], L.margin_l, y_logo + L.logo_h, h=L.logo_h)[0] if th["logo"] else 0
        room = page_w - L.margin_r - (L.margin_l + logo_w + L.head_gap)
        draw_text(c, page_w - L.margin_r, y_logo + L.head_raise, short, "Sans", L.head_size, muted,
                  align="right", max_w=room)
        rule_line(c, th, page_w, y_logo - L.head_rule_gap)
    rule_line(c, th, page_w, L.foot_rule_y)
    draw_text(c, L.margin_l, L.foot_y, left_foot, "Sans", L.foot_size, muted)
    if page_label:
        draw_text(c, page_w - L.margin_r, L.foot_y, page_label, "Sans", L.foot_size, muted, align="right")


def draw_stamp(c, page_w, th, n, total):
    """Book page number, centred in the footer."""
    draw_text(c, page_w / 2, LAYOUT.stamp_y, LABELS["stamp"].format(n=n, total=total), "Sans",
              LAYOUT.stamp_size, colors.HexColor(th["muted_color"]), align="centre")


# ---------------------------------------------------------------- cover page
ASSETS = os.path.join(report_figs.SKILL_DIR, "assets")


def same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def is_skill_logo(path):
    return bool(path) and same_path(path, os.path.join(ASSETS, "logo.png"))


def cover_logo(th):
    """Cover logo: the cover_logo key; else the vector assets/logo.svg while the theme uses the
    skill's own logo; else the theme logo (a custom theme keeps its own logo). None = no logo."""
    if th["cover_logo"] is not None:
        return th["cover_logo"] or None  # "" = cover_logo: none
    if is_skill_logo(th["logo"]) and os.path.exists(os.path.join(ASSETS, "logo.svg")):
        return os.path.join(ASSETS, "logo.svg")
    return th["logo"]


def _cut_warning(what, lines, kept):
    if len(lines) > kept:
        warn(f"cover {what} cut to {kept} lines; dropped: {' '.join(lines[kept:])}")


def draw_cover(c, th, meta, page_w, page_h, rows):
    """Cover page from the front matter (kicker, title, subtitle, project, specs, note, license)
    and `rows`, a list of (label, value) shown below the specs panel; empty values are skipped."""
    L, m = LAYOUT, meta
    ink, acc = colors.HexColor(th["text_color"]), colors.HexColor(th["accent_color"])
    muted, tint = colors.HexColor(th["muted_color"]), colors.HexColor(th["tint_light"])
    tw = page_w - L.margin_l - L.margin_r
    c.setFillColor(acc); c.rect(0, 0, L.strip_w, page_h, stroke=0, fill=1)
    logo = cover_logo(th)
    if logo:
        draw_image(c, logo, L.margin_l, page_h - L.cover_logo_top, w=L.cover_logo_w)
    if m.get("project"):
        draw_text(c, page_w - L.margin_r, page_h - L.project_top, LABELS["project"].format(project=m["project"]),
                  "Sans", L.project_size, muted, align="right")
    y = page_h - L.kicker_top
    if m.get("kicker"):
        draw_text(c, L.margin_l, y, m["kicker"].upper(), "Sans-Bold", L.kicker_size, acc)
        y -= L.kicker_gap
    lines = wrap(m.get("title", ""), "Sans-Bold", L.title_size, tw)
    _cut_warning("title", lines, L.title_lines)
    for line in lines[:L.title_lines]:
        draw_text(c, L.margin_l, y, line, "Sans-Bold", L.title_size, colors.HexColor(th["title_color"]))
        y -= L.title_lead
    y += L.subtitle_rise
    lines = wrap(m.get("subtitle", ""), "Sans", L.subtitle_size, tw)
    _cut_warning("subtitle", lines, L.subtitle_lines)
    for line in lines[:L.subtitle_lines]:
        draw_text(c, L.margin_l, y, line, "Sans", L.subtitle_size, muted)
        y -= L.subtitle_lead
    y -= L.title_rule_gap
    rule_line(c, th, page_w, y)
    items = [s.strip() for s in m.get("specs", "").split("|") if s.strip()]
    for s in items:
        if "=" not in s:
            warn(f"cover specs item '{s}' has no '=' and is left out (write Key = value)")
    specs = [s.split("=", 1) for s in items if "=" in s]
    if specs:
        y -= L.specs_drop
        c.setFillColor(tint); c.rect(L.margin_l, y, tw, L.specs_h, stroke=0, fill=1)
        c.setFillColor(acc); c.rect(L.margin_l, y, L.specs_bar, L.specs_h, stroke=0, fill=1)
        colw = (tw - L.specs_pad) / len(specs)
        for i, (k, v) in enumerate(specs):
            x, room = L.margin_l + L.specs_pad + i * colw, colw - L.specs_val_pad
            draw_text(c, x, y + L.specs_key_y, k.strip(), "Sans", L.specs_key_size, muted, max_w=room)
            size = fit_size(v.strip(), "Sans-Bold", L.specs_val_size, L.specs_val_min, room)
            draw_text(c, x, y + L.specs_val_y, v.strip(), "Sans-Bold", size, ink, max_w=room)
    y -= L.rows_drop
    for k, v in rows:
        if v:
            draw_text(c, L.margin_l, y, k, "Sans", L.row_label_size, muted)
            draw_text(c, L.margin_l + L.row_value_x, y, v, "Sans", L.row_value_size, ink,
                      max_w=tw - L.row_value_x)
            y -= L.row_lead
    rule_line(c, th, page_w, L.cover_rule_y)
    if m.get("note"):
        draw_text(c, L.margin_l, L.cover_note_y, m["note"], "Sans", L.cover_note_size, muted)
    if m.get("license"):
        draw_text(c, page_w - L.margin_r, L.cover_note_y, m["license"], "Sans", L.cover_note_size, muted,
                  align="right")
