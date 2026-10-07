#!/usr/bin/env python3
"""単年度の概況を自然文で書き出し、その情報量を試す (D20)。

天気予報の考え方を借りる:
- 平年値: 各指標の前 5 年度の平均と標準偏差。その年の値を z = (値 − 平均) / 標準偏差 で「平年並み」「多い」などと言い表す。
- 持続予報: 「最も多い分野」などの順位の文は「去年と同じ」と予報した時に当たるかを数える。毎年当たる文は自明 (太陽は東から昇る)。

入力: analysis/classified.csv、data/external/hkd-budget-initial.csv
出力: reports/annual/overviews.md (平成21〜令和7年度の概況、新しい順)、reports/annual/skill.md (文ごとの情報量)
"""
import collections
import csv
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = list(range(2009, 2026))
BASE_N = 5
rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in rows:
    r['year'] = int(r['year'])
    r['bl'] = r['bureaus'].split()
    r['ml'] = r['muni_codes'].split()
munis = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
active = {m['code']: m for m in munis if m['status'] == 'active'}
BUREAUS = list(dict.fromkeys(m['bureau'] for m in active.values()))
by_year = collections.defaultdict(list)
for r in rows:
    by_year[r['year']].append(r)


def era(y):
    if y >= 2019:
        return '令和元年度' if y == 2019 else f'令和{y - 2018}年度'
    return f'平成{y - 1988}年度'


def short(y):
    return f'R{y - 2018}' if y >= 2019 else f'H{y - 1988}'


# ---- 指標 ----
def indicators(y):
    s = by_year[y]
    n = len(s)
    ind = {'件数': n}
    for t in ('北海道', '北海道開発局', '市町村'):
        ind[f'発注:{t}'] = sum(1 for r in s if r['planner_type'] == t) / n
    for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤'):
        ind[f'分野:{f}'] = sum(1 for r in s if r['field'] == f) / n
    withm = [r for r in s if r['ml']]
    for b in BUREAUS:
        ind[f'地域:{b}'] = sum(1 for r in withm if b in r['bl']) / len(withm)
    ind['上期の割合'] = sum(1 for r in s if r['half'] == '上期') / n
    mc = collections.Counter(c for r in s for c in r['ml'] if c in active)
    ind['測量のあった市町村'] = len(mc)
    ind['上位10市町村の割合'] = sum(v for _, v in mc.most_common(10)) / sum(mc.values())
    ind['複数市町村の測量'] = sum(1 for r in s if int(r['n_munis']) > 1) / n
    return ind


IND = {y: indicators(y) for y in range(2004, 2026)}


def top(y, key):
    s = by_year[y]
    if key == '分野':
        c = collections.Counter(r['field'] for r in s)
    elif key == '振興局':
        c = collections.Counter(b for r in s for b in r['bl'])
    elif key == '発注機関':
        c = collections.Counter(r['planner'] for r in s)
    elif key == '市町村':
        c = collections.Counter(active[c]['fullName'] for r in s for c in r['ml'] if c in active)
    elif key == '受付月':
        c = collections.Counter(int(r['recept_date'][5:7]) for r in s if r['recept_date'])
    return c.most_common(3)


def sampling_sd(y, k, m):
    """偶然のぶれの目安。割合は二項 sqrt(p(1-p)/n)、件数・市町村数はポアソン sqrt(平均)。"""
    if k in ('件数', '測量のあった市町村'):
        return max(m, 1) ** 0.5
    nn = len(by_year[y])
    return (max(m, 1 / nn) * (1 - min(m, 1 - 1 / nn)) / nn) ** 0.5


def normal(y, k):
    vals = [IND[x][k] for x in range(y - BASE_N, y)]
    m = statistics.mean(vals)
    return m, max(statistics.stdev(vals), sampling_sd(y, k, m))


def trend(y, k):
    """前 5 年度の直線の延長 (傾向予報) と、その当てはまりのばらつき。"""
    xs = list(range(y - BASE_N, y))
    vals = [IND[x][k] for x in xs]
    mx, mv = statistics.mean(xs), statistics.mean(vals)
    b = sum((x - mx) * (v - mv) for x, v in zip(xs, vals)) / sum((x - mx) ** 2 for x in xs)
    pred = mv + b * (y - mx)
    res = [v - (mv + b * (x - mx)) for x, v in zip(xs, vals)]
    sd = (sum(r * r for r in res) / (len(res) - 2)) ** 0.5
    return pred, max(sd, sampling_sd(y, k, max(pred, 0)))


def z(y, k):
    m, sd = normal(y, k)
    return (IND[y][k] - m) / sd


def zt(y, k):
    pred, sd = trend(y, k)
    return (IND[y][k] - pred) / sd


# 比べる指標の数 k に応じたしきい値 (k 個のうち最大の |z| が偶然この値を超える確率が 32% / 5% になる値)
THR = {1: (1.0, 2.0), 3: (1.61, 2.39), 6: (1.93, 2.64), 14: (2.21, 2.91)}


def word(zv, more='多い', less='少ない', k=1, ztr=None):
    t1, t2 = THR[k]
    if zv >= t2:
        w = f'平年よりかなり{more}'
    elif zv >= t1:
        w = f'平年より{more}'
    elif zv <= -t2:
        w = f'平年よりかなり{less}'
    elif zv <= -t1:
        w = f'平年より{less}'
    else:
        return '平年並み'
    if ztr is not None and abs(ztr) < t1:
        w += ' (ただし近年の傾向どおり)'
    return w


def level(zv, ztr, k=1):
    """文の情報の段階: 0 平年並み、1 平年と違うが傾向どおり、2 予想外 (平年からも傾向からも外れる)、3 かなり予想外。"""
    t1, t2 = THR[k]
    if abs(zv) < t1:
        return 0
    if abs(ztr) < t1:
        return 1
    return 3 if (abs(zv) >= t2 and abs(ztr) >= t2) else 2


def pct(v):
    return f'{100 * v:.0f}%'


def bname(b):
    return b if b in ('オホーツク',) else b


# ---- 文 (スロット) ----
SLOTS = []   # (年, スロット名, 種類, 値, 情報の段階 or 差が有意か)


def q(y, slot, k, key, more='多い', less='少ない'):
    """量の文の述語を返し、評価用に記録する。"""
    zn, ztr = z(y, key), zt(y, key)
    SLOTS.append((y, slot, 'z', zn, level(zn, ztr, k)))
    return word(zn, more, less, k, ztr)


def rank(y, slot, items):
    """順位の文を記録する。1 位と 2 位の差が偶然のぶれ (2 sqrt(a+b)) より大きいか。"""
    (v1, c1), (v2, c2) = items[0], items[1]
    SLOTS.append((y, slot, 'top', v1, (c1 - c2) > 2 * (c1 + c2) ** 0.5))
    return v1


def overview(y):
    s = by_year[y]
    n = len(s)
    ind = IND[y]
    L = []
    m, _ = normal(y, '件数')
    L.append(f'{era(y)}の公共測量は {n} 件で、{q(y, "件数", 1, "件数")} (平年 {m:.0f} 件)。')
    parts = []
    for t, short_t in (('北海道', '北海道'), ('北海道開発局', '開発局'), ('市町村', '市町村')):
        w = q(y, f'発注:{short_t}', 3, f'発注:{t}', '高い', '低い')
        if w != '平年並み':
            parts.append(f'{short_t}の割合が{w}')
    L.append(f'発注は北海道 {pct(ind["発注:北海道"])}・開発局 {pct(ind["発注:北海道開発局"])}・市町村 {pct(ind["発注:市町村"])}で、'
             + ('、'.join(parts) if parts else '割合はいずれも平年並み') + '。')
    tp = top(y, '発注機関')
    name = rank(y, '最多の発注機関', tp)
    L.append(f'最も多く発注したのは{name.replace("北海道", "", 1) if "開発局" not in name else name} ({tp[0][1]} 件)。')
    tf = top(y, '分野')
    rank(y, '最多の分野', tf)
    L.append(f'分野で最も多いのは{tf[0][0]} ({pct(tf[0][1] / n)})、次いで{tf[1][0]} ({pct(tf[1][1] / n)})。')
    parts = []
    for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤'):
        w = q(y, f'分野:{f}', 6, f'分野:{f}')
        if w != '平年並み':
            parts.append(f'{f}が{w.replace("平年より", "")}')
    L.append(('平年と比べると、' + '、'.join(parts) + '。') if parts else '分野の構成は平年並み。')
    tb = top(y, '振興局')
    rank(y, '最多の振興局', tb)
    L.append(f'地域では{tb[0][0]} ({tb[0][1]} 件)・{tb[1][0]}・{tb[2][0]}が多い。')
    parts = []
    for bb in BUREAUS:
        w = q(y, f'地域:{bb}', 14, f'地域:{bb}', '高い', '低い')
        if w != '平年並み':
            parts.append(f'{bb}の割合が{w.replace("平年より", "")}')
    L.append(('平年と比べると、' + '、'.join(parts) + '。') if parts else '地域の構成は平年並み。')
    tm = top(y, '市町村')
    rank(y, '最多の市町村', tm)
    L.append(f'市町村では{tm[0][0]} ({tm[0][1]} 件)・{tm[1][0]}・{tm[2][0]}が多い。')
    L.append(f'測量のあった市町村は {ind["測量のあった市町村"]} で{q(y, "広がり:市町村数", 1, "測量のあった市町村")}、'
             f'上位 10 市町村の割合は {pct(ind["上位10市町村の割合"])} で{q(y, "広がり:集中", 1, "上位10市町村の割合", "高い", "低い")}。')
    mo = top(y, '受付月')
    rank(y, '最多の受付月', [(f'{mo[0][0]} 月', mo[0][1]), (f'{mo[1][0]} 月', mo[1][1])])
    L.append(f'受付は {mo[0][0]} 月が最も多く、上期 (4〜9 月) が {pct(ind["上期の割合"])} で{q(y, "時期:上期", 1, "上期の割合", "高い", "低い")}。')
    return L


def changes(y):
    """その年に初めて (前 5 年度に 0 件) 現れた計画機関・目立って増えた業務名の語。"""
    prev = {r['planner'] for x in range(y - BASE_N, y) for r in by_year[x]}
    new = collections.Counter(r['planner'] for r in by_year[y] if r['planner'] not in prev)
    return new.most_common(4)


out = ['# 単年度の概況 (自然文) — 平成21〜令和7年度\n',
       '`scripts/annual_overview.py` が同じ規則で書いた概況。「平年」は前 5 年度の平均、「平年より多い」は平均から 1 標準偏差以上、'
       '「かなり」は 2 標準偏差以上。件数は測量の需要であって事業の規模ではない (D19)。'
       '令和7年度は 4〜8 月の受付に業務名の欠けがあり、令和6年度以降の道営農業の増加は届出の増加とみられる (D16)。\n']
for y in reversed(YEARS):
    out.append(f'\n## {era(y)} ({y})\n')
    out.append(''.join(overview(y)))
    nw = changes(y)
    if nw:
        out.append('\n\n前 5 年度に登録のなかった計画機関: ' + '、'.join(f'{p} {c}' for p, c in nw) + '。')
    out.append('')
(ROOT / 'reports/annual').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/annual/overviews.md').write_text('\n'.join(out) + '\n')

# ---- 情報量の評価 ----
GROUP = lambda slot: slot.split(':')[0]
sk = ['# 概況の文の情報量 — 持続予報・平年・傾向\n',
      '`scripts/annual_overview.py` が生成。対象は平成21〜令和7年度の 17 年。平年は前 5 年度の平均、傾向は前 5 年度の直線の延長。'
      'ばらつきは前 5 年度の標準偏差と偶然のぶれ (件数はポアソン、割合は二項) の大きい方。'
      '比べる指標が k 個ある文 (発注 3、分野 6、地域 14) は、k 個の最大値が偶然超える確率が 32% / 5% になるしきい値を使う。\n',
      '\n## 順位の文: 「去年と同じ」と予報した時の的中率\n',
      '| 文 | 的中 / 年 | 的中率 | 1 位と 2 位の差が偶然のぶれより大きい年 | 17 年で現れた値 |', '|---|---:|---:|---:|---|']
bys = collections.defaultdict(dict)
for y, slot, kind, value, info in SLOTS:
    bys[slot][y] = (kind, value, info)
for slot, d in bys.items():
    if next(iter(d.values()))[0] != 'top':
        continue
    ys = sorted(d)
    hit = sum(1 for a_, b_ in zip(ys, ys[1:]) if d[a_][1] == d[b_][1])
    sig = sum(1 for y in ys if d[y][2])
    vals = collections.Counter(d[y][1] for y in ys)
    sk.append(f'| {slot} | {hit} / {len(ys) - 1} | {pct(hit / (len(ys) - 1))} | {sig} / {len(ys)} | '
              + '、'.join(f'{v} ({c})' for v, c in vals.most_common()) + ' |')
sk += ['\n## 量の文: 平年並み・傾向どおり・予想外\n',
       '1 つの文 (行) の中に複数の指標がある時 (発注・分野・地域) は、年ごとに最も情報の大きい指標で数える。\n',
       '| 文 | 平年並み | 平年と違うが傾向どおり | 予想外 | かなり予想外 | 予想外だった年 (指標) |', '|---|---:|---:|---:|---:|---|']
grp = collections.defaultdict(lambda: collections.defaultdict(list))
for y, slot, kind, value, info in SLOTS:
    if kind == 'z':
        grp[GROUP(slot)][y].append((info, slot, value))
for g, d in grp.items():
    best = {y: max(v) for y, v in d.items()}
    cnt = collections.Counter(b[0] for b in best.values())
    yrs = '、'.join(f'{short(y)} ({b[1].split(":")[-1]} {b[2]:+.1f})' for y, b in sorted(best.items()) if b[0] >= 2)
    sk.append(f'| {g} | {cnt[0]} | {cnt[1]} | {cnt[2]} | {cnt[3]} | {yrs} |')
(ROOT / 'reports/annual/skill.md').write_text('\n'.join(sk) + '\n')
print('wrote reports/annual/overviews.md, reports/annual/skill.md')
