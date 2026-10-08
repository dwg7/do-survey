#!/usr/bin/env python3
"""北海道開発局関係の補正予算 (事業費) とゼロ国債 (国庫債務負担行為) の直轄・補助の総額を抜き出す (D26)。

出典: 北海道開発局「予算概要」https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4.html の各年度の補正予算の PDF
(平成21〜令和7年度。1 年度に複数あれば全部)。PDF は data/raw/budget/hosei/ に保存し (コミットしない)、pdftotext -layout で読む。
出力: data/external/hkd-budget-supplementary.csv (億円)

- 各 PDF の冒頭の枠「直轄事業 ○億円 / 補助事業 ○億円」を読む。直前の見出しに「ゼロ国債」があれば zero (当該年度の支出はゼロで、
  年度内に契約できる翌年度の予算)、なければ supp (補正予算の事業費)。
- 分野別 (治水・道路・農業農村整備) の内訳は PDF の後ろの表にあるが、様式が年度で変わるので、ここでは総額だけを取る。
"""
import csv
import pathlib
import re
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / 'data/raw/budget/hosei'
BASE = 'https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4-att/'
PAGE = 'https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4.html'
FILES = {   # 保存名: (年度, PDF)
    'h2009a': (2009, 'u23dsn0000000hv0'), 'h2009b': (2009, 'u23dsn0000000hv3'), 'h2010': (2010, 'u23dsn0000000hux'),
    'h2011a': (2011, 'u23dsn0000000hnx'), 'h2011b': (2011, 'u23dsn0000000ho0'), 'h2011c': (2011, 'u23dsn0000000ho3'),
    'h2012': (2012, 'u23dsn0000000hn3'), 'h2013': (2013, 'u23dsn0000000hm9'), 'h2014': (2014, 'u23dsn0000000hm3'),
    'h2015': (2015, 'u23dsn0000000hm0'), 'h2016a': (2016, 'u23dsn0000000hlx'), 'h2016b': (2016, 'splaat000000mm7s'),
    'h2017': (2017, 'splaat00000174we'), 'h2018': (2018, 'splaat000001iw0u'), 'h2019': (2019, 'splaat000001t87d'),
    'h2020': (2020, 'splaat0000021xis'), 'h2021': (2021, 'slo5pa000000emog'), 'h2022': (2022, 'slo5pa000000tll6'),
    'h2023': (2023, 'slo5pa0000018dwb'), 'h2024': (2024, 'slo5pa000001mrxi'), 'h2025': (2025, 'jtfkjs0000002arz'),
}
UA = 'do-survey/0.1 (Hokkaido public survey dashboard; python-urllib)'
Z2H = str.maketrans('０１２３４５６７８９，', '0123456789,')


def amount(s):
    """「１，０７１億円」「３１０百万円」→ 億円。"""
    s = s.translate(Z2H).replace(' ', '')
    m = re.match(r'([\d,.]+)(億円|百万円)', s)
    v = float(m.group(1).replace(',', ''))
    return v / 100 if m.group(2) == '百万円' else v


def blocks(text):
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        m = re.match(r'\s*直\s*轄\s*事\s*業\s+([０-９0-9，,.\s]+(?:億円|百万円))', line)
        if not m:
            continue
        head = '\n'.join(lines[max(0, i - 6):i])
        kind = 'zero' if 'ゼロ国債' in head else 'supp'
        direct = amount(m.group(1))
        sub = 0.0
        m2 = re.match(r'\s*補\s*助\s*事\s*業\s+([０-９0-9，,.\s]+億円)', lines[i + 1]) if i + 1 < len(lines) else None
        if m2:
            sub = amount(m2.group(1))
        out.append((kind, direct, sub))
        if len(out) == 2:
            break
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (y, pdf) in FILES.items():
        p = RAW / f'{name}.pdf'
        if not p.exists():
            req = urllib.request.Request(BASE + pdf + '.pdf', headers={'User-Agent': UA})
            p.write_bytes(urllib.request.urlopen(req).read())
            time.sleep(1)
        text = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, text=True).stdout
        bs = blocks(text)
        assert bs, name
        for kind, d, s in bs:
            rows.append({'year': y, 'file': name, 'kind': kind, 'direct': round(d, 1), 'subsidy': round(s, 1),
                         'source': BASE + pdf + '.pdf'})
    out = ROOT / 'data/external/hkd-budget-supplementary.csv'
    with out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {out} ({len(rows)} rows)')


if __name__ == '__main__':
    main()
