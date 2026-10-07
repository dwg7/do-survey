#!/usr/bin/env python3
"""長期の変化が取れるかの見積もり: 3 年度ずつの「飛び石」で記録の質と中身を並べる (D17)。

入力: analysis/classified.csv (scripts/classify.py の出力、全年度)
出力: reports/longterm/tables.md
"""
import collections
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WINDOWS = [('H1-3', 1989, 1991), ('H11-13', 1999, 2001), ('H21-23', 2009, 2011), ('R1-3', 2019, 2021), ('R5-7', 2023, 2025)]
AIMS = ['生産力維持', '地域維持', '公共事業執行', '防災減災', '資産管理', '制度・権利管理', '不明']
PTYPES = ['北海道', '北海道開発局', '市町村', 'その他・国など']
FIELDS = ['農業農村', '道路', '防災・治水', '公物管理', '都市・まちづくり', '地籍・登記・課税', '位置基盤', '行政情報', '港湾・空港・鉄道']

rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in rows:
    r['year'] = int(r['year'])
master = set()
# 定型語 (現行マスターと、旧い年度に現れる短い定型語)。業務名の有無の判定に使う。
master.update(['その他', 'ダム計画', 'ほ場整備', '下水道管理', '下水道計画', '固定資産', '土地区画整理', '土地改良', '地すべり対策',
               '地盤変動調査', '地籍調査', '基準点管理', '文化財調査', '森林計画', '河川管理', '河川計画', '海岸保全', '港湾計画', '環境調査',
               '砂防計画', '空港計画', '総合計画', '農地開発', '農道管理', '農道計画', '道路台帳', '道路管理', '道路計画', '都市計画', '鉄道計画',
               '道路用地', '河川用地', '宅地開発', '電源開発'])
munis = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
BUREAUS = []
for m in munis:
    if m['status'] == 'active' and m['bureau'] not in BUREAUS:
        BUREAUS.append(m['bureau'])

out = ['# 長期の変化の見積もり — 飛び石の表\n',
       '`scripts/longterm_tables.py` が `analysis/classified.csv` から生成。各期間は 3 年度の合計。'
       'ねらいの「不明」は目的が定型語「その他」などで分類できないもの。\n']


def win(w):
    _, a, b = w
    return [r for r in rows if a <= r['year'] <= b]


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '—'


def table(title, head, body, note=None):
    out.append(f'\n## {title}\n')
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(head))) + '|')
    for b in body:
        out.append('| ' + ' | '.join(str(x) for x in b) + ' |')
    if note:
        out.append(f'\n{note}')
    out.append('')


ws = [win(w) for w in WINDOWS]
names = [w[0] + f' ({w[1]}-{w[2]})' for w in WINDOWS]

# L1 記録の質
q = []
q.append(['測量件数 (3 年度計)'] + [len(s) for s in ws])
q.append(['目的が「その他」'] + [pct(sum(1 for r in s if r['purpose'] == 'その他'), len(s)) for s in ws])
q.append(['業務名 (自由記述) あり'] + [pct(sum(1 for r in s if r['purpose'].strip() not in master), len(s)) for s in ws])
q.append(['担当部署あり'] + [pct(sum(1 for r in s if r['charge_section'].strip()), len(s)) for s in ws])
q.append(['測量地域の市町村あり'] + [pct(sum(1 for r in s if r['muni_codes']), len(s)) for s in ws])
q.append(['実施地域図あり'] + [pct(sum(1 for r in s if r['area_km2']), len(s)) for s in ws])
q.append(['ねらい不明'] + [pct(sum(1 for r in s if r['aim'] == '不明'), len(s)) for s in ws])
q.append(['段階不明'] + [pct(sum(1 for r in s if r['stage'] == '不明'), len(s)) for s in ws])
table('L1 記録の質', ['項目'] + names, q)

# L2 発注主体
def ptype(r):
    return r['planner_type'] if r['planner_type'] in ('北海道', '北海道開発局', '市町村') else 'その他・国など'
table('L2 発注主体 (構成比)', ['発注主体'] + names,
      [[t] + [pct(sum(1 for r in s if ptype(r) == t), len(s)) for s in ws] for t in PTYPES]
      + [['(件数)'] + [len(s) for s in ws]])

# L3 ねらい
table('L3 ねらい (構成比、不明を含む)', ['ねらい'] + names,
      [[a] + [pct(sum(1 for r in s if r['aim'] == a), len(s)) for s in ws] for a in AIMS])
# 不明を除いた構成比 (下限と上限の幅を示すため)
body = []
for a in AIMS[:-1]:
    row = [a]
    for s in ws:
        k = [r for r in s if r['aim'] != '不明']
        n = sum(1 for r in k if r['aim'] == a)
        u = sum(1 for r in s if r['aim'] == '不明')
        row.append(f'{pct(n, len(k))} ({pct(n, len(s))}〜{pct(n + u, len(s))})')
    body.append(row)
table('L3b ねらい (不明を除いた構成比と、不明を全部そこに入れた場合までの幅)', ['ねらい'] + names, body,
      '括弧内は「不明が 1 件も当てはまらない場合」〜「不明が全部当てはまる場合」の構成比。幅が広い期間は結論を出せない。')

# L4 分野
table('L4 分野 (構成比)', ['分野'] + names,
      [[f] + [pct(sum(1 for r in s if r['field'] == f), len(s)) for s in ws] for f in FIELDS])

# L5 農業農村の発注主体
table('L5 農業農村の件数 (発注主体別、3 年度計)', ['発注主体'] + names,
      [[t] + [sum(1 for r in s if r['field'] == '農業農村' and ptype(r) == t) for s in ws] for t in PTYPES])

# L6 地域
body = []
for b in BUREAUS:
    body.append([b] + [pct(sum(1 for r in s if b in r['bureaus'].split()), sum(1 for r in s if r['muni_codes'])) for s in ws])
table('L6 振興局 (関与件数の構成比、市町村が分かる測量に対して)', ['振興局'] + names, body,
      'H1-3 は市町村が分からない測量が多い (L1)。振興局をまたぐ測量は両方に数える。')

# L7 定型語の目的 (古い記録で唯一の手がかり)
top = [p for p, _ in collections.Counter(r['purpose'] for r in rows if r['purpose'] in master).most_common(14)]
table('L7 定型語の目的 (構成比)', ['目的 (定型語)'] + names,
      [[p] + [pct(sum(1 for r in s if r['purpose'] == p), len(s)) for s in ws] for p in top])

# L8 「その他」の中身の手がかり (測量種別)
body = []
for s in ws:
    k = collections.Counter()
    for r in s:
        if r['purpose'] == 'その他':
            for t in r['kinds'].split('|'):
                if t:
                    k[t.replace('【大分類】', '').strip()] += 1
    body.append(k)
kinds = [t for t, _ in sum(body, collections.Counter()).most_common(8)]
table('L8 目的「その他」の測量種別 (延べ)', ['測量種別'] + names, [[t] + [b[t] for b in body] for t in kinds])

(ROOT / 'reports/longterm').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/longterm/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/longterm/tables.md')
