"""Figure helpers that match the report template.

Import from a figure script:
    import sys; sys.path.insert(0, "<skill>/scripts")
    from report_figs import *

Everything saves to SVG (vector) so build_report.py can embed it sharply.
"""
import difflib
import math
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------- theme
# Default values live in <skill>/theme.yml only. A report-theme.yml next to the report, then the
# report's front matter, override them. build_report.py uses load_theme() for the page.
SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEFAULT_THEME = os.path.join(SKILL_DIR, "theme.yml")
PROJECT_THEME = "report-theme.yml"

COLOR_KEYS = ("text_color", "accent_color", "muted_color", "heading_color", "number_color",
              "eq_color", "header_rule_color", "title_color")
SWITCH_KEYS = ("eq_numbers", "header", "title_rule")
THEME_KEYS = ("author", "logo", "footer", "eq_style") + COLOR_KEYS + SWITCH_KEYS
REPORT_KEYS = ("title", "subtitle", "short_title", "date", "doc_no", "revision", "paper",
               "subscripts", "italic_titles", "theme")
EQ_STYLES = ("panel", "bar", "plain")


def parse_kv(text):
    """Flat `key: value` lines (front matter or a theme file). `#` starts a comment, but a value
    that is a colour (`#1F63D6`) is kept. Quote a value to keep a literal ` #` in it."""
    out = {}
    for line in text.split("\n"):
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v and v[0] in "\"'" and v[0] in v[1:]:
            v = v[1:v.index(v[0], 1)]
        else:
            if v.startswith("#") and not re.match(r"#[0-9A-Fa-f]{6}(\s|$)", v):
                v = ""  # the whole value is a comment
            v = re.sub(r"\s+#.*$", "", v).strip()
        out[k.strip().lower()] = v
    return out


def _fail(msg):
    sys.exit(f"Theme error: {msg}")


def check_keys(d, where):
    for k in d:
        if k not in THEME_KEYS + REPORT_KEYS:
            near = difflib.get_close_matches(k, THEME_KEYS + REPORT_KEYS, n=1)
            _fail(f"unknown key '{k}' in {where}" + (f" (did you mean '{near[0]}'?)" if near else ""))


def _mix(hex_color, f, toward="#FFFFFF"):
    """Blend: f = share of hex_color, the rest is `toward` (white makes a tint, black a shade)."""
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(toward[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * f + y * (1 - f)):02X}" for x, y in zip(a, b))


def load_theme(layers):
    """Merge [(source_name, base_dir, dict), ...] from lowest to highest priority.
    Returns (theme, sources): resolved values (hex colours, booleans, absolute logo path or None)
    and the source of each key, for --show-theme."""
    raw, src, base = {}, {}, {}
    for name, folder, d in layers:
        check_keys(d, name)
        for k, v in d.items():
            if k in THEME_KEYS:
                raw[k], src[k], base[k] = v, name, folder
    missing = [k for k in THEME_KEYS if k not in raw]
    if missing:
        _fail(f"{DEFAULT_THEME} is missing {', '.join(missing)}")

    th = {"author": raw["author"], "footer": raw["footer"]}
    logo = raw["logo"]
    if logo.lower() == "none":
        th["logo"] = None
    else:
        th["logo"] = logo if os.path.isabs(logo) else os.path.normpath(os.path.join(base["logo"], logo))
        if not os.path.exists(th["logo"]):
            _fail(f"logo not found: {th['logo']} (logo: {logo}, set in {src['logo']})")

    hexre = re.compile(r"^#[0-9A-Fa-f]{6}$")
    for k in ("text_color", "accent_color", "muted_color"):
        if not hexre.match(raw[k]):
            _fail(f"{k}: '{raw[k]}' must be #RRGGBB (set in {src[k]})")
    names = {"text": raw["text_color"].upper(), "accent": raw["accent_color"].upper(),
             "muted": raw["muted_color"].upper()}
    for k in sorted(COLOR_KEYS, key=lambda k: k == "header_rule_color"):  # last: it may follow title_color
        v = raw[k].strip()
        if v.lower() in names:
            th[k] = names[v.lower()]
        elif hexre.match(v):
            th[k] = v.upper()
        elif v.lower() == "title" and k == "header_rule_color":
            th[k] = th["title_color"]
        elif v.lower() == "none" and k == "header_rule_color":
            th[k] = None
        else:
            allowed = "text, accent, muted, #RRGGBB" + (", title or none" if k == "header_rule_color" else "")
            _fail(f"{k}: '{v}' must be {allowed} (set in {src[k]})")
    for k in SWITCH_KEYS:
        v = raw[k].lower()
        if v not in ("on", "off", "true", "false", "yes", "no"):
            _fail(f"{k}: '{raw[k]}' must be on or off (set in {src[k]})")
        th[k] = v in ("on", "true", "yes")
    th["eq_style"] = raw["eq_style"].lower()
    if th["eq_style"] not in EQ_STYLES:
        _fail(f"eq_style: '{raw['eq_style']}' must be {', '.join(EQ_STYLES)} (set in {src['eq_style']})")

    acc, eq = th["accent_color"], th["eq_color"]
    th.update(accent_dark=_mix(acc, 0.82, "#000000"), tint=_mix(acc, 0.11), tint_light=_mix(acc, 0.05),
              hairline=_mix(acc, 0.30), grid=_mix(acc, 0.18), grid_minor=_mix(acc, 0.07),
              eq_fill=_mix(eq, 0.05))
    return th, src


def read_theme_file(path):
    with open(path, encoding="utf-8") as f:
        return parse_kv(f.read())


def default_layers():
    """The skill defaults, then report-theme.yml in the current folder if there is one."""
    layers = [(DEFAULT_THEME, SKILL_DIR, read_theme_file(DEFAULT_THEME))]
    if os.path.exists(PROJECT_THEME):
        p = os.path.abspath(PROJECT_THEME)
        layers.append((p, os.path.dirname(p), read_theme_file(p)))
    return layers


# Figure palette: theme colours from the layers above, plus fixed figure colours
_TH, _ = load_theme(default_layers())
INK = _TH["text_color"]        # all text: body, headings, labels
NAVY = "#1F2A3C"               # wires, outlines, reference lines (logo dark)
BLUE = _TH["accent_color"]     # accent: the one series / component the figure is about
BLUE_D = _TH["accent_dark"]    # small headings, note label
SKY = "#2AB4E6"                # secondary accent (logo light)
MUTED = _TH["muted_color"]     # meta text, captions, equation numbers, header and footer
GRAY = "#8A94A3"               # de-emphasised series, annotations
BLACK = INK                    # old name, kept so existing figure scripts still import it
BLUE_L = _TH["tint"]           # table header fill
BLUE_LL = _TH["tint_light"]    # equation panel, zebra rows
BLUE_LINE = _TH["hairline"]    # hairlines, note border
GRID = _TH["grid"]
GRID_MINOR = _TH["grid_minor"]

# Use the bundled IBM Plex fonts if present (matplotlib also ships DejaVu Sans as a fallback)
from matplotlib import font_manager as _fm
_FD = os.path.join(SKILL_DIR, "assets", "fonts")
if os.path.isdir(_FD):
    for _f in os.listdir(_FD):
        if _f.endswith(".ttf"):
            _fm.fontManager.addfont(os.path.join(_FD, _f))

plt.rcParams.update({
    "font.family": ["IBM Plex Sans", "DejaVu Sans"],
    "mathtext.fontset": "cm",
    "svg.fonttype": "path",
})


def apply_plot_style(ax, legend_loc=None):
    """Accent-tinted grid, soft spines, readable ticks."""
    ax.grid(True, which="major", color=GRID, lw=0.8)
    ax.grid(True, which="minor", color=GRID_MINOR, lw=0.6)
    ax.tick_params(labelsize=8.5, colors=INK)
    for sp in ax.spines.values():
        sp.set_color("#9AA8BC")
    if legend_loc:
        ax.legend(loc=legend_loc, fontsize=8.5, frameon=False)


def plain_log_ticks(ax, x_unit=None, x_scale=1.0):
    """Log axes labelled 0.1, 1, 10 ... instead of 10^n. Optional unit on x (e.g. 'kHz', scale 1e3)."""
    from matplotlib.ticker import FuncFormatter, NullFormatter
    if x_unit:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / x_scale:g} {x_unit}"))
    else:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())


def save_svg(fig, path, tight=True):
    fig.savefig(path, transparent=True, bbox_inches="tight" if tight else None, pad_inches=0.05)
    plt.close(fig)


def latex_to_mathtext(tex):
    """Adapt common LaTeX to matplotlib mathtext."""
    tex = tex.strip()
    tex = tex.replace(r"\tfrac", r"\frac").replace(r"\dfrac", r"\frac")
    tex = re.sub(r"\\frac(?![a-zA-Z])", r"\\dfrac", tex)
    tex = tex.replace(r"\operatorname{", r"\mathrm{").replace(r"\text{", r"\mathrm{")
    tex = tex.replace(r"\displaystyle", "")
    tex = re.sub(r"\\le(?![a-zA-Z])", r"\\leq", tex)
    tex = re.sub(r"\\ge(?![a-zA-Z])", r"\\geq", tex)
    tex = re.sub(r"\\ne(?![a-zA-Z])", r"\\neq", tex)
    tex = tex.replace(r"\left\{", r"\{").replace(r"\right\}", r"\}")
    return tex


def equation(tex, path, size=15, color=None):
    """Render one display equation to SVG. Raises ValueError if mathtext cannot parse it."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex_to_mathtext(tex)}$", fontsize=size, color=color or INK)
    try:
        fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0.04)
    finally:
        plt.close(fig)


class Schematic:
    """Minimal circuit / block drawing on an SVG-like canvas (x right, y DOWN, units ~ px).

    s = Schematic(700, 290)          # canvas size in units
    s.wire([(80,90),(110,90)]); s.res_h(110, 90); s.ind_h(210, 90); s.cap_v(460,154,166)
    s.text(142, 66, r"$R_s$"); s.save("fig.svg")
    Components: res_h (64 long), res_v (64 tall), ind_h (n humps x 20), cap_v, source, ground,
    dot, box (dashed group or solid block), arrow, text (mathtext allowed).
    """

    def __init__(self, w, h, inch_w=6.4):
        self.fig = plt.figure(figsize=(inch_w, inch_w * h / w))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)
        self.ax.set_aspect("equal")
        self.ax.axis("off")

    def wire(self, pts, c=NAVY, lw=1.4, ls="-"):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=c, lw=lw, ls=ls, solid_capstyle="round", solid_joinstyle="round")

    def res_h(self, x0, y, c=NAVY, lw=1.4):
        pts, x, s = [(x0, y), (x0 + 4, y - 8)], x0 + 4, 1
        for _ in range(7):
            x += 8; pts.append((x, y + 8 * s)); s = -s
        pts.append((x0 + 64, y)); self.wire(pts, c, lw)

    def res_v(self, x, y0, c=NAVY, lw=1.4):
        pts, y, s = [(x, y0), (x + 8, y0 + 4)], y0 + 4, -1
        for _ in range(7):
            y += 8; pts.append((x + 8 * s, y)); s = -s
        pts.append((x, y0 + 64)); self.wire(pts, c, lw)

    def ind_h(self, x0, y, n=4, r=10, c=NAVY, lw=1.4):
        for i in range(n):
            cx = x0 + r + 2 * r * i
            th = np.linspace(math.pi, 0, 40)
            self.ax.plot(cx + r * np.cos(th), y - r * np.sin(th), color=c, lw=lw)

    def cap_v(self, x, y1, y2, half=20, c=NAVY, lw=1.6):
        self.wire([(x - half, y1), (x + half, y1)], c, lw)
        self.wire([(x - half, y2), (x + half, y2)], c, lw)

    def source(self, x, y, r=22):
        self.ax.add_patch(plt.Circle((x, y), r, fill=False, ec=NAVY, lw=1.4))
        t = np.linspace(-12, 12, 60)
        self.ax.plot(x + t, y - 6 * np.sin(t / 12 * math.pi), color=NAVY, lw=1.3)

    def ground(self, x, y):
        self.wire([(x, y), (x, y + 12)])
        for half, dy in [(14, 12), (8, 18), (3, 24)]:
            self.wire([(x - half, y + dy), (x + half, y + dy)])

    def dot(self, x, y):
        self.ax.add_patch(plt.Circle((x, y), 3, color=NAVY))

    def text(self, x, y, s, size=14, ha="center", va="center", c=BLACK, **kw):
        self.ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, **kw)

    def box(self, x, y, w, h, c=BLUE, ls="--", lw=0.9, r=8):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                         fill=False, ec=c, lw=lw, ls=ls))

    def arrow(self, x1, y1, x2, y2, c=NAVY):
        self.ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                         arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2, mutation_scale=12))

    def save(self, path):
        save_svg(self.fig, path)
