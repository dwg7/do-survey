#!/usr/bin/env python3
"""依存なしで .xlsx の最初のシートを行のリストとして読む (共有文字列・数値のみ)。"""
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def col_index(ref):
    letters = re.match(r'[A-Z]+', ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def rows(path, sheet=1):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            # ふりがな (rPh) は除き、本文の t と書式付きの r/t だけをつなぐ
            parts = [si.find('m:t', NS)] + [r.find('m:t', NS) for r in si.findall('m:r', NS)]
            shared.append(''.join(t.text or '' for t in parts if t is not None))
    root = ET.fromstring(z.read(f'xl/worksheets/sheet{sheet}.xml'))
    out = []
    for r in root.iter('{%s}row' % NS['m']):
        vals = {}
        for c in r.findall('m:c', NS):
            v = c.find('m:v', NS)
            if c.get('t') == 'inlineStr':
                val = ''.join(t.text or '' for t in c.iter('{%s}t' % NS['m']))
            elif v is None:
                continue
            elif c.get('t') == 's':
                val = shared[int(v.text)]
            else:
                val = float(v.text)
            vals[col_index(c.get('r'))] = val
        out.append([vals.get(i) for i in range(max(vals) + 1)] if vals else [])
    return out
