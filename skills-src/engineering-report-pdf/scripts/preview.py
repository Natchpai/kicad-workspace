#!/usr/bin/env python3
"""Render PDF pages to PNG so the layout can be checked by eye.

Usage:
    python preview.py report.pdf outdir [--dpi 80]           -> outdir/p-1.png, p-2.png ...
    python preview.py book.pdf outdir --pages 1-3,7          -> only those pages
    python preview.py book.pdf outdir --sheet 8              -> outdir/sheet-1.png ... (8 pages per image)

Old p-*.png and sheet-*.png files in outdir are deleted first, so the folder holds only this PDF.
A sheet tiles pages in a grid with the page number under each: check a long book in a few image
reads, then render single pages at full size where something looks wrong.
Uses pypdfium2 (in requirements.txt); falls back to poppler's pdftoppm if it is not installed.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile

SHEET_COLS = 4          # pages per row on a contact sheet
SHEET_PAD = 12          # px between pages and around the sheet
SHEET_LABEL = 18        # px band under each page for its number


def parse_pages(spec, n):
    """'1-3,7' -> [1, 2, 3, 7] (1-based, clipped to the page count); None -> every page."""
    if not spec:
        return list(range(1, n + 1))
    out = []
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
        if not m:
            sys.exit(f"--pages: '{part}' must be N or N-M")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        out += [p for p in range(a, b + 1) if 1 <= p <= n and p not in out]
    return out


def clear(outdir):
    for f in os.listdir(outdir):
        if re.fullmatch(r"(p|sheet)-\d+\.png", f):
            os.remove(os.path.join(outdir, f))


def render(pdf, outdir, dpi, pages=None):
    """Render pages (a '1-3,7' spec or None for all) to outdir/p-N.png. Returns the file names."""
    os.makedirs(outdir, exist_ok=True)
    clear(outdir)
    try:
        import pypdfium2 as pdfium
    except ImportError:
        exe = shutil.which("pdftoppm")
        if not exe:
            sys.exit("No renderer: pip install pypdfium2 (or install poppler for pdftoppm), or open the PDF by hand.")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([exe, "-r", str(dpi), "-png", pdf, os.path.join(tmp, "p")], check=True)
            files = {int(re.search(r"(\d+)\.png$", f).group(1)): f for f in os.listdir(tmp)}
            names = []
            for p in parse_pages(pages, max(files)):
                shutil.move(os.path.join(tmp, files[p]), os.path.join(outdir, f"p-{p}.png"))
                names.append(f"p-{p}.png")
            return names
    doc = pdfium.PdfDocument(pdf)
    names = []
    for p in parse_pages(pages, len(doc)):
        name = f"p-{p}.png"
        doc[p - 1].render(scale=dpi / 72).to_pil().save(os.path.join(outdir, name))
        names.append(name)
    doc.close()
    return names


def sheets(outdir, names, per_sheet):
    """Tile the rendered pages into outdir/sheet-N.png, per_sheet pages each; the single page
    files are removed. Returns the sheet file names."""
    from PIL import Image, ImageDraw
    out = []
    for s in range(0, len(names), per_sheet):
        group = names[s:s + per_sheet]
        imgs = [Image.open(os.path.join(outdir, n)) for n in group]
        w, h = max(i.width for i in imgs), max(i.height for i in imgs)
        cols = min(SHEET_COLS, len(imgs))
        rows = -(-len(imgs) // cols)
        sheet = Image.new("RGB", (SHEET_PAD + cols * (w + SHEET_PAD),
                                  SHEET_PAD + rows * (h + SHEET_LABEL + SHEET_PAD)), "#9AA3AE")
        d = ImageDraw.Draw(sheet)
        for k, (n, im) in enumerate(zip(group, imgs)):
            x = SHEET_PAD + (k % cols) * (w + SHEET_PAD)
            y = SHEET_PAD + (k // cols) * (h + SHEET_LABEL + SHEET_PAD)
            sheet.paste(im, (x, y))
            d.text((x + w // 2 - 10, y + h + 3), n[2:-4], fill="black")
            im.close()
        name = f"sheet-{len(out) + 1}.png"
        sheet.save(os.path.join(outdir, name))
        out.append(name)
    for n in names:
        os.remove(os.path.join(outdir, n))
    return out


def preview(pdf, outdir, dpi=80, pages=None, sheet=0):
    names = render(pdf, outdir, dpi, pages)
    return sheets(outdir, names, sheet) if sheet else names


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf"); ap.add_argument("outdir")
    ap.add_argument("--dpi", type=int, default=80)
    ap.add_argument("--pages", help="pages to render, e.g. 1-3,7 (default: all)")
    ap.add_argument("--sheet", type=int, default=0, metavar="N", help="tile N pages per contact-sheet image")
    a = ap.parse_args()
    for n in preview(a.pdf, a.outdir, a.dpi, a.pages, a.sheet):
        print(os.path.join(a.outdir, n))
