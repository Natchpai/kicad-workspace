"""Figures for example_report.md, built with the template helpers.

Run from this folder:  python example_figures.py   -> fig_filter.svg, fig_bode.svg
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from report_figs import *  # noqa: F401,F403


def filter_schematic(path):
    s = Schematic(740, 300, 6.4)
    s.wire([(70, 158), (70, 100), (150, 100)])
    s.ind_h(150, 100)
    s.wire([(230, 100), (260, 100)])
    s.res_h(260, 100)
    s.wire([(324, 100), (665, 100), (665, 144)])
    s.wire([(410, 100), (410, 174)])
    s.cap_v(410, 174, 186)
    s.wire([(410, 186), (410, 260)])
    s.wire([(520, 100), (520, 130)])
    s.res_v(520, 130, c=BLUE, lw=1.8)
    s.wire([(520, 194), (520, 212)])
    s.cap_v(520, 212, 224, c=BLUE, lw=1.9)
    s.wire([(520, 224), (520, 260)])
    s.wire([(665, 216), (665, 260), (70, 260), (70, 202)])
    for p in [(410, 100), (520, 100), (410, 260), (520, 260)]:
        s.dot(*p)
    s.source(70, 180)
    s.ground(300, 260)
    s.box(140, 56, 196, 66, c=BLUE)
    s.text(190, 76, r"$L$", 15)
    s.text(292, 76, r"$r_L$", 15)
    s.text(238, 138, "Real inductor", 9.5, c=BLUE)
    s.text(102, 180, r"$V_{in}$", 15, ha="left")
    s.text(442, 180, r"$C$", 15, ha="left")
    s.text(540, 162, r"$R_d$", 15, ha="left")
    s.text(548, 218, r"$C_d$", 15, ha="left")
    s.box(596, 144, 138, 72, c=NAVY, ls="-", lw=1.2)
    s.text(665, 166, "Converter", 10.5, weight="semibold")
    s.text(665, 194, r"$R_n = -V_{in}^2/P$", 11.5)
    s.arrow(592, 242, 562, 242)
    s.text(600, 242, r"$Z_o$", 14, ha="left")
    s.save(path)


def bode(path, Vin=48, P=100, L=22e-6, C=10e-6, rL=0.02, Rd=1.06, Cd=150e-6):
    f0 = 1 / (2 * math.pi * math.sqrt(L * C))
    f = np.sort(np.concatenate([np.logspace(3, 5, 4001), [f0]]))
    w = 2 * np.pi * f
    yl = 1 / (rL + 1j * w * L)
    yc = 1j * w * C
    yd = 1 / (Rd + 1 / (1j * w * Cd))
    zu = np.abs(1 / (yl + yc))
    zd = np.abs(1 / (yl + yc + yd))
    rn = Vin ** 2 / P
    iu, idd = zu.argmax(), zd.argmax()
    margin = 20 * math.log10(rn / zd[idd])

    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    ax.loglog(f, zu, color=GRAY, lw=1.4, label="Undamped")
    ax.loglog(f, zd, color=BLUE, lw=2.3, label=r"Damped ($R_d$ + $C_d$)")
    ax.axhline(rn, color=NAVY, lw=1.1, ls=(0, (5, 4)))
    ax.text(9.6e4, rn * 1.12, rf"Converter $|Z_{{in}}| = |R_n|$ = {rn:.1f} $\Omega$",
            ha="right", va="bottom", fontsize=9, color=NAVY)
    ax.plot(f[iu], zu[iu], "o", color=GRAY, ms=4)
    ax.text(f[iu] * 1.08, zu[iu], f"Undamped peak {zu[iu]:.0f} Ω", fontsize=9, va="center", color="#4A5361")
    ax.plot(f[idd], zd[idd], "o", color=BLUE, ms=5.5)
    bx = 2.6e4
    ax.plot([bx, bx], [zd[idd], rn], color=BLACK, lw=0.9)
    for yv in (zd[idd], rn):
        ax.plot([bx / 1.06, bx * 1.06], [yv, yv], color=BLACK, lw=0.9)
    ym = math.sqrt(zd[idd] * rn)
    ax.text(bx * 1.12, ym * 1.18, f"{margin:.1f} dB margin", fontsize=9.5, weight="semibold", color=BLACK)
    ax.text(bx * 1.12, ym / 1.25, f"to damped peak {zd[idd]:.2f} Ω", fontsize=9, color="#4A5361")
    ax.set_xlim(1e3, 1e5)
    ax.set_ylim(0.1, 300)
    ax.set_xlabel("Frequency (Hz)", fontsize=9.5)
    ax.set_ylabel(r"$|Z_o|$ ($\Omega$)", fontsize=10)
    apply_plot_style(ax, legend_loc="upper left")
    plain_log_ticks(ax, x_unit="kHz", x_scale=1e3)
    fig.tight_layout()
    save_svg(fig, path)
    return dict(pu=zu[iu], pd=zd[idd], margin=margin)



if __name__ == "__main__":
    filter_schematic("fig_filter.svg")
    print(bode("fig_bode.svg"))
