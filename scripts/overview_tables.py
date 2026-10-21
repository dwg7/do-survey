#!/usr/bin/env python3
"""長期概況 (平成21〜令和7年度) の根拠表と出来事の表 (D39)。

使い方: python3 scripts/overview_tables.py   → reports/overview/tables.md
入力: analysis/classified.csv、reports/overview/events.csv (年度ごとの概況の予想外の仕分け。人が書く)
- 予想外 (平年からも傾向からも外れた指標、D20) を annual_overview.py と同じ物差しで計算し直し、events.csv の行とちょうど一致するかを確かめる。
  仕分けのない予想外や、予想外でない行があれば止まる (年度ごとの概況の根拠表 Y1 と同じ集合)。
- 平年に平成20年度以前が入る平成21〜25年度は、後の 5 年度との z も出す (D38)。
"""
import collections
import csv
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / 'scripts/annual_overview.py').read_text()
ns = {'__file__': str(ROOT / 'scripts/annual_overview.py'), '__name__': 'borrowed'}
exec(src.split("out = ['# 単年度の概況")[0], ns)
IND, normal, z, zt, level, THR, by_year, BUREAUS, active, sampling_sd = (ns[k] for k in (
    'IND', 'normal', 'z', 'zt', 'level', 'THR', 'by_year', 'BUREAUS', 'active', 'sampling_sd'))
YEARS = list(range(2009, 2026))
GROUPS = [('件数', ['件数'], 1), ('発注', ['発注:北海道', '発注:北海道開発局', '発注:市町村'], 3),
          ('分野', [f'分野:{f}' for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤')], 6),
          ('地域', [f'地域:{b}' for b in BUREAUS], 14),
          ('時期', ['上期の割合'], 1), ('広がり', ['測量のあった市町村', '上位10市町村の割合', '複数市町村の測量'], 1)]


def short(y):
    return ('R1' if y == 2019 else f'R{y - 2018}') if y >= 2019 else f'H{y - 1988}'


def pct(v):
    return f'{100 * v:.0f}%'


def fmt(key, v):
    return f'{v:.0f}' if key in ('件数', '測量のあった市町村') else pct(v)


def z_after(y, key):
    vals = [IND[x][key] for x in range(y + 1, y + 6)]
    m = statistics.mean(vals)
    return (IND[y][key] - m) / max(statistics.stdev(vals), sampling_sd(y, key, m))


# ---- 予想外の計算と events.csv の照合 ----
sur = {}
for y in YEARS:
    for g, keys, k in GROUPS:
        for key in keys:
            lv = level(z(y, key), zt(y, key), k)
            if lv >= 2:
                sur[(y, key)] = lv
ev = list(csv.DictReader((ROOT / 'reports/overview/events.csv').open()))
evk = {(int(e['year']), e['indicator']): e for e in ev}
missing = sorted(set(sur) - set(evk))
extra = sorted(set(evk) - set(sur))
if missing or extra or len(evk) != len(ev):
    print('events.csv が予想外の集合と一致しない', '仕分けのない予想外:', missing, '予想外でない行:', extra, file=sys.stderr)
    sys.exit(1)
KINDS = ['出来事', 'レンズ', '物差し・構成', '不明']
assert all(e['kind'] in KINDS for e in ev), '種類は 出来事・レンズ・物差し・構成・不明 のどれか'
for e in ev:
    assert (ROOT / f'reports/yearly/{e["ref"]}/summary.md').exists(), e['ref']

LV = {2: '予想外', 3: 'かなり予想外'}
out = ['# 長期概況 (平成21〜令和7年度) — 根拠表\n',
       '`scripts/overview_tables.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) を dwg7 が編集・加工。'
       '予想外の物差しは年度ごとの概況と同じ (平年 = 前 5 年度、傾向 = 前 5 年度の直線、群ごとのしきい値、D20)。'
       '仕分け (種類・細目・原因) は `reports/overview/events.csv` (年度ごとの概況の Y1 から写したもの) で、予想外の集合と一致することを生成のたびに確かめる。\n']

# O1 出来事の表
out.append('## O1. 出来事の表 — 17 年度の予想外と仕分け\n')
out.append('| 年度 | 指標 | 今年 | 平年 | z (平年) | z (短期傾向) | z (後の 5 年度) | 段階 | 種類 | 細目 | 中身 | 概況 |')
out.append('|---|---|---:|---:|---:|---:|---:|---|---|---|---|---|')
for y in YEARS:
    keys = [key for g, ks, k in GROUPS for key in ks if (y, key) in sur]
    if not keys:
        out.append(f'| {short(y)} | (予想外なし) | | | | | | | | | | [{short(y).lower()}](../yearly/{"r0" + str(y - 2018) if y >= 2019 else short(y).lower()}/summary.md) |')
        continue
    for key in keys:
        e = evk[(y, key)]
        m, _ = normal(y, key)
        za = f'{z_after(y, key):+.1f}' if y <= 2020 else ''
        out.append(f'| {short(y)} | {key} | {fmt(key, IND[y][key])} | {fmt(key, m)} | {z(y, key):+.1f} | {zt(y, key):+.1f} | {za} | {LV[sur[(y, key)]]} | '
                   f'{e["kind"]} | {e["sub"]} | {e["cause"]} | [{e["ref"]}](../yearly/{e["ref"]}/summary.md) |')

# O2 種類の集計
out.append('\n## O2. 種類と細目の集計\n')
kc = collections.Counter(e['kind'] for e in ev)
out.append('| 種類 | 予想外の数 | 割合 | 年度 |')
out.append('|---|---:|---:|---|')
for k in KINDS:
    ys = sorted({int(e['year']) for e in ev if e['kind'] == k})
    out.append(f'| {k} | {kc[k]} | {pct(kc[k] / len(ev))} | ' + '・'.join(short(y) for y in ys) + ' |')
out.append(f'| 計 | {len(ev)} | | |')
out.append('\n| 種類 | 細目 | 予想外の数 | 年度 |')
out.append('|---|---|---:|---|')
sc = collections.Counter((e['kind'], e['sub']) for e in ev)
for (k, s_), n in sorted(sc.items(), key=lambda kv: (KINDS.index(kv[0][0]), -kv[1], kv[0][1])):
    ys = sorted({int(e['year']) for e in ev if e['kind'] == k and e['sub'] == s_})
    out.append(f'| {k} | {s_} | {n} | ' + '・'.join(short(y) for y in ys) + ' |')

# O3 年度ごとの数と主な種類
out.append('\n## O3. 年度ごとの予想外の数と種類\n')
out.append('| 年度 | 予想外 | 出来事 | レンズ | 物差し・構成 | 不明 | 出来事の細目 |')
out.append('|---|---:|---:|---:|---:|---:|---|')
for y in YEARS:
    es = [e for e in ev if int(e['year']) == y]
    c = collections.Counter(e['kind'] for e in es)
    subs = '・'.join(dict.fromkeys(e['sub'] for e in es if e['kind'] == '出来事'))
    out.append(f'| {short(y)} | {len(es)} | ' + ' | '.join(str(c[k]) for k in KINDS) + f' | {subs} |')
periods = [('H21〜H25 (平年に平成20年度以前が入る)', range(2009, 2014)), ('H26〜R5', range(2014, 2024)), ('R6〜R7 (道の届出の段差の後)', range(2024, 2026))]
out.append('\n| 期間 | 年度の数 | 予想外 | 1 年度あたり | 出来事 | レンズ | 物差し・構成 | 不明 |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|')
for lab, ys in periods:
    es = [e for e in ev if int(e['year']) in ys]
    c = collections.Counter(e['kind'] for e in es)
    out.append(f'| {lab} | {len(ys)} | {len(es)} | {len(es) / len(ys):.1f} | ' + ' | '.join(str(c[k]) for k in KINDS) + ' |')
nz = [y for y in YEARS if not any(int(e['year']) == y for e in ev)]
out.append(f'\n予想外のない年度: {"・".join(short(y) for y in nz)}。')

# O4 長期構造の系列
out.append('\n## O4. 長期構造の系列 (年度ごと)\n')


def mshare(y, ms):
    rs = [r for r in by_year[y] if r['recept_date']]
    return sum(1 for r in rs if int(r['recept_date'][5:7]) in ms) / len(rs)


FL = ['農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤']
out.append('| 年度 | 件数 | 道 | 開発局 | 市町村 | 農業農村 | 道路 | 防災・治水 | 最大の分野 | 上期 | 6〜8 月 | 7 月 | 最多の月 | 冬 (1〜3 月) | 冬の件数 | 測量のない市町村 | 航空レーザ |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|')
for y in YEARS:
    rs = by_year[y]
    fc = collections.Counter(r['field'] for r in rs if r['field'] in FL)
    mc = collections.Counter(int(r['recept_date'][5:7]) for r in rs if r['recept_date'])
    win = sum(mc[m] for m in (1, 2, 3))
    zero = sum(1 for c in active if not any(c in r['ml'] for r in rs))
    out.append(f'| {short(y)} | {len(rs)} | {pct(IND[y]["発注:北海道"])} | {pct(IND[y]["発注:北海道開発局"])} | {pct(IND[y]["発注:市町村"])} | '
               f'{pct(IND[y]["分野:農業農村"])} | {pct(IND[y]["分野:道路"])} | {pct(IND[y]["分野:防災・治水"])} | {fc.most_common(1)[0][0]} | '
               f'{pct(IND[y]["上期の割合"])} | {pct(mshare(y, (6, 7, 8)))} | {pct(mshare(y, (7,)))} | {max(mc, key=lambda m: (mc[m], -m))} 月 | '
               f'{pct(win / sum(mc.values()))} | {win} | {zero} | {sum(1 for r in rs if "航空レーザ" in r["kinds"])} |')

# O5 期間の平均
out.append('\n## O5. 期間ごとの平均\n')
P2 = [('H21〜H23 (業務名が決まり文句)', range(2009, 2012)), ('H24〜H30', range(2012, 2019)), ('R1〜R5', range(2019, 2024)), ('R6〜R7 (届出の段差の後)', range(2024, 2026))]
out.append('| 期間 | 件数 | 道の件数 | 開発局の件数 | 市町村の件数 | 道 | 開発局 | 市町村 | 農業農村 | 道路 | 防災・治水 | 上期 | 6〜8 月 | 7 月 | 冬 (1〜3 月) | 測量のない市町村 |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for lab, ys in P2:
    mean = lambda f: statistics.mean(f(y) for y in ys)
    pc = lambda t: f'{mean(lambda y: sum(1 for r in by_year[y] if r["planner_type"] == t)):.0f}'
    out.append(f'| {lab} | {mean(lambda y: len(by_year[y])):.0f} | {pc("北海道")} | {pc("北海道開発局")} | {pc("市町村")} | ' + ' | '.join(pct(mean(lambda y: IND[y][k])) for k in (
        '発注:北海道', '発注:北海道開発局', '発注:市町村', '分野:農業農村', '分野:道路', '分野:防災・治水', '上期の割合'))
        + f' | {pct(mean(lambda y: mshare(y, (6, 7, 8))))} | {pct(mean(lambda y: mshare(y, (7,))))} | {pct(mean(lambda y: mshare(y, (1, 2, 3))))} | '
        f'{mean(lambda y: sum(1 for c in active if not any(c in r["ml"] for r in by_year[y]))):.0f} |')

# O6 長期構造の文が成り立つ年度
out.append('\n## O6. 長期構造の文が成り立つ年度\n')
TESTS = [('6〜8 月が 45% を超える (他の都府県の令和5〜7年度の最大)', lambda y: mshare(y, (6, 7, 8)) > 0.45),
         ('7 月が 20% 以上', lambda y: mshare(y, (7,)) >= 0.20),
         ('冬 (1〜3 月) が 3% 以下', lambda y: mshare(y, (1, 2, 3)) <= 0.03),
         ('農業農村が件数で最大の分野', lambda y: collections.Counter(r['field'] for r in by_year[y] if r['field'] in FL).most_common(1)[0][0] == '農業農村'),
         ('道と開発局で 85% 以上', lambda y: IND[y]['発注:北海道'] + IND[y]['発注:北海道開発局'] >= 0.85)]
out.append('| 長期構造の文 | 成り立つ年度の数 | 成り立つ年度 | 成り立たない年度 |')
out.append('|---|---:|---|---|')
for lab, f in TESTS:
    ok = [y for y in YEARS if f(y)]
    ng = [y for y in YEARS if not f(y)]
    out.append(f'| {lab} | {len(ok)} / {len(YEARS)} | ' + '・'.join(short(y) for y in ok) + ' | ' + ('・'.join(short(y) for y in ng) or 'なし') + ' |')
dk = [IND[y]['発注:北海道'] + IND[y]['発注:北海道開発局'] for y in YEARS]
out.append(f'\n道と開発局の割合の和: 17 年度で {pct(min(dk))}〜{pct(max(dk))} (平均 {pct(statistics.mean(dk))})。')
out.append('')

# O7〜O11: 測量と北海道の社会のつながり (D48)
ALLY = sorted(y for y in by_year if 1983 <= y <= 2025)   # 当年度 (途中) は除く
out.append('\n## O7. 段階の構成 (平成24〜令和7年度、業務名から段階が分かる時期)\n')
fr = [r for y in range(2012, 2026) for r in by_year[y]]
stc = collections.Counter(r['stage'] for r in fr)
known = sum(v for k, v in stc.items() if k != '不明')
out.append('| 段階 | 件数 | 割合 (不明を除く) |')
out.append('|---|---:|---:|')
for k, v in stc.most_common():
    out.append(f'| {k} | {v} | {pct(v / known) if k != "不明" else "—"} |')
out.append(f'| 計 | {len(fr)} | |')
out.append(f'\n計画と用地 (工事の前の段階) の和: 不明を除く {pct((stc["計画"] + stc["用地"]) / known)}。業務名に「除雪」がある測量 {sum(1 for r in fr if "除雪" in r["purpose"])} 件、「維持」{sum(1 for r in fr if "維持" in r["purpose"])} 件。\n')
out.append('## O8. 開発局の届出の多い年度 (昭和58〜令和7年度)\n')
kd = {y: sum(1 for r in by_year[y] if r['planner_type'] == '北海道開発局') for y in ALLY}
tot = {y: len(by_year[y]) for y in ALLY}
out.append('| 順位 | 年度 | 開発局の届出 | 全体の届出 |')
out.append('|---:|---|---:|---:|')
for i, (y, v) in enumerate(sorted(kd.items(), key=lambda kv: (-kv[1], kv[0]))[:5], 1):
    out.append(f'| {i} | {short(y)} ({y}) | {v} | {tot[y]} |')
ty, tv = max(tot.items(), key=lambda kv: (kv[1], kv[0]))
out.append(f'\n全体の届出の最多は {short(ty)} ({ty}) の {tv} 件。\n')
out.append('## O9. 航空レーザを含む測量の年平均\n')
las = {y: sum(1 for r in by_year[y] if '航空レーザ' in r['kinds']) for y in YEARS}
out.append(f'平成21〜30年度 {statistics.mean(las[y] for y in range(2009, 2019)):.1f} 件、令和元〜7年度 {statistics.mean(las[y] for y in range(2019, 2026)):.1f} 件。'
           f'最多は {short(max(las, key=lambda y: (las[y], y)))} の {max(las.values())} 件。\n')
out.append('## O10. 振興局ごとの分野の構成 (平成24〜令和5年度、令和6年度の届出の段差の前)\n')
F4 = ['農業農村', '道路', '防災・治水', '位置基盤']
out.append('| 振興局 | 関わった測量 | ' + ' | '.join(F4) + ' | 最大の分野 |')
out.append('|---|---:|' + '---:|' * len(F4) + '---|')
for b in BUREAUS:
    sb = [r for y in range(2012, 2024) for r in by_year[y] if b in r['bl']]
    fc = collections.Counter(r['field'] for r in sb)
    out.append(f'| {b} | {len(sb)} | ' + ' | '.join(pct(fc[f] / len(sb)) for f in F4) + f' | {fc.most_common(1)[0][0]} |')
out.append('\n## O11. 件数の多い市町村の常連 (平成21〜令和7年度の 17 年度)\n')
top1, top1t, top3t = collections.Counter(), collections.Counter(), collections.Counter()
for y in YEARS:
    c = collections.Counter(x for r in by_year[y] for x in r['ml'] if x in active)
    vals = sorted(c.values(), reverse=True)
    for x, v in c.items():
        if v == vals[0]:
            top1t[x] += 1
            if vals.count(vals[0]) == 1:
                top1[x] += 1
        if v >= vals[2]:
            top3t[x] += 1
popu = {r['code']: int(r['population']) for r in csv.DictReader((ROOT / 'data/external/hokkaido-population-2026.csv').open())}
out.append('| 市町村 | 人口 (2026-01-01) | 道内最多 (単独) の年度の数 | 道内最多 (同数を含む) | 上位 3 (同数を含む) の年度の数 |')
out.append('|---|---:|---:|---:|---:|')
for c_, v in sorted(top3t.items(), key=lambda kv: (-kv[1], kv[0]))[:8]:
    out.append(f'| {active[c_]["fullName"]} | {popu.get(c_, 0):,} | {top1[c_]} | {top1t[c_]} | {v} |')
out.append('\n同じ件数の年度は、同数の市町村をすべて数える (同数を含む)。人口は `data/external/hokkaido-population-2026.csv` (住民基本台帳、2026-01-01)。\n')

d = ROOT / 'reports/overview'
(d / 'tables.md').write_text('\n'.join(out) + '\n')
print(f'wrote {d / "tables.md"} (予想外 {len(sur)} 件、仕分け {len(ev)} 行が一致)')
