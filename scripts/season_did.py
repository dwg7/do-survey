#!/usr/bin/env python3
"""受付の季節の形の分解: 北海道の夏の集中の強まりは全国一律か、北海道に固有か (D23)。

入力: data/raw/<区分>-<年度>.json (区分 A〜J、年度 2009・2014・2019・2023・2024・2025)
出力: reports/season/compare.md

差の差: (北海道の変化) − (他の 9 地方の変化の平均)。変化は平成21年度 (2009) → 令和5〜7年度 (2023〜2025 の合算)。
発注主体の区分は scripts/national_compare.py と同じ (計画機関名から県名を除いた残り)。
"""
import collections
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
src = (ROOT / 'scripts/national_compare.py').read_text()
ns = {'__file__': str(ROOT / 'scripts/national_compare.py')}
exec(src.split('arules = classify.load_rules')[0].replace('import classify  # noqa: E402', ''), ns)   # planner_kind を借りる
planner_kind = ns['planner_kind']
SECTIONS = ns['SECTIONS']
PERIODS = [('H21', (2009,)), ('H26', (2014,)), ('R1', (2019,)), ('R5-7', (2023, 2024, 2025))]

recs = collections.defaultdict(list)
for sec in SECTIONS:
    for _, ys in PERIODS:
        for y in ys:
            for it in json.loads((ROOT / f'data/raw/{sec}-{y}.json').read_text())['items']:
                m = re.match(r'\d{4}/(\d{2})/', it['dateReceptYmd'] or '')
                if m:
                    recs[(sec, y)].append((int(m.group(1)), planner_kind(it['plannerName'] or '')))


def stat(sec, ys, fn, kind=None):
    s = [r for y in ys for r in recs[(sec, y)] if kind is None or r[1] == kind]
    return (sum(1 for r in s if fn(r[0])) / len(s), len(s)) if s else (None, 0)


up = lambda m: 4 <= m <= 9
summer = lambda m: m in (6, 7, 8)
out = ['# 受付の季節の形の分解 — 地方の比較と差の差\n',
       '`scripts/season_did.py` が生成。国土地理院「公共測量実施情報」の地方測量部区分 A〜J。差の差 = 北海道の変化 − 他の 9 地方の変化の平均 '
       '(平成21年度 → 令和5〜7年度、ポイント)。\n']


def block(title, fn, kind=None):
    out.append(f'\n## {title}\n')
    out.append('| 地方 | ' + ' | '.join(p for p, _ in PERIODS) + ' | 変化 (H21 → R5-7) |')
    out.append('|---|' + '|'.join('---:' for _ in PERIODS) + '|---:|')
    ch = {}
    for sec, name in SECTIONS.items():
        vals = [stat(sec, ys, fn, kind) for _, ys in PERIODS]
        cells = [f'{100 * v:.0f}% ({n})' if v is not None else '—' for v, n in vals]
        if vals[0][0] is not None and vals[-1][0] is not None:
            ch[sec] = 100 * (vals[-1][0] - vals[0][0])
        out.append(f'| {name} | ' + ' | '.join(cells) + f' | {ch.get(sec, float("nan")):+.0f} |')
    others = [v for s, v in ch.items() if s != 'A']
    did = ch['A'] - statistics.mean(others)
    out.append(f'\n北海道の変化 {ch["A"]:+.0f} ポイント、他の 9 地方の変化の平均 {statistics.mean(others):+.0f} '
               f'(範囲 {min(others):+.0f}〜{max(others):+.0f})、**差の差 {did:+.0f}**。括弧は件数。\n')
    return ch['A'], statistics.mean(others), did


res = {}
res['上期 (全体)'] = block('上期 (4〜9 月) の受付の割合 — 全体', up)
res['6〜8 月 (全体)'] = block('6〜8 月の受付の割合 — 全体', summer)
for k in ('国', '都道府県', '市区町村'):
    res[f'上期 ({k})'] = block(f'上期の受付の割合 — 発注: {k}', up, k)

out.append('\n## まとめ\n')
out.append('| 指標 | 北海道の変化 | 他の 9 地方の平均の変化 | 差の差 |')
out.append('|---|---:|---:|---:|')
for k, (a, o, d) in res.items():
    out.append(f'| {k} | {a:+.0f} | {o:+.0f} | {d:+.0f} |')
out.append('')
(ROOT / 'reports/season').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/season/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/season/compare.md')
