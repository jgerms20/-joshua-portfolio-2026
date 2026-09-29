#!/usr/bin/env python3
"""Fail if any page references a local file that doesn't exist."""
import glob, html, os, re, sys
from urllib.parse import unquote
bad = []
pages = ['index.html', 'shop.html', 'photography/index.html'] + glob.glob('work/*.html') + glob.glob('podcasts/*.html')
for p in pages:
    c = open(p, encoding='utf-8', errors='ignore').read(); b = os.path.dirname(p)
    for attr, val in re.findall(r'\b(src|href|poster|data-poster|data-mp4|data-fallbacks)\s*=\s*"([^"]+)"', c):
        vals = html.unescape(val).split() if attr == 'data-fallbacks' else [html.unescape(val)]
        for u in vals:
            if u.startswith(('http', '//', '#', 'data:', 'mailto:', 'tel:', 'javascript:', 'yt:')) or '${' in u:
                continue
            u = unquote(u.split('#')[0].split('?')[0])
            if u and not os.path.exists(os.path.normpath(os.path.join(b, u))):
                bad.append(f'{p} -> {u}')
for x in sorted(set(bad)): print('BROKEN', x)
print('broken refs:', len(set(bad)))
sys.exit(1 if bad else 0)
