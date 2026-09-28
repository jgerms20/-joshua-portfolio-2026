#!/usr/bin/env python3
"""Re-encode heavy images the site actually references into web-sized files.

Originals are moved (not deleted) to media-originals/<same path> so full-
resolution files stay available for print production. Pages keep pointing
at the same paths, so no markup changes are needed for JPEG/WebP. Heavy
PNG photographs are converted to JPEG and their references rewritten.

Usage: python3 scripts/optimize-images.py [--dry-run]
"""
import glob, html, os, re, shutil, sys
from urllib.parse import unquote, quote
from PIL import Image, ImageOps

THRESHOLD = 700 * 1024      # only touch files heavier than this
MAX_EDGE = 2200             # long edge in px after resize
QUALITY = 80
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'media-originals')
DRY = '--dry-run' in sys.argv

def pages():
    out = ['index.html', 'shop.html']
    for d in ('work', 'podcasts', 'media'):
        out += [p for p in glob.glob(f'{d}/*.html') if 'template' not in p]
    return out

def referenced():
    refs = {}
    for p in pages():
        c = open(os.path.join(ROOT, p), encoding='utf-8').read()
        base = os.path.dirname(p)
        for u in re.findall(r'(?:src|poster|data-src|data-fallbacks)="([^"]+)"', c):
            for tok in u.split():
                if tok.startswith(('http', '//', 'data:', 'yt:')):
                    continue
                if not re.search(r'\.(jpe?g|png|webp)$', tok, re.I):
                    continue
                f = os.path.normpath(os.path.join(base, unquote(html.unescape(tok))))
                if os.path.exists(os.path.join(ROOT, f)):
                    refs.setdefault(f, set()).add(p)
    return refs

def main():
    os.chdir(ROOT)
    refs = referenced()
    saved = 0
    for f, ps in sorted(refs.items()):
        size = os.path.getsize(f)
        if size <= THRESHOLD:
            continue
        im = Image.open(f)
        im = ImageOps.exif_transpose(im)
        is_png = f.lower().endswith('.png')
        has_alpha = im.mode in ('RGBA', 'LA') and im.getextrema()[-1][0] < 255
        if is_png and has_alpha:
            print(f'  skip (transparent png): {f}')
            continue
        im = im.convert('RGB')
        if max(im.size) > MAX_EDGE:
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        out = re.sub(r'\.png$', '.jpg', f, flags=re.I) if is_png else f
        orig_dest = os.path.join(ORIG, f)
        if DRY:
            print(f'  would optimize {f} ({size/1e6:.1f}MB) -> {out}')
            continue
        os.makedirs(os.path.dirname(orig_dest), exist_ok=True)
        if not os.path.exists(orig_dest):
            shutil.move(f, orig_dest)
        elif os.path.exists(f):
            os.remove(f)
        fmt = 'WEBP' if out.lower().endswith('.webp') else 'JPEG'
        kw = dict(quality=QUALITY, method=6) if fmt == 'WEBP' else dict(quality=QUALITY, optimize=True, progressive=True)
        im.save(out, fmt, **kw)
        new = os.path.getsize(out)
        saved += size - new
        print(f'  {size/1e6:5.1f}MB -> {new/1e6:4.2f}MB  {out}')
        if out != f:
            for p in ps:
                c = open(p, encoding='utf-8').read()
                rel_old = os.path.relpath(f, os.path.dirname(p) or '.')
                rel_new = os.path.relpath(out, os.path.dirname(p) or '.')
                for old in {rel_old, quote(rel_old)}:
                    c = c.replace(old, rel_new)
                open(p, 'w', encoding='utf-8').write(c)
    print(f'saved {saved/1e6:.1f}MB')

if __name__ == '__main__':
    main()
