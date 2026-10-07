#!/usr/bin/env python3
"""ある受付年度の「北海道測量概況」の根拠表を作る (D16, D18)。

使い方: python3 scripts/year_tables.py <受付年度> <出力パス>   (推移はその年度までの 7 年度)
入力: analysis/classified.csv (scripts/classify.py の出力)
出力: 指定のパス (素案が引用する表。すべてこのスクリプトで再現できる)

数え方:
- 発注主体・ねらい・分野・段階は測量 1 件を 1 件と数える。
- 地域 (振興局) は「関与」で数える: 測量地域の市町村が属する振興局それぞれに 1 件。振興局をまたぐ測量は
  複数の振興局に数えるので、振興局の合計は測量件数より多い。構成比は「その振興局に関わった測量 / 全測量」。
- 主対象は指定の年度、推移はその年度までの 7 年度。令和7年度なら令和元〜7年度 (2019〜2025)。
"""
import collections
import csv
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = 'scripts/r07_tables.py' if (len(sys.argv) <= 1 or sys.argv[1] == '2025') else 'scripts/year_tables.py'
Y = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
OUT = sys.argv[2] if len(sys.argv) > 2 else 'reports/r07/tables.md'
YEARS = list(range(Y - 6, Y + 1))
AIMS = ['生産力維持', '地域維持', '公共事業執行', '防災減災', '資産管理', '制度・権利管理']
PTYPES = ['北海道', '北海道開発局', '市町村', '法務局', '防衛省', '国 (その他)', 'その他']
STAGES = ['計画', '用地', '工事', '管理', '不明']
FOCUS = ['空知', '十勝', 'オホーツク', '上川', '胆振', '日高']


def era(y):
    return f'R{y - 2018}' if y >= 2019 else f'H{y - 1988}'


def era_long(y):
    return f'令和{y - 2018}年度' if y >= 2019 else f'平成{y - 1988}年度'


def span(a, b):
    # 'R1-7'、'H16-22'、'H26-R2' の形
    ea, eb = era(a), era(b)
    return f'{ea}-{eb[1:]}' if ea[0] == eb[0] else f'{ea}-{eb}'


def span_long(a, b):
    la, lb = era_long(a), era_long(b)
    la = la.replace('令和1年度', '令和元年度')
    return f'{la[:-2]}〜{lb[2:]}' if la[:2] == lb[:2] else f'{la[:-2]}〜{lb}'


REIWA = {y: era(y) for y in YEARS}
TY = era(Y)
W = span(YEARS[0], YEARS[-1])
E3, L3 = span(YEARS[0], YEARS[2]), span(YEARS[-3], YEARS[-1])

rows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if YEARS[0] <= int(r['year']) <= Y]
if any(r['aim'] == '不明' for r in rows):   # 目的が「その他」の古い年度だけ
    AIMS = AIMS + ['不明']
for r in rows:
    r['year'] = int(r['year'])
    r['bureau_list'] = r['bureaus'].split()
munis = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
BUREAUS = []
for m in munis:
    if m['status'] == 'active' and m['bureau'] not in BUREAUS:
        BUREAUS.append(m['bureau'])
n_munis_by_bureau = collections.Counter(m['bureau'] for m in munis if m['status'] == 'active')
name_of = {m['code']: m['fullName'] for m in munis}

out = []


def h(title):
    out.append(f'\n## {title}\n')


def table(head, body, note=None):
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(head))) + '|')
    for b in body:
        out.append('| ' + ' | '.join(str(x) for x in b) + ' |')
    if note:
        out.append(f'\n{note}')
    out.append('')


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '—'


def cy(y):
    return [r for r in rows if r['year'] == y]


r07 = cy(Y)
N = len(r07)

out.append(f'# {era_long(Y)} 北海道測量概況 — 根拠表\n')
out.append(f'`{SCRIPT}` が `analysis/classified.csv` から生成。{era_long(Y)} (受付年度 {Y}) は {N} 件。'
           f'推移は{span_long(YEARS[0], Y)}。分類の規則は `analysis/*-rules.csv`、考え方は DECISIONS.md D16。\n')

# T1 発注主体
h('T1 発注主体')
body = []
for t in PTYPES:
    c = [sum(1 for r in cy(y) if r['planner_type'] == t) for y in YEARS]
    body.append([t] + c + [pct(c[-1], N)])
body.append(['計'] + [len(cy(y)) for y in YEARS] + ['100%'])
table(['発注主体'] + [REIWA[y] for y in YEARS] + [f'{TY} 構成比'], body)
sub = collections.Counter((r['planner_type'], r['planner_sub']) for r in r07 if r['planner_type'] in ('その他', '国 (その他)', '防衛省', '法務局'))
table([f'{TY} の内訳 (北海道・開発局・市町村以外)', '件数'], [[f'{a} / {b}', n] for (a, b), n in sub.most_common()])
# 北海道の振興局別、開発局の開建別
hk = collections.Counter(r['planner'] for r in r07 if r['planner_type'] in ('北海道', '北海道開発局'))
table([f'{TY} 北海道・開発局の発注機関 (上位 25)', '件数'], [[p, n] for p, n in hk.most_common(25)])

# T2 地域 (振興局、関与)
h('T2 振興局別 (測量地域、関与件数)')
body = []
early = {b: statistics.mean(sum(1 for r in cy(y) if b in r['bureau_list']) for y in (2019, 2020, 2021)) for b in BUREAUS}
late = {b: statistics.mean(sum(1 for r in cy(y) if b in r['bureau_list']) for y in (2023, 2024, 2025)) for b in BUREAUS}
tot_e = statistics.mean(len(cy(y)) for y in YEARS[:3])
tot_l = statistics.mean(len(cy(y)) for y in YEARS[-3:])
for b in sorted(BUREAUS, key=lambda b: -sum(1 for r in r07 if b in r['bureau_list'])):
    c = [sum(1 for r in cy(y) if b in r['bureau_list']) for y in YEARS]
    body.append([b, n_munis_by_bureau[b]] + c + [pct(c[-1], N), f'{100 * early[b] / tot_e:.1f}% → {100 * late[b] / tot_l:.1f}%'])
table(['振興局', '市町村数'] + [REIWA[y] for y in YEARS] + [f'{TY} 構成比', f'構成比 {E3} 平均 → {L3} 平均'], body,
      '構成比 = その振興局に関わった測量 / 全測量。振興局をまたぐ測量は両方に数える。')
cross = sum(1 for r in r07 if int(r['n_bureaus']) > 1)
nom = sum(1 for r in r07 if int(r['n_bureaus']) == 0)
out.append(f'{TY} で複数の振興局にまたがる測量: {cross} 件 ({pct(cross, N)})。測量地域が特定できない測量: {nom} 件。\n')

# T3 ねらい
h('T3 ねらい (行政目的 6 分類)')
body = []
for a in AIMS:
    c = [sum(1 for r in cy(y) if r['aim'] == a) for y in YEARS]
    body.append([a] + c + [pct(c[-1], N)])
table(['ねらい'] + [REIWA[y] for y in YEARS] + [f'{TY} 構成比'], body)
fa = collections.Counter((r['aim'], r['field']) for r in r07)
table([f'{TY} ねらい / 分野', '件数', '構成比'], [[f'{a} / {f}', n, pct(n, N)] for (a, f), n in sorted(fa.items(), key=lambda x: (AIMS.index(x[0][0]), -x[1]))])
body = []
for a in AIMS:
    body.append([a] + [sum(1 for r in r07 if r['aim'] == a and r['planner_type'] == t) for t in PTYPES])
table([f'{TY} ねらい × 発注主体'] + PTYPES, body)
body = []
for a in AIMS:
    sub = [r for r in r07 if r['aim'] == a]
    body.append([a] + [pct(sum(1 for r in sub if r['stage'] == s), len(sub)) for s in STAGES] + [len(sub)])
table([f'{TY} ねらい × 段階 (行内構成比)'] + STAGES + ['件数'], body)

# T4 分野の推移
h('T4 分野の推移')
fields = [f for f, _ in collections.Counter(r['field'] for r in rows).most_common()]
body = []
for f in fields:
    c = [sum(1 for r in cy(y) if r['field'] == f) for y in YEARS]
    body.append([f] + c + [pct(c[-1], N)])
table(['分野'] + [REIWA[y] for y in YEARS] + [f'{TY} 構成比'], body)

# T5 半期
h('T5 半期 (受付日: 上期 4〜9 月、下期 10〜翌 3 月)')
body = []
for y in YEARS:
    s = cy(y)
    up = sum(1 for r in s if r['half'] == '上期')
    body.append([REIWA[y], up, len(s) - up, pct(up, len(s))])
table(['年度', '上期', '下期', '上期の割合'], body)
body = []
for a in AIMS:
    s = [r for r in rows if r['aim'] == a]
    up = sum(1 for r in s if r['half'] == '上期')
    s7 = [r for r in r07 if r['aim'] == a]
    up7 = sum(1 for r in s7 if r['half'] == '上期')
    body.append([a, pct(up, len(s)), pct(up7, len(s7))])
table(['ねらい', f'上期の割合 ({W})', f'上期の割合 ({TY})'], body)
months = collections.Counter(int(r['recept_date'][5:7]) for r in rows if r['recept_date'])
order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
table([f'受付月 ({W} 合計)'] + [f'{m}月' for m in order], [['件数'] + [months[m] for m in order]])

# T6 振興局 × ねらい / 分野 (対象年度)
h(f'T6 振興局 × ねらい ({TY}、関与件数、行内構成比)')
body = []
for b in sorted(BUREAUS, key=lambda b: -sum(1 for r in r07 if b in r['bureau_list'])):
    s = [r for r in r07 if b in r['bureau_list']]
    body.append([b, len(s)] + [pct(sum(1 for r in s if r['aim'] == a), len(s)) for a in AIMS])
s = [r for r in r07 if r['bureau_list']]
body.append(['全道', len(s)] + [pct(sum(1 for r in s if r['aim'] == a), len(s)) for a in AIMS])
table(['振興局', '件数'] + AIMS, body)
body = []
topf = fields[:8]
for b in sorted(BUREAUS, key=lambda b: -sum(1 for r in r07 if b in r['bureau_list'])):
    s = [r for r in r07 if b in r['bureau_list']]
    body.append([b, len(s)] + [pct(sum(1 for r in s if r['field'] == f), len(s)) for f in topf])
table([f'振興局 × 分野 ({TY}、行内構成比)', '件数'] + topf, body)

# T7 地域特性 (6 振興局)
h('T7 地域特性 (空知・十勝・オホーツク・上川・胆振・日高)')
KW = ['ほ場整備', '土地改良', '畑地帯', '中山間', '経営体', '通作条件', '水利施設', '農地集積', '草地整備', '区画整理',
      '農道', '用水', '排水', '国道', '道道|地方道|地道', '町道|市道|村道', '砂防', '改修', '河川', '海岸', '港', '空港', '地籍', '法務局']
import re
body = []
for k in KW:
    rk = re.compile(k)
    body.append([k] + [sum(1 for r in rows if b in r['bureau_list'] and rk.search(r['purpose'])) for b in FOCUS]
                + [sum(1 for r in rows if r['bureau_list'] and rk.search(r['purpose']))])
table([f'業務名の語 ({W} 延べ)'] + FOCUS + ['全道'], body, '業務名 (目的欄) に語が含まれる測量の件数。定型の目的「ほ場整備」「土地改良」も業務名に含む。')
for b in FOCUS:
    s = [r for r in r07 if b in r['bureau_list']]
    sr = [r for r in rows if b in r['bureau_list']]
    pt = collections.Counter(r['planner'] for r in s).most_common(5)
    fl = collections.Counter(r['field'] for r in s).most_common(5)
    mc = collections.Counter(c for r in sr for c in r['muni_codes'].split() if name_of.get(c) and c in {m['code'] for m in munis if m['bureau'] == b})
    covered = len(mc)
    cross_b = sum(1 for r in s if int(r['n_bureaus']) > 1)
    out.append(f'### {b} ({TY} {len(s)} 件、管内 {n_munis_by_bureau[b]} 市町村)\n')
    out.append(f'- 分野: ' + '、'.join(f'{f} {n} ({pct(n, len(s))})' for f, n in fl))
    out.append(f'- 発注機関: ' + '、'.join(f'{p} {n}' for p, n in pt))
    out.append(f'- 他の振興局にもまたがる測量: {cross_b} 件 ({pct(cross_b, len(s))})')
    out.append(f'- {W} に測量のあった管内市町村: {covered} / {n_munis_by_bureau[b]}。多い順: '
               + '、'.join(f'{name_of[c]} {n}' for c, n in mc.most_common(6)))
    tr = [sum(1 for r in cy(y) if b in r['bureau_list']) for y in YEARS]
    ag = [sum(1 for r in cy(y) if b in r['bureau_list'] and r['field'] == '農業農村') for y in YEARS]
    out.append(f'- 推移 ({era(YEARS[0])}→{TY}): 全体 ' + ' / '.join(map(str, tr)) + '、うち農業農村 ' + ' / '.join(map(str, ag)))
    out.append('')

# T8 航空写真・オルソ・行政情報
h('T8 航空写真・オルソ画像・数値撮影 (業務名または測量種別)')
rk = re.compile('(航空写真|写真撮影|オルソ|写真地図|数値撮影|空中写真|航空レーザ)')
body = []
for t in PTYPES:
    body.append([t] + [sum(1 for r in cy(y) if r['planner_type'] == t and (rk.search(r['purpose']) or rk.search(r['kinds']))) for y in YEARS])
table(['発注主体'] + [REIWA[y] for y in YEARS], body)
lst = [r for r in r07 if r['planner_type'] == '市町村' and (rk.search(r['purpose']) or rk.search(r['kinds']))]
table([f'{TY} 市町村の航空写真・レーザ等', 'ねらい', '担当部署'], [[f"{r['planner']} {r['purpose'][:40]}", r['aim'], r['charge_section'][:20]] for r in lst])
fx = [r for r in rows if re.search('固定資産|課税|税務', r['purpose'] + r['charge_section'])]
out.append(f'{W} で業務名・担当部署に「固定資産・課税・税務」を含む測量: {len(fx)} 件 (うち {TY} {sum(1 for r in fx if r["year"] == Y)} 件)。\n')

# T9 空間分布
h('T9 空間分布 (市町村の広がりと集中)')
active = [m['code'] for m in munis if m['status'] == 'active']
body = []
for a in AIMS + ['(全体)']:
    s = [r for r in r07 if a == '(全体)' or r['aim'] == a]
    mc = collections.Counter(c for r in s for c in r['muni_codes'].split())
    tot = sum(mc.values())
    top10 = sum(n for _, n in mc.most_common(10))
    body.append([a, len(s), len(mc), pct(top10, tot), '、'.join(f'{name_of[c]} {n}' for c, n in mc.most_common(5))])
table([f'{TY} ねらい', '測量', '関わった市町村数 (/179)', '上位 10 市町村の占める割合', '多い市町村'], body)
zero = [name_of[c] for c in active if not any(c in r['muni_codes'].split() for r in r07)]
out.append(f'{TY} に測量が 1 件もない市町村: {len(zero)} / 179 — ' + '、'.join(zero) + '\n')
zero7 = [name_of[c] for c in active if not any(c in r['muni_codes'].split() for r in rows)]
out.append(f'{W} を通じて 1 件もない市町村: {len(zero7)} — ' + ('、'.join(zero7) or 'なし') + '\n')
body = []
for b in sorted(BUREAUS, key=lambda b: -sum(1 for r in r07 if b in r['bureau_list'])):
    s = [r for r in r07 if r['bureaus'] == b and r['area_km2']]
    areas = [float(r['area_km2']) for r in s]
    body.append([b, len(s), f'{statistics.median(areas):.2f}' if areas else '—', f'{sum(areas):.0f}'])
table([f'{TY} 振興局 (単独の振興局の測量)', '実施地域図あり', '範囲の面積の中央値 km²', '範囲の面積の合計 km²'], body,
      '実施地域図は作業量ではなく作業範囲の外形 (重なりあり)。広がりの目安としてだけ使う。北海道の外にある 2 件は除く。')

# T10 仮説 C の指標
h('T10 「接続」の指標 (仮説 C)')
CONNECT = {'道路', '港湾・空港・鉄道'}
body = []
for b in ['胆振', '日高', '空知', '十勝', 'オホーツク', '上川', '石狩', '渡島', '釧路', '根室', '後志', '宗谷', '留萌', '檜山']:
    s = [r for r in rows if b in r['bureau_list']]
    con = sum(1 for r in s if r['field'] in CONNECT)
    agri = sum(1 for r in s if r['field'] == '農業農村')
    dis = sum(1 for r in s if r['aim'] == '防災減災')
    multi = sum(1 for r in s if int(r['n_munis']) > 1)
    crossb = sum(1 for r in s if int(r['n_bureaus']) > 1)
    dev = sum(1 for r in s if r['planner_type'] == '北海道開発局')
    body.append([b, len(s), pct(con, len(s)), pct(agri, len(s)), pct(dis, len(s)), pct(multi, len(s)), pct(crossb, len(s)), pct(dev, len(s))])
s = rows
body.append(['全道', len(s), pct(sum(1 for r in s if r['field'] in CONNECT), len(s)), pct(sum(1 for r in s if r['field'] == '農業農村'), len(s)),
             pct(sum(1 for r in s if r['aim'] == '防災減災'), len(s)), pct(sum(1 for r in s if int(r['n_munis']) > 1), len(s)),
             pct(sum(1 for r in s if int(r['n_bureaus']) > 1), len(s)), pct(sum(1 for r in s if r['planner_type'] == '北海道開発局'), len(s))])
table([f'振興局 ({W} 延べ)', '件数', '道路・港湾・空港・鉄道', '農業農村', '防災減災', '複数市町村', '複数振興局', '開発局発注'], body)
for b in ['胆振', '日高']:
    s = [r for r in rows if b in r['bureau_list'] and r['field'] in CONNECT]
    roads = collections.Counter(re.match(r'(一般国道\s*\d+号|[^\s　]+線|[^\s　]*港|[^\s　]*空港|道東自動車道|日高自動車道)', r['purpose']).group(1)
                                if re.match(r'(一般国道\s*\d+号|[^\s　]+線|[^\s　]*港|[^\s　]*空港|道東自動車道|日高自動車道)', r['purpose']) else r['purpose'][:12]
                                for r in s)
    out.append(f'- {b} の道路・港湾等 ({W}) の主な路線・施設: ' + '、'.join(f'{k} {n}' for k, n in roads.most_common(10)))
out.append('')

(ROOT / OUT).parent.mkdir(parents=True, exist_ok=True)
(ROOT / OUT).write_text('\n'.join(out) + '\n')
print('wrote', OUT, len(out), 'lines')
