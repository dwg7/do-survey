#!/usr/bin/env python3
"""北海道開発局関係予算 (当初、事業費) の治水・道路・農業農村整備・合計を年度ごとに抜き出す (D19)。

出典: 北海道開発局「予算概要」https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4.html の各年度の当初予算の PDF。
PDF は data/raw/budget/ に保存し (コミットしない)、pdftotext -layout で読む。
出力: data/external/hkd-budget-initial.csv (百万円。直轄と補助、事業費、当初予算のみ。補正は含まない)

注意: 補助の道路は平成22年度以降、社会資本整備総合交付金などに移り、年度間で比べられない。比較は直轄を主に使う。
"""
import csv
import pathlib
import re
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = 'https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4-att/'
FILES = {
    2009: 'u23dsn0000000hs4.pdf', 2010: 'u23dsn0000000hrq.pdf', 2011: 'u23dsn0000000hnu.pdf', 2012: 'u23dsn0000000hn0.pdf',
    2013: 'u23dsn0000000hm6.pdf', 2014: 'u23dsn0000000hl3.pdf', 2015: 'u23dsn0000000hjv.pdf', 2016: 'u23dsn0000000hjz.pdf',
    2017: 'splaat000000mmar.pdf', 2018: 'splaat000001aj8l.pdf', 2019: 'splaat000001lho6.pdf', 2020: 'splaat000001vca9.pdf',
    2021: 'slo5pa00000058ub.pdf', 2022: 'slo5pa000000jf7j.pdf', 2023: 'slo5pa0000010yxd.pdf', 2024: 'slo5pa000001eu1s.pdf',
    2025: 'k5m5qg00000047dl.pdf',
}
ITEMS = {'治水': '治水', '道路': '道路', '道路整備': '道路', '道路環境': '道路', '農業農村整備': '農業農村整備', '合計': '合計'}


def section_values(text, name):
    """【 直 轄 】 / 【 補 助 】 の最初の表から、行名 → 最初の数値 (百万円) を読む。"""
    m = re.search(r'【\s*' + r'\s*'.join(name) + r'\s*】(.*?)(?=【|\Z)', text, re.S)
    if not m:
        raise SystemExit(f'section {name} not found')
    vals = {}
    for line in m.group(1).splitlines():
        if re.match(r'\s*注', line):   # 表の終わり (平成23年度の補助には合計の行がない)
            break
        mm = re.match(r'\s*([^\d\s,－-][^\d,－-]*?)\s+([\d,]+)', line)
        if not mm:
            continue
        label = re.sub(r'\s', '', mm.group(1))
        if label in ITEMS:
            key = ITEMS[label]
            vals[key] = vals.get(key, 0) + int(mm.group(2).replace(',', ''))
        if label == '合計':
            break
    return vals


def main():
    raw = ROOT / 'data/raw/budget'
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for y, f in sorted(FILES.items()):
        pdf = raw / f't{y}.pdf'
        if not pdf.exists():
            urllib.request.urlretrieve(BASE + f, pdf)
            time.sleep(1)
        text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True).stdout
        for sec, label in (('直轄', 'direct'), ('補助', 'subsidy')):
            v = section_values(text, sec)
            rows.append({'year': y, 'kind': label, 'flood': v.get('治水', ''), 'road': v.get('道路', ''),
                         'agri': v.get('農業農村整備', ''), 'total': v.get('合計', ''), 'source': BASE + f})
    out = ROOT / 'data/external/hkd-budget-initial.csv'
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='') as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print('wrote', out)


if __name__ == '__main__':
    main()
