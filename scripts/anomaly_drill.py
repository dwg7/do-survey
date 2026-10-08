#!/usr/bin/env python3
"""原因の分からない「予想外」4 件の掘り下げ (D24)。

入力: analysis/classified.csv (scripts/classify.py の出力)
出力: reports/anomaly/tables.md

対象は reports/annual/summary.md で「不明」に残した 4 件: 平成23年度の空知 (+)、平成26年度の上川 (+)、
平成28年度の釧路 (−)、令和4年度の上川 (−)。
物差しは scripts/annual_overview.py と同じ: 地域の割合 = その振興局に関わった測量 / 市町村の分かる測量、
平年 = 前 5 年度の平均。これに加えて、比べる土台を平成21年度以降に限った「長期の平年」(その年度を除く平成21〜令和7年度) でも測る。
内訳は「その年度の件数 − 前 5 年度の平均件数」(振興局に関わった測量の件数) を、計画機関・担当部署・分野・市町村ごとに出す。
"""
import collections
import csv
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = [('空知', 2011), ('上川', 2014), ('釧路', 2016), ('上川', 2022)]
LONG = list(range(2009, 2026))
rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in rows:
    r['year'] = int(r['year'])
    r['bl'] = r['bureaus'].split()
    r['ml'] = r['muni_codes'].split()
munis = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
mname = {m['code']: m['fullName'] for m in munis if m['status'] == 'active'}
by_year = collections.defaultdict(list)
for r in rows:
    by_year[r['year']].append(r)


def era(y):
    return f'R{y - 2018}' if y >= 2019 else f'H{y - 1988}'


def era_long(y):
    if y >= 2019:
        return '令和元年度' if y == 2019 else f'令和{y - 2018}年度'
    return f'平成{y - 1988}年度'


def count(b, y):
    return sum(1 for r in by_year[y] if b in r['bl'])


def share(b, y):
    withm = [r for r in by_year[y] if r['ml']]
    return count(b, y) / len(withm)


def zscore(v, vals):
    return (v - statistics.mean(vals)) / statistics.stdev(vals)


def section(r):
    return f"{r['planner']} {r['charge_section']}".strip()


def field_of(r):
    return r['field']


def munis_of(r, b):
    return [mname[c] for c in r['ml'] if c in mname and b in r['bl']]


out = ['# 原因の分からない「予想外」4 件の掘り下げ — 根拠表\n',
       '`scripts/anomaly_drill.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) を dwg7 が編集・加工。'
       '地域の割合 = その振興局に関わった測量 / 市町村の分かる測量 (`scripts/annual_overview.py` と同じ)。'
       '平年 = 前 5 年度の平均、長期の平年 = その年度を除く平成21〜令和7年度の平均。z は (値 − 平均) / 標準偏差。\n']

out.append('## T1. 4 件の振興局の推移 (件数 / 割合)\n')
ys = list(range(2004, 2027))
bs = list(dict.fromkeys(b for b, _ in CASES))
out.append('| 年度 | 全件 | ' + ' | '.join(bs) + ' |')
out.append('|---|---:|' + '---:|' * len(bs))
for y in ys:
    mark = {b for b, yy in CASES if yy == y}
    cells = []
    for b in bs:
        c = f'{count(b, y)} / {100 * share(b, y):.0f}%'
        cells.append(f'**{c}**' if b in mark else c)
    out.append(f'| {era(y)} ({y}) | {len(by_year[y])} | ' + ' | '.join(cells) + ' |')
out.append('\n令和8年度 (2026) は途中 (9/17 受付分まで)。太字が「予想外」の年度。\n')

out.append('## T2. 物差しを変えた時の z\n')
out.append('| 件 | 割合 | 前 5 年度の平均 | z (前 5 年度) | 長期の平年 (H21〜R7、その年を除く) | z (長期) | 件数 | 件数の z (長期) |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|')
for b, y in CASES:
    prev = [share(b, x) for x in range(y - 5, y)]
    lng = [share(b, x) for x in LONG if x != y]
    lc = [count(b, x) for x in LONG if x != y]
    out.append(f'| {era_long(y)} {b} | {100 * share(b, y):.1f}% | {100 * statistics.mean(prev):.1f}% | {zscore(share(b, y), prev):+.1f} '
               f'| {100 * statistics.mean(lng):.1f}% | {zscore(share(b, y), lng):+.1f} | {count(b, y)} | {zscore(count(b, y), lc):+.1f} |')
out.append('\n前 5 年度の z は標準偏差に偶然のぶれの下限を置かない素の値 (概況のスクリプトは下限を置くので値が少し違う)。\n')


def share_of(b, y, flt):
    s = [r for r in by_year[y] if r['ml'] and flt(r)]
    return sum(1 for r in s if b in r['bl']) / len(s)


out.append('\n**T2b. 発注主体を分けた割合 (長期の平年との比較)** — 割合の分母も同じ発注主体に限る。'
           '「全体」の z が「開発局を除く」で下がるなら、その分は開発局の件数の増減が分母を動かした効果。\n')
SUBSETS = [('全体', lambda r: True), ('開発局を除く', lambda r: r['planner_type'] != '北海道開発局'),
           ('道のみ', lambda r: r['planner_type'] == '北海道'), ('開発局のみ', lambda r: r['planner_type'] == '北海道開発局')]
out.append('| 件 | ' + ' | '.join(f'{lab} (割合 / 長期 / z)' for lab, _ in SUBSETS) + ' |')
out.append('|---|' + '---:|' * len(SUBSETS))
for b, y in CASES:
    cells = []
    for _, f in SUBSETS:
        v = share_of(b, y, f)
        lng = [share_of(b, x, f) for x in LONG if x != y]
        cells.append(f'{100 * v:.1f}% / {100 * statistics.mean(lng):.1f}% / {zscore(v, lng):+.1f}')
    out.append(f'| {era_long(y)} {b} | ' + ' | '.join(cells) + ' |')
out.append('')


def diff_table(title, b, y, key, top=12, multi=False):
    cy, cr = collections.Counter(), collections.Counter()
    for x in range(y - 5, y + 1):
        for r in by_year[x]:
            if b not in r['bl']:
                continue
            ks = key(r) if multi else [key(r)]
            for k in ks:
                (cy if x == y else cr)[k] += 1
    ks = sorted(set(cy) | set(cr), key=lambda k: (-abs(cy[k] - cr[k] / 5), k))[:top]
    out.append(f'\n**{title}** (その年度 / 前 5 年度の平均 / 差)\n')
    out.append('| 項目 | その年度 | 前 5 年度の平均 | 差 |')
    out.append('|---|---:|---:|---:|')
    for k in ks:
        out.append(f'| {k or "(空)"} | {cy[k]} | {cr[k] / 5:.1f} | {cy[k] - cr[k] / 5:+.1f} |')


for i, (b, y) in enumerate(CASES, 3):
    out.append(f'\n## T{i}. {era_long(y)} の{b} — 内訳の差\n')
    out.append(f'{b}に関わった測量 {count(b, y)} 件 (前 5 年度の平均 {statistics.mean(count(b, x) for x in range(y - 5, y)):.1f} 件)。'
               f'全件は {len(by_year[y])} 件 (同 {statistics.mean(len(by_year[x]) for x in range(y - 5, y)):.1f} 件)。')
    diff_table('計画機関', b, y, lambda r: r['planner'], top=8)
    diff_table('計画機関と担当部署 (担当部署は平成21年度から。名前の揺れは T7 で束ねる)', b, y, section, top=10)
    diff_table('分野', b, y, field_of, top=8)
    diff_table('市町村 (その振興局の中)', b, y, lambda r: munis_of(r, b), top=10, multi=True)
    if y >= 2012:   # 業務名 (自由記述) は平成24年度ごろから
        purp = collections.Counter(r['purpose'][:28] for r in by_year[y] if b in r['bl'] and r['field'] == '農業農村')
        out.append(f'\n**業務名 (農業農村、先頭 28 字、上位 12)**\n')
        out.append('| 業務名 | 件数 |')
        out.append('|---|---:|')
        for k, v in purp.most_common(12):
            out.append(f'| {k.replace("|", "／")} | {v} |')

# 担当部署の名前は年度で変わる (支庁の再編、表記の空白など)。主な発注機関の担当部署を年度ごとに並べる。
SERIES = [('空知', '北海道空知総合振興局', ['北部耕地', '東部耕地', '南部耕地', '建設管理部']),
          ('空知', '北海道石狩振興局', ['札幌土木現業所', '産業振興部']),
          ('上川', '北海道上川総合振興局', ['耕地', '整備課', '調整課', '建設管理部']),
          ('上川', '北海道開発局旭川開発建設部', ['農業', '公物管理', '用地', '治水']),
          ('釧路', '北海道釧路総合振興局', ['農村振興', '建設管理部']),
          ('釧路', '北海道開発局釧路開発建設部', ['農業', '用地', '道路', '公物管理'])]
n = 3 + len(CASES)
out.append(f'\n## T{n}. 主な発注機関の担当部署 (名前の一部で束ねる) の推移\n')
ys = list(range(2009, 2027))
out.append('| 振興局 | 計画機関 | 担当部署 | ' + ' | '.join(era(y) for y in ys) + ' |')
out.append('|---|---|---|' + '---:|' * len(ys))
for b, pl, parts in SERIES:
    sub = [r for r in rows if r['planner'] == pl and b in r['bl']]
    for p in parts + ['(計)']:
        c = collections.Counter(r['year'] for r in sub if p == '(計)' or p in r['charge_section'])
        out.append(f'| {b} | {pl.replace("北海道開発局", "開発局")} | {p} | ' + ' | '.join(str(c[y]) for y in ys) + ' |')
out.append('\n「北海道石狩振興局」の平成21年度以前は札幌土木現業所 (平成22年度の支庁再編で空知総合振興局の札幌建設管理部へ) の記録で、'
           '計画機関名が現在の名前に置き換えられている (記録の形、レンズの癖 3)。担当部署の名前を部分一致で束ねるので、'
           '同じ部署が年度で別の名前になると別の行に分かれることがある。\n')

n += 1
out.append(f'\n## T{n}. 分野別の推移 (振興局に関わった測量)\n')
for b in bs:
    sub = [r for r in rows if b in r['bl'] and 2009 <= r['year']]
    fs = [f for f, _ in collections.Counter(r['field'] for r in sub).most_common(5)]
    out.append(f'\n**{b}**\n')
    out.append('| 分野 | ' + ' | '.join(era(y) for y in ys) + ' |')
    out.append('|---|' + '---:|' * len(ys))
    for f in fs + ['(計)']:
        c = collections.Counter(r['year'] for r in sub if f == '(計)' or r['field'] == f)
        out.append(f'| {f} | ' + ' | '.join(str(c[y]) for y in ys) + ' |')

out.append('\n**釧路の「地籍・登記・課税」の業務名 (先頭 4 字で束ねる)**\n')
ys2 = list(range(2012, 2019))
sub = [r for r in rows if '釧路' in r['bl'] and r['field'] == '地籍・登記・課税' and r['year'] in ys2]
heads = [k for k, _ in collections.Counter(r['purpose'][:4] for r in sub).most_common(6)]
out.append('| 業務名の先頭 | ' + ' | '.join(era(y) for y in ys2) + ' |')
out.append('|---|' + '---:|' * len(ys2))
for h in heads:
    c = collections.Counter(r['year'] for r in sub if r['purpose'][:4] == h)
    out.append(f'| {h} | ' + ' | '.join(str(c[y]) for y in ys2) + ' |')

(ROOT / 'reports/anomaly').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/anomaly/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/anomaly/tables.md')
