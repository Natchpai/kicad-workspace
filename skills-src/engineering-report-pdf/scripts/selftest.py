#!/usr/bin/env python3
"""Selftest of the skill: run it after editing any script, theme.yml or a page_layout value.

Usage:
    python selftest.py              # temporary folder, deleted at the end
    python selftest.py out_dir      # keep the PDFs and inputs in out_dir to look at them

Builds the bundled example, the fixtures in ../references/selftest (every dialect construct,
an alternative theme, a book) and a set of broken inputs, and checks exit codes, messages,
page counts, page sizes, equation labels, contents and bookmark pages, preview.py and the
figure helpers. Prints PASS or FAIL per case and exits with 1 if any case failed.
It writes nothing outside the output folder.
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REFS = os.path.join(SKILL, "references")
FIX = os.path.join(REFS, "selftest")
sys.path.insert(0, HERE)

from pypdf import PdfReader  # noqa: E402

RESULTS = []


def run(script, *args, cwd=None):
    """Run a skill script; returns (exit code, stdout + stderr)."""
    p = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n      {detail.strip()[-600:]}"))


def text(pdf, page=None):
    r = PdfReader(pdf)
    pages = r.pages if page is None else [r.pages[page]]
    return "\n".join(p.extract_text() or "" for p in pages)


def norm(s):
    return re.sub(r"[\W_]+", "", s).lower()


def write(folder, name, content):
    p = os.path.join(folder, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return p


# ---------------------------------------------------------------- good builds
def good_builds(out):
    buck = os.path.join(REFS, "buck_converter_design_report.md")
    pdf = os.path.join(out, "buck.pdf")
    code, log = run("build_report.py", buck, pdf, "--strict")
    check("buck example builds with no warning", code == 0, log)

    feat = os.path.join(out, "features.pdf")
    code, log = run("build_report.py", os.path.join(FIX, "features.md"), feat, "--strict")
    check("features.md (every construct) builds with no warning", code == 0, log)
    if code == 0:
        t = text(feat)
        check("labels: (@rd) (@z0) (@f0) become (2) (1) (3)",
              "follows Eq. (2)" in t and "impedance of Eq. (1)" in t and "Eq. (3) is the third" in t
              and "(@" not in t and "(??)" not in t, t[:800])
        r = PdfReader(feat)
        n = len(r.pages)
        check("pages: full (default) = cover, contents, report numbered as one document",
              "Page" not in text(feat, 0) and "Contents" in text(feat, 1) and f"Page 3 of {n}" in text(feat, 2)
              and not re.search(r"\d+ / \d+", text(feat, 2)), text(feat, 1) + text(feat, 2))
        contents = text(feat, 1)
        bad = [f"{s.title} p{r.get_destination_page_number(s) + 1}" for s in r.outline[3]
               if not re.search(rf"{re.escape(s.title)}[\s.]*{r.get_destination_page_number(s) + 1}\b", contents)
               or norm(s.title[3:])[:15] not in norm(text(feat, r.get_destination_page_number(s)))]
        check("pages: full contents numbers and bookmarks point at the section pages", not bad, "; ".join(bad))
        for pages, front in (("cover", 1), ("content", 0)):
            pdf = os.path.join(out, f"features_{pages}.pdf")
            code, log = run("build_report.py", os.path.join(FIX, "features.md"), pdf, "--pages", pages)
            ok = code == 0 and len(PdfReader(pdf).pages) == n - 2 + front and "Page 1 of" in text(pdf, front)
            check(f"--pages {pages}: {'cover page, then' if front else 'only'} the report", ok, log)

    plain = os.path.join(out, "plain.pdf")
    code, log = run("build_report.py", os.path.join(FIX, "plain.md"), plain, "--strict")
    check("plain.md (alternative theme file) builds", code == 0, log)
    if code == 0:
        r = PdfReader(plain)
        box = r.pages[0].mediabox
        check("paper: letter from the theme file", (round(float(box.width)), round(float(box.height))) == (612, 792),
              str(box))
        check("title from the first # line outside code fences",
              r.metadata.title == "Plain Style Check", str(r.metadata.title))
        check("header: off leaves no short title at the top", "Plain Style Check  ·" not in text(plain))

    a4 = os.path.join(out, "plain_a4.pdf")
    code, log = run("build_report.py", os.path.join(FIX, "plain.md"), a4, "--set", "paper=a4",
                    "--set", "eq_style=plain", "--set", "eq_numbers=on")
    check("--set paper=a4 overrides the theme file",
          code == 0 and round(float(PdfReader(a4).pages[0].mediabox.width)) == 595, log)
    code, log = run("build_report.py", os.path.join(FIX, "plain.md"), "--show-theme", "--set", "eq_style=panel")
    check("--show-theme names the theme file and the command line",
          code == 0 and re.search(r"eq_style\s+panel\s+command line", log) and "alt-theme.yml" in log, log)

    book = os.path.join(out, "book.pdf")
    code, log = run("build_book.py", os.path.join(FIX, "book.md"), book, "--strict")
    check("book.md builds with no warning", code == 0, log)
    if code == 0:
        check_book(book, log)


def check_book(book, log):
    r = PdfReader(book)
    m = re.search(r"(\d+) pages, (\d+) reports, (\d+) contents page", log)
    check("book page count = cover + contents + reports",
          bool(m) and int(m.group(1)) == len(r.pages), log)
    check("book cover shows the Document row", "ST-BOOK" in text(book, 0), text(book, 0))
    check("book contents runs over more than one page", bool(m) and int(m.group(3)) >= 2, log)
    bad = []

    def walk(items, depth=0):
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
                continue
            page = r.get_destination_page_number(it)
            title = it.title
            if title in ("Cover", "Contents"):
                continue
            # the heading text (without its number) must be on the page the bookmark opens
            want = norm(re.sub(r"^\d+\.\s*", "", title))[:20]
            if want not in norm(text(book, page)):
                bad.append(f"{title} -> p{page + 1}")
    walk(r.outline)
    check("every bookmark opens the page that holds its heading", not bad, "; ".join(bad))
    stamp = text(book, 1)
    check("contents page carries the book page stamp", re.search(r"2 / \d+", stamp) is not None, stamp)


# ---------------------------------------------------------------- broken inputs
FRONT = "---\ntitle: Broken input\n{extra}---\n\n"
ERRORS = [  # name, front matter lines, body, expected message (exit code must be non-zero)
    ("unknown key with a near match", "eq_stlye: bar\n", "Text.\n", "did you mean 'eq_style'"),
    ("bad colour", "accent_color: blue\n", "Text.\n", "accent_color: 'blue' must be #RRGGBB"),
    ("bad switch", "header: maybe\n", "Text.\n", "header: 'maybe' must be on or off"),
    ("bad choice", "paper: a3\n", "Text.\n", "paper: 'a3' must be a4, letter"),
    ("missing figure", "", "![Cap](nope.svg)\n", "Figure not found: nope.svg (line 5"),
    ("missing theme file", "theme: nope.yml\n", "Text.\n", "theme file not found"),
    ("missing logo", "logo: nope.png\n", "Text.\n", "logo not found"),
    ("unclosed $$", "", "Text.\n\n$$ x = 1\n\nmore\n", "Unclosed $$ starting at line 7"),
    ("unclosed ``` fence", "", "Text.\n\n```python\nx = 1\n", "Unclosed ``` starting at line 7"),
    ("old cover key", "cover: on\n", "Text.\n", "replaced by pages: full, cover or content"),
]
WARNINGS = [  # name, front matter lines, body, expected warning (--strict must exit 1)
    ("unknown label", "", "See (@nope).\n", "(@nope) not found"),
    ("hand-written Eq. number out of range", "", "$$ x = 1 $$\n\nSee Eq. (4).\n", "the report has 1 numbered equations"),
    ("duplicate label", "", "$$ x = 1 \\label{a} $$\n\n$$ y = 2 \\label{a} $$\n", "used twice"),
    ("label on an unnumbered equation", "", "$$ x = 1 \\nonumber \\label{a} $$\n", "unnumbered equation"),
    ("TeX mathtext cannot render", "", "$$ \\begin{aligned} x &= 1 \\end{aligned} $$\n", "equation not rendered"),
    ("nested list", "", "- one\n  - nested\n", "nested list item flattened"),
    ("image line with extra text", "", "![Cap](fig.svg) trailing words\n", "image line not understood"),
    ("cover specs item without =", "specs: Input = 5 V | broken\n", "Text.\n", "has no '='"),
    ("cover title cut", "", "Text.\n", "cover title cut"),
]


def broken_inputs(out):
    d = os.path.join(out, "broken")
    os.makedirs(d, exist_ok=True)
    for k, (name, extra, body, want) in enumerate(ERRORS):
        md = write(d, f"err{k}.md", FRONT.format(extra=extra) + body)
        code, log = run("build_report.py", md, os.path.join(d, f"err{k}.pdf"))
        check(f"error: {name}", code != 0 and want in log, log)
    for k, (name, extra, body, want) in enumerate(WARNINGS):
        front = FRONT.format(extra=extra)
        if name == "cover title cut":
            front = front.replace("Broken input", "A very long cover title " * 6)
        md = write(d, f"warn{k}.md", front + body)
        code, log = run("build_report.py", md, os.path.join(d, f"warn{k}.pdf"), "--strict")
        check(f"warning under --strict: {name}", code == 1 and want in log, log)
    code, log = run("build_report.py", write(d, "ok.md", FRONT.format(extra="") + "Text.\n"),
                    os.path.join(d, "ok.pdf"), "--set", "colour=red")
    check("error: unknown --set key", code != 0 and "unknown key 'colour'" in log, log)

    write(d, "report-theme.yml", "accent_color: #0F8A5F\n")
    code, log = run("build_report.py", os.path.join(d, "ok.md"), "--show-theme")
    check("report-theme.yml next to the report is a theme layer",
          code == 0 and re.search(r"accent_color\s+#0F8A5F\s+\S*report-theme\.yml", log) is not None, log)

    for name, body, want in [("book: missing report", "---\ntitle: B\n---\n- nope.md\n", "report not found: nope.md"),
                             ("book: no reports", "---\ntitle: B\n---\nNothing here.\n", "no reports listed"),
                             ("book: no title", "---\nkicker: K\n---\n- ok.md\n", "no title in the front matter")]:
        code, log = run("build_book.py", write(d, "book.md", body), os.path.join(d, "book.pdf"))
        check(f"error: {name}", code != 0 and want in log, log)
    pdf = os.path.join(d, "book.pdf")
    code, log = run("build_book.py", write(d, "book.md", "---\ntitle: B\n---\n- ok.md\n"), pdf,
                    "--set", "footer=Footer from set", "--set", "page_stamp=off")
    last = text(pdf, -1) if code == 0 else ""
    check("book --set: theme keys reach the reports, page_stamp=off drops the stamp",
          code == 0 and "Footer from set" in last and not re.search(r"\d+ / \d+", last), log + last)


# ---------------------------------------------------------------- preview and figures
def preview_and_figures(out):
    pdf = os.path.join(out, "features.pdf")
    if os.path.exists(pdf):
        pv = os.path.join(out, "preview")
        os.makedirs(pv, exist_ok=True)
        open(os.path.join(pv, "p-99.png"), "wb").close()  # left over from an earlier, longer PDF
        code, log = run("preview.py", pdf, pv, "--pages", "1-2", "--dpi", "30")
        files = sorted(os.listdir(pv))
        check("preview.py --pages renders those pages and clears old files", code == 0 and files == ["p-1.png", "p-2.png"],
              log + str(files))
        code, log = run("preview.py", pdf, pv, "--sheet", "4", "--dpi", "30")
        files = sorted(os.listdir(pv))
        n = len(PdfReader(pdf).pages)
        check("preview.py --sheet tiles the pages", code == 0 and len(files) == -(-n // 4)
              and all(f.startswith("sheet-") for f in files), log + str(files))

    figs = os.path.join(out, "figures")
    os.makedirs(figs, exist_ok=True)
    write(figs, "report-theme.yml", "accent_color: #0F8A5F\n")
    write(figs, "fig.py", f"""import sys, numpy as np
sys.path.insert(0, {HERE!r})
from report_figs import *
assert BLUE == "#0F8A5F", BLUE
s = Schematic(400, 200)
s.wire([(10, 100), (40, 100)]); s.res_h(40, 100); s.res_v(200, 20); s.ind_h(110, 100)
s.cap_v(300, 90, 100); s.source(30, 150); s.ground(300, 110); s.dot(40, 100)
s.box(5, 5, 390, 190); s.arrow(10, 10, 60, 10); s.text(150, 60, r"$R_d$", weight="semibold")
s.save("schematic.svg")
fig, ax = plt.subplots()
x = np.logspace(1, 5, 50); ax.loglog(x, 1 / x, color=BLUE)
plain_log_ticks(ax, x_unit="kHz", x_scale=1e3); apply_plot_style(ax)
save_svg(fig, "plot.svg")
equation(r"\\frac{{a}}{{b}} \\le c", "eq.svg")
try:
    equation(r"\\begin{{aligned}} x \\end{{aligned}}", "bad.svg")
    sys.exit("bad TeX did not raise")
except ValueError:
    pass
print("figures ok")
""")
    p = subprocess.run([sys.executable, "fig.py"], cwd=figs, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    log = p.stdout + p.stderr
    check("report_figs: theme from report-theme.yml, every Schematic part, log ticks, equation()",
          p.returncode == 0 and "figures ok" in log and all(os.path.exists(os.path.join(figs, f))
                                                           for f in ("schematic.svg", "plot.svg", "eq.svg")), log)
    check("report_figs: no matplotlib font warnings", "findfont" not in log, log)


if __name__ == "__main__":
    keep = sys.argv[1] if len(sys.argv) > 1 else None
    out = os.path.abspath(keep) if keep else tempfile.mkdtemp(prefix="report_selftest_")
    os.makedirs(out, exist_ok=True)
    try:
        good_builds(out)
        broken_inputs(out)
        preview_and_figures(out)
    finally:
        if not keep:
            shutil.rmtree(out, ignore_errors=True)
    failed = RESULTS.count(False)
    print(f"\n{len(RESULTS) - failed} passed, {failed} failed" + (f"; files in {out}" if keep else ""))
    sys.exit(1 if failed else 0)
