#!/usr/bin/env python3
"""開発局の補正予算・ゼロ国債と公共測量の届出の突き合わせ (D26)。

入力: analysis/classified.csv、data/external/hkd-budget-initial.csv (fetch_budget.py)、
      data/external/hkd-budget-supplementary.csv (fetch_budget_supp.py)
出力: reports/supplementary/compare.md

- 届出は計画機関が北海道開発局の測量 (受付年度)。予算は直轄の事業費 (億円)。
- 補正予算は多くが 11〜2 月に成立し、翌年度に繰り越して執行される。そこで「当初」「当初 + 当該年度の補正」
  「当初 + 前年度の補正」の 3 通りで、件数との相関 (水準と前年度からの増減) を比べる。
- ゼロ国債は年度内に契約でき支出は翌年度になる枠。年度末 (1〜3 月) の受付が増えるかを見る。
"""
import collections
import csv
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = list(range(2009, 2026))


def era(y):
    if y >= 2019:
        return 'R1' if y == 2019 else f'R{y - 2018}'
    return f'H{y - 1988}'


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** .5


def diffs(v):
    return [v[i] - v[i - 1] for i in range(1, len(v))]


rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
ini = {int(r['year']): int(r['total']) / 100 for r in csv.DictReader((ROOT / 'data/external/hkd-budget-initial.csv').open())
       if r['kind'] == 'direct'}
sup, zero = collections.defaultdict(float), collections.defaultdict(float)
for r in csv.DictReader((ROOT / 'data/external/hkd-budget-supplementary.csv').open()):
    (sup if r['kind'] == 'supp' else zero)[int(r['year'])] += float(r['direct'])
kai = collections.Counter(int(r['year']) for r in rows if r['planner_type'] == '北海道開発局')
q4 = collections.Counter(int(r['year']) for r in rows if r['planner_type'] == '北海道開発局' and r['recept_date'][5:7] in ('01', '02', '03'))
apr = collections.Counter(int(r['year']) for r in rows if r['planner_type'] == '北海道開発局' and r['recept_date'][5:7] == '04')

out = ['# 開発局の補正予算・ゼロ国債と公共測量の届出 — 根拠表\n',
       '`scripts/budget_supp_compare.py` が生成。届出は国土地理院「公共測量実施情報」(北海道地方測量部) の計画機関が北海道開発局の測量、'
       '予算は北海道開発局「予算概要」の当初予算・補正予算の直轄の事業費 (億円) を dwg7 が編集・加工。'
       '補正は 1 年度に複数あれば合算。ゼロ国債は補正予算の資料に載る国庫債務負担行為 (当該年度の支出はゼロ、年度内に契約可能)。\n']

out.append('## T1. 年度ごとの予算と届出\n')
out.append('| 年度 | 当初 (直轄) | 補正 (直轄) | ゼロ国債 (直轄) | 当初 + 前年度の補正 | 開発局の届出 | うち 1〜3 月の受付 | うち 4 月の受付 |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|')
for y in YEARS:
    prev = f'{ini[y] + sup[y - 1]:,.0f}' if y > 2009 else '—'
    out.append(f'| {era(y)} ({y}) | {ini[y]:,.0f} | {sup[y]:,.0f} | {zero[y]:,.0f} | {prev} | {kai[y]} | {q4[y]} | {apr[y]} |')
out.append('\n平成21年度の補正 (1,071 億円) は 5 月に成立し、その年度に執行された (平成21年度の経済危機対策)。'
           '平成23年度の補正は 5 月 (3 億円) と 11 月 (317 億円) の合計。\n')

Y = YEARS[1:]   # 前年度の補正を使うので平成22年度から
k = [kai[y] for y in Y]
specs = [('当初', lambda y: ini[y]), ('当初 + 当該年度の補正', lambda y: ini[y] + sup[y]),
         ('当初 + 前年度の補正', lambda y: ini[y] + sup[y - 1]), ('前年度の補正だけ', lambda y: sup[y - 1])]
out.append('## T2. 予算と届出の相関 (平成22〜令和7年度、16 年度)\n')
out.append('| 予算の取り方 | 水準の相関 | 前年度からの増減の相関 | 増減の相関 (1 年度ずつ抜いた時の範囲) |')
out.append('|---|---:|---:|---:|')
for lab, f in specs:
    v = [f(y) for y in Y]
    dv, dk = diffs(v), diffs(k)
    loo = [corr(dv[:i] + dv[i + 1:], dk[:i] + dk[i + 1:]) for i in range(len(dv))]
    out.append(f'| {lab} | {corr(v, k):+.2f} | {corr(dv, dk):+.2f} | {min(loo):+.2f}〜{max(loo):+.2f} |')
out.append('\n増減の相関は 15 組。1 年度ずつ抜いても符号と大きさが保たれるかで、少数の年に引っぱられていないかを見る。\n')

out.append('## T3. ゼロ国債と年度末の受付\n')
zs = [zero[y] for y in YEARS]
out.append(f'ゼロ国債 (直轄) と開発局の 1〜3 月の受付件数の相関 {corr(zs, [q4[y] for y in YEARS]):+.2f}、'
           f'翌年度 4 月の受付件数との相関 {corr(zs[:-1], [apr[y + 1] for y in YEARS[:-1]]):+.2f} (平成21〜令和7年度)。'
           f'ゼロ国債は {min(zs):,.0f}〜{max(zs):,.0f} 億円、1〜3 月の受付は {min(q4[y] for y in YEARS)}〜{max(q4[y] for y in YEARS)} 件。\n')

out.append('## T4. 開発局の受付の月別 (大きな補正の前後)\n')
out.append('| 年度 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 1 | 2 | 3 |')
out.append('|---|' + '---:|' * 12)
for y in (2012, 2013, 2019, 2020, 2021):
    c = collections.Counter(int(r['recept_date'][5:7]) for r in rows if r['planner_type'] == '北海道開発局' and int(r['year']) == y)
    out.append(f'| {era(y)} | ' + ' | '.join(str(c[m]) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)) + ' |')
out.append('')
(ROOT / 'reports/supplementary').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/supplementary/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/supplementary/compare.md')
