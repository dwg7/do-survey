#!/usr/bin/env python3
"""飛び石 (平成22・27年度、令和2・7年度) の主な指標を 1 枚に並べる (D18)。

入力: analysis/classified.csv
出力: reports/stepping/compare.md
各年度の詳しい表は reports/{h22,h27,r02,r07}/tables.md (scripts/year_tables.py)。
単年はぶれるので、件数の構成比には前後を含む 3 年度平均も併記する。
"""
import collections
import csv
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
STEPS = [(2010, 'H22'), (2015, 'H27'), (2020, 'R2'), (2025, 'R7')]
AIMS = ['生産力維持', '地域維持', '公共事業執行', '防災減災', '資産管理', '制度・権利管理', '不明']
FIELDS = ['農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤', '都市・まちづくり', '行政情報', '水産', '港湾・空港・鉄道']
STAGES = ['計画', '用地', '工事', '管理', '不明']
FOCUS = ['空知', '十勝', 'オホーツク', '上川', '胆振', '日高']

rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in rows:
    r['year'] = int(r['year'])
    r['bl'] = r['bureaus'].split()
    r['ml'] = r['muni_codes'].split()
munis = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
active = [m for m in munis if m['status'] == 'active']
name_of = {m['code']: m['fullName'] for m in active}
BUREAUS = []
for m in active:
    if m['bureau'] not in BUREAUS:
        BUREAUS.append(m['bureau'])


def yr(y):
    return [r for r in rows if r['year'] == y]


def y3(y):
    # 3 年度平均の母集団。令和7年度は令和8年度が途中なので令和5〜7年度
    ys = (y - 2, y - 1, y) if y == 2025 else (y - 1, y, y + 1)
    return [r for r in rows if r['year'] in ys], ys


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '—'


out = ['# 飛び石の比較 — 平成22・27年度、令和2・7年度\n',
       '`scripts/stepping_compare.py` が `analysis/classified.csv` から生成。各年度の詳しい表は '
       '[H22](../h22/tables.md)・[H27](../h27/tables.md)・[R2](../r02/tables.md)・[R7](../r07/tables.md)。'
       '括弧内は前後を含む 3 年度の値 (R7 は R5〜7)。\n']


def table(title, head, body, note=None):
    out.append(f'\n## {title}\n')
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(head))) + '|')
    for b in body:
        out.append('| ' + ' | '.join(str(x) for x in b) + ' |')
    if note:
        out.append(f'\n{note}')
    out.append('')


def share_row(label, pred):
    row = [label]
    for y, _ in STEPS:
        s = yr(y)
        t, _ = y3(y)
        row.append(f'{pct(sum(1 for r in s if pred(r)), len(s))} ({pct(sum(1 for r in t if pred(r)), len(t))})')
    return row


heads = ['指標'] + [f'{lab} ({y})' for y, lab in STEPS]

# C1 規模と記録
body = [['測量件数'] + [f'{len(yr(y))} ({round(len(y3(y)[0]) / 3)})' for y, _ in STEPS]]
body.append(share_row('ねらい不明 (目的「その他」)', lambda r: r['aim'] == '不明'))
body.append(share_row('業務名 (自由記述) あり', lambda r: r['purpose'] not in ('その他',) and len(r['purpose']) > 8))
body.append(share_row('実施地域図あり', lambda r: bool(r['area_km2'])))
table('C1 規模と記録', heads, body, '「業務名あり」は目的欄が 9 文字以上のものの割合 (定型語は 8 文字以下) で、目安。')

# C2 発注主体
def pt(r):
    return r['planner_type'] if r['planner_type'] in ('北海道', '北海道開発局', '市町村', '法務局') else 'その他・国など'
table('C2 発注主体', heads, [share_row(t, lambda r, t=t: pt(r) == t) for t in ('北海道', '北海道開発局', '市町村', '法務局', 'その他・国など')])
body = []
for y, lab in STEPS:
    s = [r for r in yr(y) if r['planner_type'] == '北海道']
    c = collections.Counter(r['planner'].replace('北海道', '') for r in s)
    top4 = sum(n for _, n in c.most_common(4))
    body.append([lab, len(s), pct(top4, len(s)), '、'.join(f'{p} {n}' for p, n in c.most_common(4))])
table('C2b 道の発注の集中 (上位 4 振興局)', ['年度', '道の発注', '上位 4 の割合', '上位 4'], body)

# C3 ねらい・分野・段階
table('C3 ねらい', heads, [share_row(a, lambda r, a=a: r['aim'] == a) for a in AIMS])
table('C3b 分野', heads, [share_row(f, lambda r, f=f: r['field'] == f) for f in FIELDS])
table('C3c 段階', heads, [share_row(st, lambda r, st=st: r['stage'] == st) for st in STAGES],
      'H22・H27 は業務名がないので、段階の多くは定型語 (道路用地・河川用地など) と測量種別から決まる。')

# C4 時期
table('C4 受付の時期', heads, [share_row('上期 (4〜9 月)', lambda r: r['half'] == '上期')]
      + [share_row(f'{m} 月', lambda r, m=m: r['recept_date'][5:7] == f'{m:02d}') for m in (6, 7, 8)])

# C5 地域
body = []
for b in BUREAUS:
    row = [b]
    for y, _ in STEPS:
        s = [r for r in yr(y) if r['ml']]
        t = [r for r in y3(y)[0] if r['ml']]
        row.append(f'{pct(sum(1 for r in s if b in r["bl"]), len(s))} ({pct(sum(1 for r in t if b in r["bl"]), len(t))})')
    body.append(row)
table('C5 振興局 (関与件数の構成比)', heads, body)

# C6 空間の広がりと集中
body = [['測量のあった市町村 (/179)'], ['測量のない市町村'], ['上位 10 市町村の割合 (関与件数)'], ['複数の市町村にまたがる測量'],
        ['複数の振興局にまたがる測量'], ['範囲の面積の中央値 km² (実施地域図あり)']]
zeros = {}
for y, lab in STEPS:
    s = yr(y)
    mc = collections.Counter(c for r in s for c in r['ml'] if c in name_of)
    tot = sum(mc.values())
    body[0].append(len(mc))
    z = [name_of[m['code']] for m in active if m['code'] not in mc]
    zeros[lab] = z
    body[1].append(len(z))
    body[2].append(pct(sum(n for _, n in mc.most_common(10)), tot))
    body[3].append(pct(sum(1 for r in s if int(r['n_munis']) > 1), len(s)))
    body[4].append(pct(sum(1 for r in s if int(r['n_bureaus']) > 1), len(s)))
    a = [float(r['area_km2']) for r in s if r['area_km2']]
    body[5].append(f'{statistics.median(a):.2f}' if a else '—')
table('C6 空間の広がりと集中 (単年)', heads, body)
always = set(zeros['H22'])
for z in zeros.values():
    always &= set(z)
out.append('4 年度とも測量のない市町村: ' + ('、'.join(sorted(always, key=lambda n: [m['fullName'] for m in active].index(n))) or 'なし') + '\n')
for y, lab in STEPS:
    mc = collections.Counter(c for r in yr(y) for c in r['ml'] if c in name_of)
    out.append(f'- {lab} の多い市町村: ' + '、'.join(f'{name_of[c]} {n}' for c, n in mc.most_common(8)))
out.append('')

# C7 6 地域の特徴 (3 年度の値)
body = []
for b in FOCUS:
    for label, pred in (('農業農村', lambda r: r['field'] == '農業農村'), ('道路・交通', lambda r: r['field'] in ('道路', '港湾・空港・鉄道')),
                        ('防災減災', lambda r: r['aim'] == '防災減災'), ('資産・制度', lambda r: r['aim'] in ('資産管理', '制度・権利管理'))):
        row = [f'{b} {label}']
        for y, _ in STEPS:
            t = [r for r in y3(y)[0] if b in r['bl']]
            row.append(f'{pct(sum(1 for r in t if pred(r)), len(t))} / {len(t)}')
        body.append(row)
table('C7 6 地域の特徴 (3 年度の構成比 / その振興局に関わった件数)', heads, body)

# C8 6 地域の主な発注機関 (3 年度)
body = []
for b in FOCUS:
    row = [b]
    for y, _ in STEPS:
        t = [r for r in y3(y)[0] if b in r['bl']]
        c = collections.Counter(r['planner'].replace('北海道開発局', '開').replace('北海道', '').replace('総合振興局', '').replace('振興局', '').replace('開発建設部', '開建') for r in t)
        row.append('、'.join(f'{p} {n}' for p, n in c.most_common(3)))
    body.append(row)
table('C8 6 地域の主な発注機関 (3 年度)', heads, body)

(ROOT / 'reports/stepping').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/stepping/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/stepping/compare.md')
