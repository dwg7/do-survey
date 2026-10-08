#!/usr/bin/env python3
"""道の発注: 公共測量の届出と委託契約の突き合わせ (D25)。

入力: analysis/classified.csv、data/external/hokkaido-pref-contracts-h1.csv (scripts/fetch_pref_contracts.py)
出力: reports/contracts/compare.md

- 届出: 計画機関が道の総合振興局・振興局で、受付が上期 (4〜9 月) の測量。担当部署に「○○建設管理部」があれば
  その建設管理部、なければその振興局の産業振興部 (農村振興・水産・林務) に数える。
- 契約: 道の入札・契約実績 (9 月末) の委託の件数 (随意契約を含む合計)。測量・設計・調査などの業務委託で、
  公共測量はその一部。
- 届出の比率 = 届出 / 委託契約。比率が動くのに契約が動かなければ、届出 (レンズ) の変化とみる。
"""
import collections
import csv
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = list(range(2020, 2025))
KEN = ['札幌', '小樽', '室蘭', '函館', '旭川', '留萌', '稚内', '網走', '帯広', '釧路']


def era(y):
    return '令和元年度' if y == 2019 else f'令和{y - 2018}年度'


def short(y):
    return f'R{y - 2018}'


rows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open())
        if r['planner_type'] == '北海道' and r['half'] == '上期' and int(r['year']) in YEARS]
con = list(csv.DictReader((ROOT / 'data/external/hokkaido-pref-contracts-h1.csv').open()))
contracts = {(x['kind'], x['dept'], x['office'], int(x['year'])): int(x['contracts_h1']) for x in con}


def key(r):
    m = re.search('(' + '|'.join(KEN) + ')建設管理部', r['charge_section'])
    if m:
        return ('建設管理部', m.group(1))
    m = re.match(r'北海道(.+?)(総合)?振興局$', r['planner'])
    return ('産業振興部', m.group(1)) if m else None


surveys = collections.Counter()
unassigned = collections.Counter()
for r in rows:
    k = key(r)
    if k:
        surveys[(k, int(r['year']))] += 1
    else:
        unassigned[int(r['year'])] += 1
fields = collections.Counter((key(r), int(r['year']), r['field']) for r in rows if key(r))

out = ['# 道の発注: 公共測量の届出と委託契約の突き合わせ — 根拠表\n',
       '`scripts/pref_contracts_compare.py` が生成。届出は国土地理院「公共測量実施情報」(北海道地方測量部)、契約は北海道入札監視委員会の'
       '資料「発注機関別入札・契約実績」(各年度 9 月末、委託・工事の件数、随意契約を含む) を dwg7 が編集・加工。'
       '届出は道の総合振興局・振興局が計画機関で、受付が 4〜9 月の測量。担当部署に「○○建設管理部」があればその建設管理部、'
       'なければ振興局の産業振興部に数える。'
       f'どちらにも当たらない届出 (計画機関が「北海道」だけのもの) は {sum(unassigned.values())} 件で、表から除いた。\n']

for dept, offices in (('産業振興部', None), ('建設管理部', KEN)):
    offs = offices or list(dict.fromkeys(x['office'] for x in con if x['dept'] == dept))
    out.append(f'\n## {dept}: 届出 / 委託契約 (届出の比率)\n')
    out.append('| 機関 | ' + ' | '.join(short(y) for y in YEARS) + ' |')
    out.append('|---|' + '---:|' * len(YEARS))
    tot_s, tot_c = collections.Counter(), collections.Counter()
    for o in offs:
        cells = []
        for y in YEARS:
            s, c = surveys[((dept, o), y)], contracts[('委託', dept, o, y)]
            tot_s[y] += s
            tot_c[y] += c
            cells.append(f'{s} / {c} ({100 * s / c:.0f}%)')
        out.append(f'| {o} | ' + ' | '.join(cells) + ' |')
    out.append('| **計** | ' + ' | '.join(f'**{tot_s[y]} / {tot_c[y]} ({100 * tot_s[y] / tot_c[y]:.0f}%)**' for y in YEARS) + ' |')

out.append('\n## 工事の契約 (参考)\n')
out.append('| 部 | 機関 | ' + ' | '.join(short(y) for y in YEARS) + ' |')
out.append('|---|---|' + '---:|' * len(YEARS))
for dept, o in (('産業振興部', '上川'), ('建設管理部', '旭川'), ('産業振興部', '空知'), ('産業振興部', '十勝')):
    out.append(f'| {dept} | {o} | ' + ' | '.join(str(contracts[('工事', dept, o, y)]) for y in YEARS) + ' |')
for dept in ('産業振興部', '建設管理部'):
    out.append(f'| {dept} | 計 | ' + ' | '.join(str(sum(v for (k, d, _, yy), v in contracts.items() if k == '工事' and d == dept and yy == y)) for y in YEARS) + ' |')

out.append('\n## 上川の届出の分野 (上期)\n')
out.append('| 部 | 分野 | ' + ' | '.join(short(y) for y in YEARS) + ' |')
out.append('|---|---|' + '---:|' * len(YEARS))
for k in (('産業振興部', '上川'), ('建設管理部', '旭川')):
    fs = [f for f, _ in collections.Counter({f: v for (kk, y, f), v in fields.items() if kk == k}).most_common(4)]
    for f in fs:
        out.append(f'| {k[0]} ({k[1]}) | {f} | ' + ' | '.join(str(fields[(k, y, f)]) for y in YEARS) + ' |')

# 比率の変化の要約: 令和4年度の上川と、令和6年度の産業振興部
out.append('\n## 比率の変化の要約\n')
out.append('| 機関 | R2〜R3 の比率 (平均) | R4 | R5 | R6 | R6 の契約 / R2〜R5 の平均 |')
out.append('|---|---:|---:|---:|---:|---:|')
for dept in ('産業振興部', '建設管理部'):
    offs = list(dict.fromkeys(x['office'] for x in con if x['dept'] == dept))
    for o in offs:
        rt = {y: surveys[((dept, o), y)] / contracts[('委託', dept, o, y)] for y in YEARS}
        base_c = statistics.mean(contracts[('委託', dept, o, y)] for y in YEARS[:-1])
        out.append(f'| {dept} {o} | {100 * statistics.mean([rt[2020], rt[2021]]):.0f}% | {100 * rt[2022]:.0f}% | '
                   f'{100 * rt[2023]:.0f}% | {100 * rt[2024]:.0f}% | {contracts[("委託", dept, o, 2024)] / base_c:.2f} |')

# 道の当初予算 (公共事業の補助事業費等) と道の届出 (通年)
bud = list(csv.DictReader((ROOT / 'data/external/hokkaido-pref-budget-initial.csv').open()))
allrows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if r['planner_type'] == '北海道']
cnt = collections.Counter(int(r['year']) for r in allrows)
agri = collections.Counter(int(r['year']) for r in allrows if r['field'] == '農業農村')
out.append('\n## 道の当初予算と道の届出 (通年)\n')
out.append('予算は令和4年度「予算のポイント」の投資的経費の推移 (`data/external/hokkaido-pref-budget-initial.csv`、億円、前年度の国の補正予算分を含まない)。'
           '届出は計画機関が道の測量 (通年)。\n')
out.append('| 年度 | 公共事業 (補助事業費等) | 投資的経費の計 | 道の届出 | うち農業農村 | 届出 / 補助事業費 100 億円 |')
out.append('|---|---:|---:|---:|---:|---:|')
for b in bud:
    y = int(b['year'])
    out.append(f'| {"H" + str(y - 1988) if y < 2019 else short(y)} | {int(b["public_subsidy"]):,} | {int(b["investment_total"]):,} | {cnt[y]} | {agri[y]} '
               f'| {100 * cnt[y] / int(b["public_subsidy"]):.1f} |')
out.append('')
(ROOT / 'reports/contracts').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/contracts/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/contracts/compare.md')
