"""Figures for buck_converter_design_report.md (engineering-report-pdf skill helpers).

Run:  python figures.py   -> fig_loss_breakdown.svg, fig_efficiency.svg, fig_input_filter_bode.svg
Set SKILL_DIR if the skill is not at ~/.claude/skills/engineering-report-pdf.
All values are the draft's assumed values; edit them here and rerun.
"""
import math, os, sys
SKILL_DIR = os.environ.get("SKILL_DIR", os.path.expanduser("~/.claude/skills/engineering-report-pdf"))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
from report_figs import *  # noqa: F401,F403

# ---- Converter and assumed IC values (Sections 1, 4, 7)
VIN, VO, IO, FSW, L = 5.0, 3.3, 2.0, 2.2e6, 1.0e-6
RDS_H, RDS_L, DCR = 0.080, 0.050, 0.025      # ohm
T_SW, T_DT, V_BD, P_FIX = 4e-9, 5e-9, 0.7, 0.015

# ---- Example input filter (Section 8.5)
LF, CF, RF = 1.0e-6, 10e-6, 0.015


def losses(io, vin=VIN):
    d = VO / vin
    di = VO * (1 - d) / (L * FSW)
    i2 = io ** 2 + di ** 2 / 12
    return {
        "MOSFET conduction": i2 * (d * RDS_H + (1 - d) * RDS_L),
        "Inductor DCR": i2 * DCR,
        "Switching": 0.5 * vin * io * T_SW * FSW,
        "Dead time": V_BD * io * 2 * T_DT * FSW,
        "Gate drive and quiescent": P_FIX,
    }


def loss_breakdown(path):
    lo = losses(IO)
    names, vals = list(lo)[::-1], list(lo.values())[::-1]
    total = sum(vals)
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    colors = [BLUE if v == max(vals) else GRAY for v in vals]
    ax.barh(names, vals, color=colors, height=0.62)
    for y, v in enumerate(vals):
        ax.text(v + 0.004, y, f"{v * 1e3:.0f} mW · {v / total * 100:.0f} %", va="center", fontsize=9, color=BLACK)
    ax.set_xlim(0, 0.36)
    ax.set_xlabel("Loss (W)", fontsize=9.5)
    ax.grid(True, axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=9, colors="#333333")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for sp in ax.spines.values():
        sp.set_color("#9AA8BC")
    fig.tight_layout()
    save_svg(fig, path)
    return total


def efficiency(path):
    io = np.linspace(0.05, IO, 391)
    eta = np.array([100 * VO * i / (VO * i + sum(losses(i).values())) for i in io])
    k = int(eta.argmax())
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.plot(io, eta, color=BLUE, lw=2.3)
    ax.plot(io[k], eta[k], "o", color=BLUE, ms=6)
    ax.plot(io[-1], eta[-1], "o", color=BLUE, ms=6, clip_on=False)   # sits on the right axis edge
    ax.annotate(f"Peak {eta[k]:.1f} % at {io[k]:.2f} A", (io[k], eta[k]), xytext=(0, 10),
                textcoords="offset points", ha="center", fontsize=9, weight="semibold")
    ax.annotate(f"{eta[-1]:.1f} % at {IO:g} A", (io[-1], eta[-1]), xytext=(-6, -16),
                textcoords="offset points", ha="right", fontsize=9)
    ax.text(0.12, 89.0, "Fixed losses dominate", fontsize=8.5, color="#4A5361")
    ax.text(1.25, 96.6, "I²R losses dominate", fontsize=8.5, color="#4A5361")
    ax.set_xlim(0, IO)
    ax.set_ylim(88, 98)
    ax.set_xlabel("Output current, Io (A)", fontsize=9.5)
    ax.set_ylabel("Efficiency (%)", fontsize=9.5)
    apply_plot_style(ax)
    fig.tight_layout()
    save_svg(fig, path)
    return eta[k], io[k], eta[-1]


def input_filter_bode(path):
    pin = VO * IO + sum(losses(IO).values())
    rn = VIN ** 2 / pin
    f0 = 1 / (2 * math.pi * math.sqrt(LF * CF))
    f = np.sort(np.concatenate([np.logspace(4, 7, 6001), [f0]]))
    w = 2 * np.pi * f
    zo = np.abs(1 / (1 / (RF + 1j * w * LF) + 1j * w * CF))
    k = int(zo.argmax())
    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    ax.loglog(f, zo, color=BLUE, lw=2.3)
    ax.axhline(rn, color=NAVY, lw=1.1, ls=(0, (5, 4)))
    ax.text(FSW / 1.15, rn / 1.15, rf"Converter $|R_n| = V_{{in}}^2/P_{{in}}$ = {rn:.1f} $\Omega$",
            ha="right", va="top", fontsize=8.5, color=NAVY)      # ends left of the fsw line
    ax.plot(f[k], zo[k], "o", color=BLUE, ms=6)
    ax.text(f[k] * 1.15, 25,                                     # between the 10 and 100 gridlines
            f"Peak {zo[k]:.2f} Ω at {f[k] / 1e3:.1f} kHz\n"
            rf"{20 * math.log10(zo[k] / rn):.1f} dB above $|R_n|$, unstable",
            va="center", fontsize=8.5, weight="semibold", color=BLACK)
    ax.axvline(FSW, color=GRAY, lw=0.9, ls=(0, (2, 3)))
    ax.text(FSW * 1.08, 0.2, f"fsw = {FSW / 1e6:g} MHz", fontsize=8.5, color="#4A5361")
    ax.set_xlim(1e4, 1e7)
    ax.set_ylim(1e-3, 100)
    ax.set_xlabel("Frequency", fontsize=9.5)
    ax.set_ylabel(r"$|Z_o|$ ($\Omega$)", fontsize=10)
    plain_log_ticks(ax)
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e6:g} MHz" if v >= 1e6 else f"{v / 1e3:g} kHz"))
    apply_plot_style(ax)
    fig.tight_layout()
    save_svg(fig, path)
    return zo[k], f[k], rn


if __name__ == "__main__":
    print("total loss W", loss_breakdown("fig_loss_breakdown.svg"))
    print("efficiency", efficiency("fig_efficiency.svg"))
    print("filter", input_filter_bode("fig_input_filter_bode.svg"))
