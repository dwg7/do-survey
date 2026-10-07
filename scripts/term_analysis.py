#!/usr/bin/env python3
"""測量期間 (工期) の分析: 航空撮影の時期と工期、工期の分布とその決まり方 (D22)。

入力: data/surveys.parquet (duckdb CLI で読む)
出力: reports/term/tables.md

- 工期 = 測量期間の終了日 − 開始日 + 1 (日)。終了日が開始日より前の 3 件は除く。
- 航空系の群は測量種別で分ける: 航空写真 (「撮影」「空中写真」を含む)、航空レーザ、UAV、地上のみ。
  記録の期間は作業の「窓」(契約上の期間) で、撮影日そのものは分からない。
- 主な対象は平成21〜令和7年度 (業務名・担当部署のある時代、D17)。航空写真はフィルムの時代 (〜平成20年度) とも比べる。
"""
import collections
import csv
import datetime as dt
import io
import math
import pathlib
import re
import statistics
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
GROUPS = ['航空写真', '航空レーザ', 'UAV', '地上のみ']

q = """COPY (SELECT year, term_from, term_to, array_to_string(contents_types,'|') AS kinds,
               array_to_string(contents_amounts,'|') AS amts FROM 'data/surveys.parquet'
        WHERE term_from IS NOT NULL AND term_to IS NOT NULL) TO '/dev/stdout' (FORMAT csv, HEADER)"""
raw = list(csv.DictReader(io.StringIO(subprocess.run(['duckdb', '-c', q], capture_output=True, text=True, check=True, cwd=ROOT).stdout)))


def grp(k):
    if re.search('撮影|空中写真', k):
        return '航空写真'
    if '航空レーザ' in k:
        return '航空レーザ'
    if 'ＵＡＶ' in k or 'UAV' in k:
        return 'UAV'
    return '地上のみ'


rows = []
for r in raw:
    a, b = dt.date.fromisoformat(r['term_from']), dt.date.fromisoformat(r['term_to'])
    if b < a:
        continue
    y = int(r['year'])
    rows.append({'year': y, 'a': a, 'b': b, 'days': (b - a).days + 1, 'g': grp(r['kinds']), 'kinds': r['kinds'], 'amts': r['amts'],
                 'over': b > dt.date(y + 1, 3, 31), 'rem': (dt.date(y + 1, 3, 31) - a).days, 'start': (a - dt.date(y, 4, 1)).days})
mod = [r for r in rows if 2009 <= r['year'] <= 2025]

out = ['# 測量期間 (工期) の分析 — 表\n', '`scripts/term_analysis.py` が生成。主に平成21〜令和7年度。'
       '記録の期間は契約上の作業の窓で、撮影日や作業日そのものではない。\n']


def table(title, head, body, note=None):
    out.append(f'\n## {title}\n')
    out.append('| ' + ' | '.join(head) + ' |')
    out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(head))) + '|')
    for row in body:
        out.append('| ' + ' | '.join(str(x) for x in row) + ' |')
    if note:
        out.append(f'\n{note}')
    out.append('')


def q3(xs):
    xs = sorted(xs)
    return statistics.median(xs), xs[len(xs) // 4], xs[3 * len(xs) // 4]


# T1 群ごとの工期
body = []
for g in GROUPS:
    for era, sel in (('H21〜R7', lambda r: 2009 <= r['year'] <= 2025), ('〜H20', lambda r: r['year'] <= 2008)):
        s = [r for r in rows if r['g'] == g and sel(r)]
        if len(s) < 5:
            continue
        m, lo, hi = q3([r['days'] for r in s])
        body.append([g, era, len(s), f'{m:.0f}', f'{lo}〜{hi}', f'{100 * sum(r["over"] for r in s) / len(s):.0f}%'])
table('T1 航空系と地上の工期 (日)', ['群', '時代', '件数', '中央値', '四分位', '年度末を越える'], body)

# T2 時期: 開始月・終了月・工期に含まれる月
for title, fn in (('T2a 開始月 (群ごとの構成比)', lambda r: {r['a'].month}), ('T2b 終了月 (群ごとの構成比)', lambda r: {r['b'].month})):
    body = []
    for g in GROUPS:
        s = [r for r in mod if r['g'] == g]
        c = collections.Counter(m for r in s for m in fn(r))
        body.append([g, len(s)] + [f'{100 * c[m] / len(s):.0f}%' for m in ORDER])
    table(title, ['群', '件数'] + [f'{m}月' for m in ORDER], body)


def months_covered(r):
    ms, d = set(), r['a'].replace(day=1)
    while d <= r['b'] and len(ms) < 12:
        ms.add(d.month)
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return ms


body = []
for g in GROUPS:
    s = [r for r in mod if r['g'] == g]
    c = collections.Counter(m for r in s for m in months_covered(r))
    body.append([g, len(s)] + [f'{100 * c[m] / len(s):.0f}%' for m in ORDER])
table('T2c 工期にその月を含む割合 (作業の窓が開いている月)', ['群', '件数'] + [f'{m}月' for m in ORDER], body)

# T3 開始の季節別の工期
SEASON = {4: '春 (4-5)', 5: '春 (4-5)', 6: '初夏 (6)', 7: '夏 (7-8)', 8: '夏 (7-8)', 9: '秋 (9-11)', 10: '秋 (9-11)', 11: '秋 (9-11)'}
seasons = ['春 (4-5)', '初夏 (6)', '夏 (7-8)', '秋 (9-11)', '冬 (12-3)']
body = []
for g in ['航空写真', '航空レーザ', '地上のみ']:
    row = [g]
    for se in seasons:
        s = [r['days'] for r in mod if r['g'] == g and SEASON.get(r['a'].month, '冬 (12-3)') == se]
        row.append(f'{statistics.median(s):.0f} ({len(s)})' if s else '—')
    body.append(row)
table('T3 開始の季節別の工期の中央値 (日、括弧は件数)', ['群'] + seasons, body)

# T4 工期の長さの分布
c = collections.Counter(min(r['days'] // 10 * 10, 400) for r in mod)
table('T4 工期の長さの分布 (10 日刻み)', ['工期 (日)', '件数'], [[f'{k}〜{k + 9}' if k < 400 else '400〜', c[k]] for k in sorted(c)])

# T5 終了日
n = len(mod)
dd = collections.Counter()
for r in mod:
    b = r['b']
    last = (b.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    dd['月末' if b == last else (f'{b.day} 日' if b.day in (10, 15, 20, 25) else 'その他')] += 1
table('T5 終了日の「日」', ['日', '割合'], [[k, f'{100 * v / n:.1f}%'] for k, v in dd.most_common()],
      '偶然なら 10 日・20 日・月末はそれぞれ約 3.3%。')
md = collections.Counter(r['b'].strftime('%m/%d') for r in mod)
table('T5b 終了日の上位', ['月日', '件数', '割合'], [[k, v, f'{100 * v / n:.1f}%'] for k, v in md.most_common(12)])


# T6 工期を決めるもの: 作業量か暦か
def rank(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0] * len(xs)
    for k, i in enumerate(o):
        rk[i] = k
    return rk


def spearman(x, y):
    rx, ry = rank(x), rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))


base = []
for r in mod:
    m = re.fullmatch(r'\s*(\d+)\s*点\s*', r['amts'])
    if r['kinds'].strip() == '基準点測量' and m:
        base.append((int(m.group(1)), r['days'], r['start']))
pts, days, start = zip(*base)
body = [['基準点測量だけの測量の点数', len(base), f'{spearman(pts, days):+.2f}'],
        ['同じ測量の開始日 (年度初めからの日数)', len(base), f'{spearman(start, days):+.2f}'],
        ['全測量の年度末までの残り日数', len(mod), f'{spearman([r["rem"] for r in mod], [r["days"] for r in mod]):+.2f}']]
table('T6 工期との順位相関', ['説明する量', '件数', '順位相関'], body)
bins = [(1, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 10 ** 6)]
table('T6b 基準点の点数別の工期の中央値', ['点数', '件数', '工期の中央値 (日)'],
      [[f'{a}〜{b}' if b < 10 ** 6 else f'{a}〜', sum(1 for p in pts if a <= p <= b), f'{statistics.median([d for p, d in zip(pts, days) if a <= p <= b]):.0f}']
       for a, b in bins])
ratio = statistics.median(r['days'] / max(1, r['rem']) for r in mod)
out.append(f'工期 / 年度末までの残り日数 の中央値: {ratio:.2f}\n')

(ROOT / 'reports/term').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/term/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/term/tables.md')
