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
# F56〜F59: 平成26〜28年度の概況
dn = lambda y, st=None: sum(1 for r in yr(y) if r['planner_type'] == '北海道' and r['field'] == '農業農村' and (st is None or r['stage'] == st))
check('F56', '道の農業農村 H27 → H28 (うち計画)', ((dn(2015), dn(2016)), (dn(2015, '計画'), dn(2016, '計画'))), ((103, 166), (81, 146)))
check('F57', '件数と道の件数 H26 → H27', ((len(yr(2014)), len(yr(2015))), tuple(sum(1 for r in yr(y) if r['planner_type'] == '北海道') for y in (2014, 2015))), ((628, 523), (364, 288)))
up = lambda y, t: p(sum(1 for r in yr(y) if r['planner_type'] == t and r['m'] in (4, 5, 6, 7, 8, 9)), sum(1 for r in yr(y) if r['planner_type'] == t))
check('F58', '上期の割合 H25 → H26 (道・市町村・開発局、%)', tuple((up(2013, t), up(2014, t)) for t in ('北海道', '市町村', '北海道開発局')), ((71, 77), (71, 81), (61, 61)))
check('F59', '7 字未満の業務名 H25 → H26 と「道路計画」', (sum(1 for r in yr(2013) if len(r['purpose']) <= 6), sum(1 for r in yr(2014) if len(r['purpose']) <= 6),
                                                sum(1 for r in yr(2014) if r['purpose'].strip() == '道路計画')), (32, 73, 35))
# F60〜F67: 平成25〜21年度の概況 (D38)
m25 = [r for r in yr(2013) if r['planner_type'] == '市町村' and r['field'] == '位置基盤']
msh = lambda y: sum(1 for r in yr(y) if r['planner_type'] == '市町村') / len(yr(y))
check('F60', '平成25年度の市町村の位置基盤・うち成果の改正・市町村の割合・後の 5 年度の平均 (%)',
      (len(m25), sum(1 for r in m25 if '成果' in r['purpose']), round(100 * msh(2013)), round(100 * statistics.mean(msh(y) for y in range(2014, 2019)))), (18, 1, 14, 15))
bsh = lambda b, y, t=None: p(sum(1 for r in yr(y) if b in r['bur'] and (t is None or r['planner_type'] == t)), sum(1 for r in yr(y) if r['mun'] and (t is None or r['planner_type'] == t)))
check('F62', '十勝の割合 H24・H25 (%)', (bsh('十勝', 2012), bsh('十勝', 2013)), (13, 10))
w = lambda y, t: sum(1 for r in yr(y) if r['purpose'].strip() == t)
check('F64', '河川管理・道路管理 H22 → H23、道路の 3 語の合計', ((w(2010, '河川管理'), w(2011, '河川管理')), (w(2010, '道路管理'), w(2011, '道路管理')),
      tuple(sum(w(y, t) for t in ('道路計画', '道路用地', '道路管理')) for y in (2010, 2011))), ((20, 44), (11, 43), (171, 203)))
check('F65', '道の測量の中での空知の割合 H23 (%)', bsh('空知', 2011, '北海道'), 23)
kd = lambda y: sum(1 for r in yr(y) if r['planner_type'] == '北海道開発局')
check('F66', '開発局の届出 H21 → H22 と減り方 (%)', (kd(2009), kd(2010), round(100 * (kd(2009) - kd(2010)) / kd(2009))), (229, 71, 69))
hs = lambda y: p(sum(1 for r in yr(y) if r['m'] in (4, 5, 6, 7, 8, 9)), sum(1 for r in yr(y) if r['m']))
check('F67', '上期の割合 H16〜H20 の最小・最大と H21 (%)', (min(hs(y) for y in range(2004, 2009)), max(hs(y) for y in range(2004, 2009)), hs(2009)), (61, 63, 69))
# F69〜F71: 長期概況 (D39)
evs = list(csv.DictReader((ROOT / 'reports/overview/events.csv').open()))
ekc = collections.Counter(e['kind'] for e in evs)
mid = [e for e in evs if 2014 <= int(e['year']) <= 2023]
check('F69', '仕分けの数 (出来事・レンズ・物差し・構成・不明) と平成26〜令和5年度の出来事 / 予想外',
      (len(evs), ekc['出来事'], ekc['レンズ'], ekc['物差し・構成'], ekc['不明'], sum(1 for e in mid if e['kind'] == '出来事'), len(mid)), (48, 13, 13, 15, 7, 10, 22))
def mavg(ys, ms):
    return round(100 * statistics.mean(sum(1 for r in yr(y) if r['m'] in ms) / sum(1 for r in yr(y) if r['m']) for y in ys))
PER = (range(2009, 2012), range(2019, 2024), range(2024, 2026))
check('F70', '6〜8 月・7 月・上期・冬の期間平均 (%)', tuple(tuple(mavg(ys, ms) for ys in PER) for ms in ((6, 7, 8), (7,), (4, 5, 6, 7, 8, 9), (1, 2, 3))),
      ((44, 57, 65), (16, 24, 29), (67, 79, 86), (5, 1, 1)))
FL6 = ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤')
topf = lambda y: collections.Counter(r['field'] for r in yr(y) if r['field'] in FL6).most_common(1)[0][0]
check('F71', '最大の分野が道路の年度・農業農村の年度', (tuple(y for y in range(2009, 2026) if topf(y) == '道路'), min(y for y in range(2009, 2026) if topf(y) == '農業農村'),
      all(topf(y) == '農業農村' for y in range(2012, 2026))), ((2009, 2010, 2011), 2012, True))
# F54・F74・F75: 平成28年台風 10 号 (D42)
tkd = lambda y: [r for r in yr(y) if r['planner_type'] == '北海道' and '十勝' in r['bur']]
check('F54b', '被災 3 河川の名を含む道の測量 H29・十勝の道の防災のうち「災害」H29',
      (sum(1 for r in yr(2017) if r['planner_type'] == '北海道' and re.search('ペケレベツ|パンケ新得|芽室川', r['purpose'])),
       sum(1 for r in tkd(2017) if r['field'] == '防災・治水' and '災害' in r['purpose'])), (11, 5))
dk = lambda y, rs: sum(1 for r in rs if '道単' in r['purpose'] and '改修' in r['purpose'])
check('F74', '十勝の道単改修 H29・他の年度の最大・全道 H29', (dk(2017, tkd(2017)), max(dk(y, tkd(y)) for y in range(2009, 2026) if y != 2017),
      dk(2017, [r for r in yr(2017) if r['planner_type'] == '北海道'])), (36, 5, 41))
dz = [r for r in yr(2016) if re.search('被害調査|災害調査|災害設計|災害復旧|災害助成|災害関連|災害査定', r['purpose'])]
check('F75', 'H28 の災害の調査・設計の測量の数・8 月以前の数', (len(dz), sum(1 for r in dz if r['m'] in (4, 5, 6, 7, 8))), (9, 0))
# F76・F77: 1 つの事業と届出の分け方 (D44)。事業の名前の正規化は method_tables.py とは別に書く
bk = [r for r in C if '別海北部' in r['purpose'] and r['y'] <= 2025]
NUM = '0-9０-９一二三四五六七八九十'
def strip_no(p):
    p = re.sub(r'[（(](補正|明許|繰越|ゼロ債|ゼロ国債|債務|単独)[)）]', '', p.strip())
    for pat in (rf'その\s*[{NUM}]+', rf'第\s*[{NUM}]+\s*工区', rf'[{NUM}]+\s*工区', rf'[（(]\s*[{NUM}]+\s*[)）]', rf'[{NUM}]+\s*$'):
        p = re.sub(pat, '', p)
    return re.sub(r'[\s　・、,]', '', p)
check('F76', '別海北部地区の届出・年度の数・異なる業務名', (len(bk), len({r['y'] for r in bk}), len({strip_no(r['purpose']) for r in bk})), (136, 14, 104))
fr = [r for r in C if 2012 <= r['y'] <= 2025 and len(r['purpose'].strip()) > 6]
def ratio(rs):
    return round(len(rs) / len({(r['y'], r['planner'], strip_no(r['purpose'])) for r in rs}), 2)
kd2 = lambda f: [r for r in fr if r['planner_type'] == '北海道開発局' and r['field'] == f]
check('F77', '届出 / まとまり (全体・開発局の農業・道路)', (ratio(fr), ratio(kd2('農業農村')), ratio(kd2('道路'))), (1.10, 1.08, 1.07))
# F78〜F82: 測量と北海道の社会のつながり (D48)
fs = [r for r in C if 2012 <= r['y'] <= 2025]
kn = [r for r in fs if r['stage'] != '不明']
check('F78', '計画と用地の割合 (%)・除雪の件数・届出の数', (p(sum(1 for r in kn if r['stage'] in ('計画', '用地')), len(kn)), sum(1 for r in fs if '除雪' in r['purpose']), len(fs)), (86, 7, 9106))
kdy = {y: sum(1 for r in yr(y) if r['planner_type'] == '北海道開発局') for y in range(1983, 2026)}
t5 = sorted(kdy, key=lambda y: -kdy[y])[:5]
check('F79', '開発局の届出の上位 5 年度 (昇順) と最多', (tuple(sorted(t5)), max(kdy.values())), ((2021, 2022, 2023, 2024, 2025), 276))
lz = {y: sum(1 for r in yr(y) if '航空レーザ' in r['kinds']) for y in range(2009, 2026)}
check('F80', '航空レーザの年平均 (平成21〜30・令和元〜7) と最多', (round(statistics.mean(lz[y] for y in range(2009, 2019)), 1), round(statistics.mean(lz[y] for y in range(2019, 2026)), 1), max(lz.values())), (8.9, 22.4, 31))
bf = lambda b, f: p(sum(1 for r in C if 2012 <= r['y'] <= 2023 and b in r['bur'] and r['field'] == f), sum(1 for r in C if 2012 <= r['y'] <= 2023 and b in r['bur']))
check('F81', '空知・根室の農業農村の割合 (%)', (bf('空知', '農業農村'), bf('根室', '農業農村')), (63, 56))
mun = json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities']
actc = {m['code'] for m in mun if m['status'] == 'active'}
t1, t3 = collections.Counter(), collections.Counter()
for y in range(2009, 2026):
    cc = collections.Counter(c for r in yr(y) for c in r['mun'] if c in actc)
    vs = sorted(cc.values(), reverse=True)
    for c, v in cc.items():
        t1[c] += v == vs[0]
        t3[c] += v >= vs[2]
check('F82', '別海町の最多 (同数を含む)・上位 3、札幌市の上位 3', (t1['01691'], t3['01691'], t3['01100']), (6, 12, 7))
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
