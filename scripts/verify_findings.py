#!/usr/bin/env python3
"""発見の台帳の数量の主張を、根拠表を介さずに元データから計算し直して確かめる (D35)。

使い方: python3 scripts/verify_findings.py
入力: analysis/classified.csv、data/raw/<区分>-<年度>.json、data/raw/gsdf/*.json、data/external/*.csv
各レポートのスクリプトとは別に書いた計算で、台帳 (reports/findings.csv) の主張の数を再現する。食い違えば FAIL を出して終了コード 1。
数は主張に書いた丸めのまま比べる (割合は整数の %、相関は小数 2 桁)。
"""
import collections
import csv
import glob
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
C = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in C:
    r['y'] = int(r['year'])
    r['m'] = int(r['recept_date'][5:7]) if r['recept_date'] else None
    r['mun'] = r['muni_codes'].split()
    r['bur'] = r['bureaus'].split()
results = []


def check(fid, label, got, want):
    ok = got == want
    results.append((fid, label, got, want, ok))


def p(n, d):
    return round(100 * n / d)


def yr(y):
    return [r for r in C if r['y'] == y]


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** .5


# F02・F04: 道の委託契約と上期の届出の比率
con = list(csv.DictReader((ROOT / 'data/external/hokkaido-pref-contracts-h1.csv').open()))
cc = lambda y, d, o=None: sum(int(x['contracts_h1']) for x in con if x['kind'] == '委託' and int(x['year']) == y and x['dept'] == d and (o is None or x['office'] == o))
KEN = '札幌|小樽|室蘭|函館|旭川|留萌|稚内|網走|帯広|釧路'


def dept_of(r):
    m = re.search(f'({KEN})建設管理部', r['charge_section'])
    if m:
        return ('建設管理部', m.group(1))
    m = re.match(r'北海道(.+?)(総合)?振興局$', r['planner'])
    return ('産業振興部', m.group(1)) if m else None


def sv(y, d, o=None):
    return sum(1 for r in yr(y) if r['planner_type'] == '北海道' and 4 <= (r['m'] or 0) <= 9
               and dept_of(r) and dept_of(r)[0] == d and (o is None or dept_of(r)[1] == o))


check('F02', '産業振興部の委託契約 R6', cc(2024, '産業振興部'), 847)
check('F02', '産業振興部の届出の比率 R5 (%)', p(sv(2023, '産業振興部'), cc(2023, '産業振興部')), 15)
check('F02', '産業振興部の届出の比率 R6 (%)', p(sv(2024, '産業振興部'), cc(2024, '産業振興部')), 33)
check('F04', '上川 産業振興部の比率 R3 → R4 (%)', (p(sv(2021, '産業振興部', '上川'), cc(2021, '産業振興部', '上川')), p(sv(2022, '産業振興部', '上川'), cc(2022, '産業振興部', '上川'))), (17, 10))
check('F04', '委託契約 上川 産業振興部・旭川建設管理部 R4', (cc(2022, '産業振興部', '上川'), cc(2022, '建設管理部', '旭川')), (123, 311))

# F06: 開発局の届出の増減と「当初 + 前年度の補正」の相関
ini = {int(x['year']): int(x['total']) / 100 for x in csv.DictReader((ROOT / 'data/external/hkd-budget-initial.csv').open()) if x['kind'] == 'direct'}
sup = collections.defaultdict(float)
for x in csv.DictReader((ROOT / 'data/external/hkd-budget-supplementary.csv').open()):
    if x['kind'] == 'supp':
        sup[int(x['year'])] += float(x['direct'])
ys = list(range(2010, 2026))
kai = [sum(1 for r in yr(y) if r['planner_type'] == '北海道開発局') for y in ys]
bud = [ini[y] + sup[y - 1] for y in ys]
d = lambda v: [v[i] - v[i - 1] for i in range(1, len(v))]
check('F06', '増減の相関 (当初 + 前年度の補正)', round(corr(d(bud), d(kai)), 2), 0.68)

# F08・F10・F11: 季節の形 (都道府県単位)


def pref_shape(years):
    g = collections.defaultdict(collections.Counter)
    for f in sorted(glob.glob(str(ROOT / 'data/raw/[A-J]-*.json'))):
        if int(pathlib.Path(f).stem[2:]) not in years:
            continue
        for it in json.loads(pathlib.Path(f).read_text())['items']:
            m = re.match(r'\d{4}/(\d{2})/', it['dateReceptYmd'] or '')
            pr = it.get('areaPref') or ''
            if m and pr and ',' not in pr:
                g[pr][int(m.group(1))] += 1
    return g


g = pref_shape((2023, 2024, 2025))
big = {k: v for k, v in g.items() if sum(v.values()) >= 100}
su = {k: p(sum(v[m] for m in (6, 7, 8)), sum(v.values())) for k, v in big.items()}
wi = {k: p(sum(v[m] for m in (1, 2, 3)), sum(v.values())) for k, v in big.items()}
oth = [k for k in big if k != '北海道']
check('F08', '北海道の 6〜8 月 (%)', su['北海道'], 63)
check('F08', '他の都府県の 6〜8 月の範囲 (%)', (min(su[k] for k in oth), max(su[k] for k in oth)), (15, 45))
check('F10', '北海道・秋田の 1〜3 月 (%)', (wi['北海道'], wi['秋田県']), (1, 3))
g9 = pref_shape((2009,))
s9 = {k: p(sum(v[m] for m in (6, 7, 8)), sum(v.values())) for k, v in g9.items() if sum(v.values()) >= 50}
check('F11', '平成21年度の北海道と新潟の 6〜8 月 (%)', (s9['北海道'], s9['新潟県']), (46, 50))

# F17: 終了日が 10 日・20 日・月末
import calendar  # noqa: E402
import subprocess  # noqa: E402
q = "SELECT term_to FROM 'data/surveys.parquet' WHERE year BETWEEN 2009 AND 2025 AND term_to IS NOT NULL"
ends = subprocess.run(['duckdb', '-csv', '-noheader', '-c', q], capture_output=True, text=True, cwd=ROOT).stdout.split()
hit, hit30 = 0, 0
for e in ends:
    yy, mm, dd = map(int, e.split('-'))
    last = calendar.monthrange(yy, mm)[1]
    if dd in (10, 20) or dd == last:
        hit += 1
    if dd in (10, 20, 30) or dd == last:
        hit30 += 1
check('F17', '終了日が 10 日・20 日・月末 / 30 日を足す (%)', (p(hit, len(ends)), p(hit30, len(ends))), (44, 52))

# F22・F20: 測量のない市町村、十勝の割合
act = [m['code'] for m in json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities'] if m['status'] == 'active']
zeros = {y: sum(1 for c in act if not any(c in r['mun'] for r in yr(y))) for y in range(2009, 2026)}
check('F22', '測量のない市町村の範囲', (min(zeros.values()), max(zeros.values())), (6, 28))
tz = [zeros[y] for y in range(2009, 2024)]
tt = [len(yr(y)) for y in range(2009, 2024)]
check('F22', '全体の件数との相関', round(corr(tz, tt), 2), -0.75)


def bshare(b, y):
    w = [r for r in yr(y) if r['mun']]
    return sum(1 for r in w if b in r['bur']) / len(w)


check('F20', '十勝の割合 H21〜23 → R3〜5 → R6〜7 (%、小数 1 桁)',
      tuple(round(100 * statistics.mean(bshare('十勝', y) for y in ys_), 1) for ys_ in ((2009, 2010, 2011), (2021, 2022, 2023), (2024, 2025))), (8.5, 14.1, 16.9))

# F23: 千人未満の 4 村
VIL = {'01470', '01404', '01562', '01485'}
pairs = [(r, c) for r in C if 2009 <= r['y'] <= 2025 for c in r['mun'] if c in VIL]
dk = sum(1 for r, c in pairs if r['planner_type'] in ('北海道', '北海道開発局', '法務局', '防衛省', '国 (その他)'))
check('F23', '4 村の関与件数と道・国の割合 (%)', (len(pairs), p(dk, len(pairs))), (95, 96))

# F24: 都市計画関係の年平均と市町村の割合
CITY = re.compile(r'都市計画|用途地域|立地適正')
cp = [r for r in C if 2009 <= r['y'] <= 2025 and (re.search('土地区画整理', r['purpose']) or (CITY.search(r['purpose']) and r['planner_type'] != '国 (その他)'))]
check('F24', '都市計画関係の年平均 (件、整数) と市町村の割合 (%)', (round(len(cp) / 17), p(sum(1 for r in cp if r['planner_type'] == '市町村'), len(cp))), (8, 88))

# F25: 帯広圏の都市計画図の更新の年度
MAPK = re.compile(r'撮影|図化|写測|修正測量|数値|写真地図|既成図')
obi = sorted({r['y'] for r in C if r['planner'] == '北海道帯広市' and CITY.search(r['purpose']) and MAPK.search(r['kinds'])})
check('F25', '帯広市の都市計画図の年度', tuple(obi), (1994, 2002, 2009, 2016))

# F28: 令和5年度の新しい型
r5 = [r for r in yr(2023) if r['planner_type'] == '北海道']
check('F28', '砂防メンテナンス・土砂洪水氾濫対策 (令和5年度、道)', (sum(1 for r in r5 if 'メンテナンス' in r['purpose'] and '砂防' in r['purpose']),
                                                     sum(1 for r in yr(2023) if re.search('土砂・?洪水氾濫', r['purpose']))), (26, 17))

# F31・F35・F49・F50・F47
check('F31', '開発局 H30 → R1', (sum(1 for r in yr(2018) if r['planner_type'] == '北海道開発局'), sum(1 for r in yr(2019) if r['planner_type'] == '北海道開発局')), (140, 237))
kf = lambda y, f: sum(1 for r in yr(y) if r['planner_type'] == '北海道開発局' and r['field'] in f)
check('F35', '開発局の農業 R5 → R7、道路・防災・公物 R6 → R7', (kf(2023, ('農業農村',)), kf(2025, ('農業農村',)), kf(2024, ('道路', '防災・治水', '公物管理')), kf(2025, ('道路', '防災・治水', '公物管理'))), (86, 117, 164, 121))
w30 = [r for r in yr(2018) if r['m'] in (1, 2, 3)]
check('F49', '平成30年度の冬の受付・うち胆振・平成29年度', (len(w30), sum(1 for r in w30 if '胆振' in r['bur']), sum(1 for r in yr(2017) if r['m'] in (1, 2, 3))), (23, 16, 6))
check('F50', '道の農業農村 H29 → H30', tuple(sum(1 for r in yr(y) if r['planner_type'] == '北海道' and r['field'] == '農業農村') for y in (2017, 2018)), (118, 156))
tk = lambda y: sum(1 for r in yr(y) if '十勝' in r['bur'] and r['planner_type'] == '北海道' and r['field'] == '防災・治水')
check('F54', '十勝の道の防災・治水 H28 → H29', (tk(2016), tk(2017)), (9, 45))
rd = lambda y, t: sum(1 for r in yr(y) if r['field'] == '道路' and r['planner_type'] == t)
check('F55', '道路の測量 道・開発局・市町村 H28 → H29', tuple((rd(2016, t), rd(2017, t)) for t in ('北海道', '北海道開発局', '市町村')), ((62, 46), (45, 29), (29, 24)))
a7 = collections.Counter(r['aim'] for r in yr(2025))
check('F47', '令和7年度の公共事業執行・防災減災', (a7['公共事業執行'], a7['防災減災']), (128, 134))

# F41・F42: 地理情報隊と地方防衛局
gs = json.loads((ROOT / 'data/raw/gsdf/planner-search.json').read_text())['items']
gt = [i for i in gs if '情報隊' in (i['plannerName'] or '')]
check('F41', '地理情報隊 (中央情報隊を含む) の件数と最初の受付年度', (len(gt), min(i['yearRecept'] for i in gt)), (14, 2023))
db = [i for i in json.loads((ROOT / 'data/raw/gsdf/defense-bureau-search.json').read_text())['items'] if not (i['plannerName'] or '').startswith('国土地理院')]
check('F42', '地方防衛局の件数と直営', (len(db), sum(1 for i in db if '直営' in (i['workerName'] or ''))), (520, 0))

bad = [x for x in results if not x[4]]
for fid, label, got, want, ok in results:
    print(f'{"OK  " if ok else "FAIL"} {fid} {label}: {got}' + ('' if ok else f' (主張は {want})'))
print(f'{len(results) - len(bad)} / {len(results)} 件が主張どおり')
sys.exit(1 if bad else 0)
