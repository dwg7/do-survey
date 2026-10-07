#!/usr/bin/env python3
"""件数と事業費 (北海道開発局関係予算、当初) の突き合わせ (D19)。

入力: analysis/classified.csv、data/external/hkd-budget-initial.csv (scripts/fetch_budget.py)
出力: reports/budget/compare.md

対応のさせ方 (どちらも受付年度 = 予算年度):
- 開発局の測量 (計画機関が北海道開発局) ↔ 直轄。分野: 道路 ↔ 道路、防災・治水 ↔ 治水、農業農村 ↔ 農業農村整備。
- 道の測量 (計画機関が北海道) の農業農村 ↔ 補助の農業農村整備 (道営事業の国費。道費は含まない)。
当初予算だけで、補正予算 (経済対策・国土強靱化など) は含まない。補正の多い年はずれる。
"""
import csv
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = list(range(2009, 2026))

rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
bud = {(int(r['year']), r['kind']): r for r in csv.DictReader((ROOT / 'data/external/hkd-budget-initial.csv').open())}


def n(pt, field=None, y=None):
    return sum(1 for r in rows if int(r['year']) == y and r['planner_type'] == pt and (field is None or r['field'] == field))


def b(y, kind, key):
    v = bud[(y, kind)][key]
    return int(v) / 100 if v else None   # 億円


def corr(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    mx = sum(p[0] for p in pairs) / len(pairs)
    my = sum(p[1] for p in pairs) / len(pairs)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    sx = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs))
    sy = math.sqrt(sum((p[1] - my) ** 2 for p in pairs))
    return sxy / (sx * sy)


def sign_agree(xs, ys):
    d = [(xs[i] - xs[i - 1], ys[i] - ys[i - 1]) for i in range(1, len(xs)) if None not in (xs[i], xs[i - 1], ys[i], ys[i - 1])]
    agree = sum(1 for a, c in d if (a > 0 and c > 0) or (a < 0 and c < 0))
    return agree, len(d)


def era(y):
    return f'R{y - 2018}' if y >= 2019 else f'H{y - 1988}'


out = ['# 件数と事業費の突き合わせ (北海道開発局関係予算、当初)\n',
       '`scripts/budget_compare.py` が生成。予算は北海道開発局「予算概要」の各年度の当初予算 (事業費、国費、億円)。'
       '補正予算は含まない。出典 URL は `data/external/hkd-budget-initial.csv`。\n']


def table(title, head, body, note=None):
    out.append(f'\n## {title}\n')
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(head))) + '|')
    for row in body:
        out.append('| ' + ' | '.join('—' if x is None else (f'{x:,.0f}' if isinstance(x, float) else str(x)) for x in row) + ' |')
    if note:
        out.append(f'\n{note}')
    out.append('')


# B1 開発局: 直轄予算と件数
body = []
series = {k: ([], []) for k in ('total', 'road', 'flood', 'agri')}
for y in YEARS:
    c_all, c_road, c_flood, c_agri = n('北海道開発局', y=y), n('北海道開発局', '道路', y), n('北海道開発局', '防災・治水', y), n('北海道開発局', '農業農村', y)
    t, rd, fl, ag = b(y, 'direct', 'total'), b(y, 'direct', 'road'), b(y, 'direct', 'flood'), b(y, 'direct', 'agri')
    for k, c, v in (('total', c_all, t), ('road', c_road, rd), ('flood', c_flood, fl), ('agri', c_agri, ag)):
        series[k][0].append(v)
        series[k][1].append(c)
    body.append([f'{era(y)} ({y})', t, c_all, rd, c_road, fl, c_flood, ag, c_agri])
table('B1 開発局: 直轄の当初予算 (億円) と測量件数',
      ['年度', '直轄計', '件数', '道路 予算', '道路 件数', '治水 予算', '防災・治水 件数', '農業農村 予算', '農業農村 件数'], body)
body = []
for k, label in (('total', '直轄計'), ('road', '道路'), ('flood', '治水 ↔ 防災・治水'), ('agri', '農業農村')):
    xs, ys = series[k]
    ag, nn = sign_agree(xs, ys)
    body.append([label, f'{corr(xs, ys):.2f}', f'{ag} / {nn}'])
table('B1b 予算と件数の連動 (平成21〜令和7年度)', ['対応', '水準の相関係数', '前年からの増減の向きが一致した年'], body,
      '相関は 17 年の水準どうし。増減の向きは前年度比の符号が一致した年の数。')

# B2 測量の密度 (件 / 100 億円)
body = []
for y in (2010, 2015, 2020, 2025):
    row = [f'{era(y)} ({y})']
    for key, field in (('road', '道路'), ('flood', '防災・治水'), ('agri', '農業農村')):
        v = b(y, 'direct', key)
        row.append(f'{100 * n("北海道開発局", field, y) / v:.1f}')
    body.append(row)
table('B2 開発局の測量の密度 (件 / 直轄当初予算 100 億円)', ['年度', '道路', '治水 (防災・治水)', '農業農村'], body,
      '同じ 100 億円あたり、農業農村は道路の何倍の測量を出すか。件数が規模を表さないことの目安。')

# B3 道営の農業と補助の農業農村整備
body = []
xs, ys = [], []
for y in YEARS:
    v = b(y, 'subsidy', 'agri')
    c = n('北海道', '農業農村', y)
    xs.append(v)
    ys.append(c)
    body.append([f'{era(y)} ({y})', v, c, f'{100 * c / v:.1f}' if v else None])
table('B3 道の農業農村の測量件数と、補助の農業農村整備 (当初、国費)', ['年度', '補助 農業農村整備 (億円)', '道の農業農村の測量', '件 / 100 億円'], body,
      '平成23年度の補助の表には農業農村整備がない (「この外」とされ、農山漁村地域整備交付金に計上)。'
      '補助の国費だけで、道費や交付金は含まない。')

(ROOT / 'reports/budget').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/budget/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/budget/compare.md')
