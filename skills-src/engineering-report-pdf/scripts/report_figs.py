"""Figure helpers that match the report template.

Import from a figure script:
    import sys; sys.path.insert(0, "<skill>/scripts")
    from report_figs import *

Everything saves to SVG (vector) so build_report.py can embed it sharply.
"""
import math
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# Theme colours: the one palette for figures and pages (build_report.py imports these)
INK = "#16202E"      # all text: body, headings, labels (navy-black)
NAVY = "#1F2A3C"     # wires, outlines, reference lines (logo dark)
BLUE = "#1F63D6"     # accent: the one series / component the figure is about
BLUE_D = "#1A4FAF"   # small headings, note label
SKY = "#2AB4E6"      # secondary accent (logo light)
MUTED = "#5B6573"    # meta text, captions, equation numbers, header and footer
GRAY = "#8A94A3"     # de-emphasised series, annotations
BLACK = INK          # old name, kept so existing figure scripts still import it
BLUE_L = "#E7F0FC"   # table header fill
BLUE_LL = "#F4F8FE"  # equation panel, zebra rows
BLUE_LINE = "#BCD3F2"  # hairlines, note border
GRID = "#D5E3F5"
GRID_MINOR = "#EEF4FB"

# Use the bundled IBM Plex fonts if present (matplotlib also ships DejaVu Sans as a fallback)
import os as _os
from matplotlib import font_manager as _fm
_FD = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets", "fonts")
if _os.path.isdir(_FD):
    for _f in _os.listdir(_FD):
        if _f.endswith(".ttf"):
            _fm.fontManager.addfont(_os.path.join(_FD, _f))

plt.rcParams.update({
    "font.family": ["IBM Plex Sans", "DejaVu Sans"],
    "mathtext.fontset": "cm",
    "svg.fonttype": "path",
})


def apply_plot_style(ax, legend_loc=None):
    """Light-blue grid, soft spines, readable ticks."""
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


def equation(tex, path, size=15):
    """Render one display equation to SVG. Raises ValueError if mathtext cannot parse it."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex_to_mathtext(tex)}$", fontsize=size, color=BLACK)
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
