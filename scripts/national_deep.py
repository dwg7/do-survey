#!/usr/bin/env python3
"""北海道の受付の季節の形は「北海道に固有」か「雪の勾配の端」か — 都道府県単位の掘り下げ (D28)。

入力: data/raw/<区分>-<年度>.json (区分 A〜J、令和5〜7年度と平成21・26年度・令和元年度)、analysis/classified.csv (北海道の振興局)
出力: reports/national2/tables.md

- 単位は測量地域の都道府県 (`areaPref`)。複数の都道府県にまたがる測量 (「岩手県,秋田県」など) は除く。北海道は振興局にも分ける。
- 季節の形の指標 (受付月の割合): 4〜5 月、6〜8 月、9〜10 月、11〜12 月、1〜3 月、最多の月、重心 (年度の月番号 4 月 = 1 〜 3 月 = 12 の平均)。
- 緯度は実施地域図のポリゴンの頂点の緯度の中央値 (測量ごと) の、都道府県内の中央値。
- 構成をそろえた比較: 分野 (scripts/classify.py の規則) と発注主体 (national_compare.py の planner_kind) を固定して 6〜8 月の割合を比べる。
- 勾配: 北海道を除く都府県 (件数 100 件以上) で「1〜3 月の割合」「緯度」と「6〜8 月の割合」の直線を引き、北海道がその延長からどれだけ離れるか。
"""
import collections
import csv
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
src = (ROOT / 'scripts/national_compare.py').read_text()
ns = {'__file__': str(ROOT / 'scripts/national_compare.py')}
exec(src.split('arules = classify.load_rules')[0], ns)   # planner_kind・SECTIONS・classify を借りる
planner_kind, SECTIONS, classify = ns['planner_kind'], ns['SECTIONS'], ns['classify']
arules = classify.load_rules('aim-rules.csv')
RECENT = (2023, 2024, 2025)
OLD = (2009, 2014, 2019)
FY = {m: (m - 3 if m >= 4 else m + 9) for m in range(1, 13)}   # 4 月 = 1 … 3 月 = 12


def lat_of(geom):
    try:
        g = json.loads(geom)
    except (TypeError, ValueError):
        return None
    pts = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            pts.append(c[1])
        else:
            for x in c:
                walk(x)
    walk(g.get('coordinates') or [])
    v = statistics.median(pts) if pts else None
    return v if v and 20 < v < 46 else None


def load(years):
    rows = []
    for sec in SECTIONS:
        for y in years:
            for it in json.loads((ROOT / f'data/raw/{sec}-{y}.json').read_text())['items']:
                m = re.match(r'\d{4}/(\d{2})/', it['dateReceptYmd'] or '')
                pref = it.get('areaPref') or ''
                if not m or not pref or ',' in pref:
                    continue
                row = {'planner': it['plannerName'] or '', 'purpose': it['purpose'] or '', 'charge_section': it['chargeSection'] or ''}
                field, _, _ = classify.aim_of(row, arules)
                rows.append({'sec': sec, 'year': y, 'pref': pref, 'month': int(m.group(1)), 'kind': planner_kind(row['planner']),
                             'field': field, 'lat': lat_of(it.get('geom'))})
    return rows


def shape(rs):
    c = collections.Counter(r['month'] for r in rs)
    n = len(rs)
    sh = lambda ms: sum(c[m] for m in ms) / n
    return {'n': n, 'am': sh((4, 5)), 'su': sh((6, 7, 8)), 'au': sh((9, 10)), 'la': sh((11, 12)), 'wi': sh((1, 2, 3)),
            'jul': c[7] / n, 'peak': c.most_common(1)[0][0], 'cg': statistics.mean(FY[r['month']] for r in rs)}


def fit(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sd = (sum(r * r for r in res) / (len(res) - 2)) ** .5
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    return a, b, sd, r


def pct(v):
    return f'{100 * v:.0f}%'


rows = load(RECENT)
by = collections.defaultdict(list)
for r in rows:
    by[r['pref']].append(r)
prefs = [p for p in by if len(by[p]) >= 100]
S = {p: shape(by[p]) for p in prefs}
LAT = {p: statistics.median([r['lat'] for r in by[p] if r['lat']]) for p in prefs}

out = ['# 北海道の季節の形は「固有」か「雪の勾配の端」か — 根拠表\n',
       '`scripts/national_deep.py` が生成。国土地理院「公共測量実施情報」の地方測量部区分 A〜J (受付年度) を dwg7 が編集・加工。'
       '単位は測量地域の都道府県 (複数の都道府県にまたがる測量は除く)。割合は受付月の割合。重心は年度の月番号 (4 月 = 1、3 月 = 12) の平均。'
       '緯度は実施地域図のポリゴンの緯度の中央値の、都道府県内の中央値。\n']

out.append('## T1. 都道府県ごとの受付の季節の形 (令和5〜7年度、6〜8 月の割合の順)\n')
out.append('| 都道府県 | 件数 | 4〜5 月 | 6〜8 月 | 7 月 | 9〜10 月 | 11〜12 月 | 1〜3 月 | 最多の月 | 重心 | 緯度 |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for p in sorted(prefs, key=lambda p: -S[p]['su']):
    s = S[p]
    out.append(f'| {p} | {s["n"]} | {pct(s["am"])} | {pct(s["su"])} | {pct(s["jul"])} | {pct(s["au"])} | {pct(s["la"])} | {pct(s["wi"])} '
               f'| {s["peak"]} 月 | {s["cg"]:.1f} | {LAT[p]:.1f} |')
others = [p for p in prefs if p != '北海道']
out.append(f'\n件数 100 件以上の {len(prefs)} 都道府県。北海道を除く {len(others)} 都府県の 6〜8 月の割合は '
           f'{pct(min(S[p]["su"] for p in others))}〜{pct(max(S[p]["su"] for p in others))}、1〜3 月の割合は '
           f'{pct(min(S[p]["wi"] for p in others))}〜{pct(max(S[p]["wi"] for p in others))}。\n')

# 勾配
out.append('## T2. 勾配の延長と北海道 (北海道を除く都府県で直線を引く)\n')
out.append('| 説明する量 → 説明される量 | 相関 (都府県) | 北海道の予測 | 北海道の実際 | 残差 / 残差の標準偏差 |')
out.append('|---|---:|---:|---:|---:|')
for xl, xf in (('緯度', lambda p: LAT[p]), ('1〜3 月の割合', lambda p: S[p]['wi'])):
    for yl, yk in (('6〜8 月の割合', 'su'), ('1〜3 月の割合', 'wi'), ('重心', 'cg')):
        if xl == yl:
            continue
        xs, ys = [xf(p) for p in others], [S[p][yk] for p in others]
        a, b, sd, r = fit(xs, ys)
        pred = a + b * xf('北海道')
        act = S['北海道'][yk]
        f = (lambda v: f'{v:.1f}') if yk == 'cg' else pct
        out.append(f'| {xl} → {yl} | {r:+.2f} | {f(pred)} | {f(act)} | {(act - pred) / sd:+.1f} |')
out.append('\n残差 / 残差の標準偏差が大きいほど、北海道は都府県の勾配の延長から外れている (勾配の端ではなく、別の形)。\n')

# 雪国の比較
SNOW = ['青森県', '秋田県', '山形県', '岩手県', '新潟県', '富山県', '石川県', '長野県']
out.append('## T3. 冬の受付が少ない都府県 (1〜3 月が 8% 以下) と北海道の月別の形 (令和5〜7年度)\n')
low = [p for p in others if S[p]['wi'] <= 0.08]
out.append('| 都道府県 | ' + ' | '.join(f'{m} 月' for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)) + ' |')
out.append('|---|' + '---:|' * 12)
for p in ['北海道'] + sorted(low, key=lambda p: S[p]['wi']):
    c = collections.Counter(r['month'] for r in by[p])
    out.append(f'| {p} | ' + ' | '.join(pct(c[m] / len(by[p])) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)) + ' |')

# 北海道の中の勾配 (振興局)
cl = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if int(r['year']) in RECENT and r['recept_date']]
bb = collections.defaultdict(list)
for r in cl:
    bs = r['bureaus'].split()
    if len(bs) == 1:
        bb[bs[0]].append({'month': int(r['recept_date'][5:7])})
out.append('\n## T4. 北海道の中の振興局ごとの形 (令和5〜7年度、1 つの振興局だけの測量)\n')
out.append('| 振興局 | 件数 | 4〜5 月 | 6〜8 月 | 7 月 | 9〜10 月 | 11〜12 月 | 1〜3 月 | 最多の月 | 重心 |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for b in sorted(bb, key=lambda b: -shape(bb[b])['su']):
    s = shape(bb[b])
    out.append(f'| {b} | {s["n"]} | {pct(s["am"])} | {pct(s["su"])} | {pct(s["jul"])} | {pct(s["au"])} | {pct(s["la"])} | {pct(s["wi"])} | {s["peak"]} 月 | {s["cg"]:.1f} |')

# 構成をそろえた比較
out.append('\n## T5. 分野・発注主体をそろえた 6〜8 月の割合 (令和5〜7年度、地方ごと)\n')
regs = collections.defaultdict(list)
for r in rows:
    regs[r['sec']].append(r)
cols = [('分野: 農業農村', lambda r: r['field'] == '農業農村'), ('分野: 道路', lambda r: r['field'] == '道路'),
        ('分野: 防災・治水', lambda r: r['field'] == '防災・治水'), ('発注: 都道府県', lambda r: r['kind'] == '都道府県'),
        ('発注: 国', lambda r: r['kind'] == '国'), ('発注: 市区町村', lambda r: r['kind'] == '市区町村')]
out.append('| 地方 | ' + ' | '.join(c for c, _ in cols) + ' |')
out.append('|---|' + '---:|' * len(cols))
colvals = collections.defaultdict(dict)
for sec, name in SECTIONS.items():
    cells = []
    for c, f in cols:
        rs = [r for r in regs[sec] if f(r)]
        if len(rs) >= 30:
            v = shape(rs)['su']
            colvals[c][sec] = v
            cells.append(f'{pct(v)} ({len(rs)})')
        else:
            cells.append('—')
    out.append(f'| {name} | ' + ' | '.join(cells) + ' |')
zrow = []
for c, _ in cols:
    o = [v for s, v in colvals[c].items() if s != 'A']
    zrow.append(f'{(colvals[c]["A"] - statistics.mean(o)) / statistics.stdev(o):+.1f}' if 'A' in colvals[c] and len(o) > 2 else '—')
out.append('| **北海道の z** | ' + ' | '.join(zrow) + ' |')
out.append('\n括弧は件数 (30 件未満は —)。z は他の 9 地方の平均と標準偏差から。\n')

# 長期の安定性
old = load(OLD)
out.append('## T6. 長期の安定性 — 6〜8 月の割合と 1〜3 月の割合の上位 (年度ごと、件数 50 件以上の都道府県)\n')
out.append('| 年度 | 北海道 6〜8 月 | 他の都府県の最大 (6〜8 月) | 北海道 1〜3 月 | 他の都府県の最小 (1〜3 月) |')
out.append('|---|---:|---|---:|---|')
for y in OLD + RECENT:
    rs = [r for r in (old if y in OLD else rows) if r['year'] == y]
    g = collections.defaultdict(list)
    for r in rs:
        g[r['pref']].append(r)
    ss = {p: shape(v) for p, v in g.items() if len(v) >= 50}
    oth = [p for p in ss if p != '北海道']
    top = max(oth, key=lambda p: ss[p]['su'])
    lowp = min(oth, key=lambda p: ss[p]['wi'])
    era = f'H{y - 1988}' if y < 2019 else ('R1' if y == 2019 else f'R{y - 2018}')
    out.append(f'| {era} | {pct(ss["北海道"]["su"])} | {top} {pct(ss[top]["su"])} | {pct(ss["北海道"]["wi"])} | {lowp} {pct(ss[lowp]["wi"])} |')
out.append('')
(ROOT / 'reports/national2').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/national2/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/national2/tables.md')
