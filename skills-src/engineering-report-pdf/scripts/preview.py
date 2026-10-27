#!/usr/bin/env python3
"""Render each PDF page to a PNG so the layout can be checked by eye.

Usage:
    python preview.py report.pdf outdir [--dpi 80]     -> outdir/p-1.png, p-2.png ...

Uses pypdfium2 (in requirements.txt); falls back to poppler's pdftoppm if it is not installed.
"""
import argparse, os, shutil, subprocess, sys


def render(pdf, outdir, dpi):
    os.makedirs(outdir, exist_ok=True)
    try:
        import pypdfium2 as pdfium
    except ImportError:
        exe = shutil.which("pdftoppm")
        if not exe:
            sys.exit("No renderer: pip install pypdfium2 (or install poppler for pdftoppm), or open the PDF by hand.")
        subprocess.run([exe, "-r", str(dpi), "-png", pdf, os.path.join(outdir, "p")], check=True)
        return sorted(f for f in os.listdir(outdir) if f.startswith("p-") and f.endswith(".png"))
    doc = pdfium.PdfDocument(pdf)
    names = []
    for i, page in enumerate(doc, 1):
        name = f"p-{i}.png"
        page.render(scale=dpi / 72).to_pil().save(os.path.join(outdir, name))
        names.append(name)
    doc.close()
    return names


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf"); ap.add_argument("outdir")
    ap.add_argument("--dpi", type=int, default=80)
    a = ap.parse_args()
    for n in render(a.pdf, a.outdir, a.dpi):
        print(os.path.join(a.outdir, n))
