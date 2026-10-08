#!/usr/bin/env python3
"""地域 (振興局) の推移と、測量のない市町村 (D27)。

入力: analysis/classified.csv、docs/vendor/do/data/municipalities.json
出力: reports/region/tables.md

- 振興局の割合 = その振興局に関わった測量 / 市町村の分かる測量 (annual_overview.py と同じ)。発注主体 (道・開発局・市町村) ごとにも出す。
- 傾向は平成21〜令和5年度の直線の傾き (ポイント / 10 年)。令和6年度以降は道の届出の段差 (D25) があるので傾きには入れず、別に並べる。
- 測量のない市町村 = その年度に関わった測量が 0 件の市町村 (179 市町村、根室振興局管内の 6 村は含まない)。
"""
import collections
import csv
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = list(range(2009, 2026))
TREND = list(range(2009, 2024))
rows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if 2009 <= int(r['year']) <= 2025]
for r in rows:
    r['year'] = int(r['year'])
    r['bl'] = r['bureaus'].split()
    r['ml'] = r['muni_codes'].split()
munis = [m for m in json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities'] if m['status'] == 'active']
active = {m['code']: m for m in munis}
BUREAUS = list(dict.fromkeys(m['bureau'] for m in munis))


def era(y):
    if y >= 2019:
        return 'R1' if y == 2019 else f'R{y - 2018}'
    return f'H{y - 1988}'


def slope(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def share(b, y, flt=lambda r: True):
    s = [r for r in rows if r['year'] == y and r['ml'] and flt(r)]
    return sum(1 for r in s if b in r['bl']) / len(s) if s else 0


out = ['# 地域 (振興局) の推移と、測量のない市町村 — 根拠表\n',
       '`scripts/region_trends.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部) を dwg7 が編集・加工。'
       '割合 = その振興局に関わった測量 / 市町村の分かる測量。傾きは平成21〜令和5年度の直線の傾き (ポイント / 10 年)。'
       '令和6年度以降は道の届出の段差 (D25) があるので傾きに入れない。\n']

PT = [('全体', lambda r: True), ('道', lambda r: r['planner_type'] == '北海道'),
      ('開発局', lambda r: r['planner_type'] == '北海道開発局'), ('市町村', lambda r: r['planner_type'] == '市町村')]
out.append('## T1. 振興局の割合の推移 (全体、%)\n')
out.append('| 振興局 | ' + ' | '.join(era(y) for y in YEARS) + ' | 傾き (全体) | 傾き (道) | 傾き (開発局) | 傾き (市町村) |')
out.append('|---|' + '---:|' * (len(YEARS) + 4))
sl = {}
for b in BUREAUS:
    vals = [100 * share(b, y) for y in YEARS]
    s = []
    for lab, f in PT:
        v = [100 * share(b, y, f) for y in TREND]
        s.append(10 * slope(TREND, v))
    sl[b] = s
    out.append(f'| {b} | ' + ' | '.join(f'{v:.0f}' for v in vals) + ' | ' + ' | '.join(f'{x:+.1f}' for x in s) + ' |')
out.append('\n振興局をまたぐ測量は複数の振興局に数えるので、割合の合計は 100% を超える。\n')

out.append('## T2. 傾きの大きい振興局 (全体、平成21〜令和5年度)\n')
out.append('| 振興局 | 傾き (全体) | 平成21〜23年度の平均 | 令和3〜5年度の平均 | 令和6〜7年度の平均 |')
out.append('|---|---:|---:|---:|---:|')
for b in sorted(BUREAUS, key=lambda b: -abs(sl[b][0]))[:8]:
    m = lambda ys: statistics.mean(100 * share(b, y) for y in ys)
    out.append(f'| {b} | {sl[b][0]:+.1f} | {m([2009, 2010, 2011]):.1f}% | {m([2021, 2022, 2023]):.1f}% | {m([2024, 2025]):.1f}% |')

# 測量のない市町村
cnt = {y: collections.Counter(c for r in rows if r['year'] == y for c in r['ml'] if c in active) for y in YEARS}
out.append('\n## T3. 測量のない市町村の数 (年度ごと)\n')
out.append('| 年度 | 測量のない市町村 | うち市 | うち町 | うち村 | 測量 1〜2 件の市町村 |')
out.append('|---|---:|---:|---:|---:|---:|')
for y in YEARS:
    zero = [c for c in active if cnt[y][c] == 0]
    cls = collections.Counter(active[c]['class'] for c in zero)
    low = sum(1 for c in active if 1 <= cnt[y][c] <= 2)
    out.append(f'| {era(y)} | {len(zero)} | {cls["市"]} | {cls["町"]} | {cls["村"]} | {low} |')
allcls = collections.Counter(m['class'] for m in munis)
out.append(f'\n179 市町村の内訳: 市 {allcls["市"]}・町 {allcls["町"]}・村 {allcls["村"]}。\n')

zy = {c: sum(1 for y in YEARS if cnt[y][c] == 0) for c in active}
tot = {c: sum(cnt[y][c] for y in YEARS) for c in active}
out.append('## T4. 測量のない年度が多い市町村 (平成21〜令和7年度の 17 年度のうち)\n')
out.append('| 市町村 | 振興局 | 測量のない年度 | 17 年度の件数の計 | 発注主体の内訳 (道 / 開発局 / 市町村 / その他) | 最後に測量のなかった年度 |')
out.append('|---|---|---:|---:|---|---|')
for c in sorted(active, key=lambda c: (-zy[c], tot[c]))[:25]:
    pt = collections.Counter(r['planner_type'] for r in rows for x in r['ml'] if x == c)
    other = sum(v for k, v in pt.items() if k not in ('北海道', '北海道開発局', '市町村'))
    last0 = max((y for y in YEARS if cnt[y][c] == 0), default=None)
    out.append(f'| {active[c]["fullName"]} | {active[c]["bureau"]} | {zy[c]} | {tot[c]} | '
               f'{pt["北海道"]} / {pt["北海道開発局"]} / {pt["市町村"]} / {other} | {era(last0) if last0 else "—"} |')

out.append('\n## T5. 測量のない年度の数の分布\n')
dist = collections.Counter(zy.values())
out.append('| 測量のない年度 (17 年度中) | 市町村の数 |')
out.append('|---:|---:|')
for k in sorted(dist):
    out.append(f'| {k} | {dist[k]} |')

out.append('\n## T6. 振興局ごとの「測量のない市町村・年度」の割合 (平成21〜令和5年度 / 令和6〜7年度)\n')
out.append('| 振興局 | 市町村の数 | 平成21〜令和5年度 | 令和6〜7年度 |')
out.append('|---|---:|---:|---:|')
for b in BUREAUS:
    cs = [c for c in active if active[c]['bureau'] == b]
    a = sum(1 for y in TREND for c in cs if cnt[y][c] == 0) / (len(cs) * len(TREND))
    bb = sum(1 for y in (2024, 2025) for c in cs if cnt[y][c] == 0) / (len(cs) * 2)
    out.append(f'| {b} | {len(cs)} | {100 * a:.0f}% | {100 * bb:.0f}% |')
out.append('')
(ROOT / 'reports/region').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/region/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/region/tables.md')
