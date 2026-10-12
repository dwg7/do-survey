#!/usr/bin/env python3
"""年度ごとの北海道測量概況 (新しい型) の根拠表 (D32)。

使い方: python3 scripts/yearly_tables.py <受付年度>   → reports/yearly/<r07 など>/tables.md

型 (reports/yearly/README.md):
  Y1 今年の天気 — 指標ごとの平年・傾向との比較と、情報の段階 (annual_overview.py と同じ物差し)
  Y2 予算と契約 — 開発局の当初 + 前年度の補正と開発局の届出、道の当初予算、道の委託契約と届出の比率 (D19・D25・D26)
  Y3 地勢の確認 — 季節の形 (7 月への集中・冬の空白)、農業の割合、発注主体。他の地方の都道府県と比べられる年度は比べる (D21・D28)
  Y4 地域と市町村 — 振興局、上位の市町村、測量のない市町村 (前年度も空白か)、千人未満の 4 村 (D27・D29)
  Y5 テーマの定点 — 都市計画図・固定資産の航空写真 (D30)、航空写真・航空レーザ、新しい計画機関、件数の多い業務名
  Y6 レンズの注意 — 業務名の記述、担当部署・実施地域図の有無、届出の段差 (D25)
入力: analysis/classified.csv、data/external/*.csv、data/raw/<区分>-<年度>.json (他の地方、ある年度だけ)
"""
import collections
import csv
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
Y = int(sys.argv[1]) if len(sys.argv) > 1 else 2025

# annual_overview.py の指標と物差し (平年・傾向・しきい値) を借りる。ファイルを書く部分の手前まで実行する。
src = (ROOT / 'scripts/annual_overview.py').read_text()
ns = {'__file__': str(ROOT / 'scripts/annual_overview.py'), '__name__': 'borrowed'}
exec(src.split("out = ['# 単年度の概況")[0], ns)
IND, normal, trend, z, zt, level, THR, by_year, BUREAUS, era = (ns[k] for k in (
    'IND', 'normal', 'trend', 'z', 'zt', 'level', 'THR', 'by_year', 'BUREAUS', 'era'))
active = ns['active']
rows = by_year[Y]
N = len(rows)


def short(y):
    if y >= 2019:
        return 'R1' if y == 2019 else f'R{y - 2018}'
    return f'H{y - 1988}'


def pct(v):
    return f'{100 * v:.0f}%'


LEVEL = {0: '平年並み', 1: '平年と違うが傾向どおり', 2: '**予想外**', 3: '**かなり予想外**'}
out = [f'# {era(Y)} 北海道測量概況 — 根拠表\n',
       f'`scripts/yearly_tables.py {Y}` が生成。国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) ほかを dwg7 が編集・加工。'
       f'受付年度 {Y} (令和/平成の年度は 4 月〜翌 3 月)。平年 = 前 5 年度 ({short(Y - 5)}〜{short(Y - 1)}) の平均、傾向 = 前 5 年度の直線の延長。'
       '比べる指標が k 個ある群 (発注 3、分野 6、地域 14) は、k 個の最大が偶然超える確率が 32% / 5% になるしきい値で段階を決める (D20)。\n']

# ---- Y1 今年の天気 ----
GROUPS = [('件数', ['件数'], 1), ('発注', ['発注:北海道', '発注:北海道開発局', '発注:市町村'], 3),
          ('分野', [f'分野:{f}' for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤')], 6),
          ('地域', [f'地域:{b}' for b in BUREAUS], 14),
          ('時期', ['上期の割合'], 1), ('広がり', ['測量のあった市町村', '上位10市町村の割合', '複数市町村の測量'], 1)]
out.append('## Y1. 今年の天気 — 指標ごとの平年・傾向との比較\n')
out.append('| 群 | 指標 | 今年 | 平年 | z (平年) | 傾向の予測 | z (傾向) | 段階 |')
out.append('|---|---|---:|---:|---:|---:|---:|---|')
surprises = []
for g, keys, k in GROUPS:
    for key in keys:
        v = IND[Y][key]
        m, _ = normal(Y, key)
        p, _ = trend(Y, key)
        zn, ztr = z(Y, key), zt(Y, key)
        lv = level(zn, ztr, k)
        f = (lambda x: f'{x:.0f}') if key in ('件数', '測量のあった市町村') else pct
        out.append(f'| {g} | {key} | {f(v)} | {f(m)} | {zn:+.1f} | {f(p)} | {ztr:+.1f} | {LEVEL[lv]} |')
        if lv >= 2:
            surprises.append((key, zn, ztr, lv))
out.append(f'\nしきい値 (k = 1 / 3 / 6 / 14): ' + '、'.join(f'k={k} {t1}・{t2}' for k, (t1, t2) in THR.items()) + '。'
           f'予想外 = 平年からも傾向からも外れる。予想外の指標: ' + ('、'.join(s[0] for s in surprises) or 'なし') + '。\n')

# ---- Y2 予算と契約 ----
out.append('## Y2. 予算と契約\n')
ini = {int(r['year']): int(r['total']) / 100 for r in csv.DictReader((ROOT / 'data/external/hkd-budget-initial.csv').open()) if r['kind'] == 'direct'}
sup, zero = collections.defaultdict(float), collections.defaultdict(float)
for r in csv.DictReader((ROOT / 'data/external/hkd-budget-supplementary.csv').open()):
    (sup if r['kind'] == 'supp' else zero)[int(r['year'])] += float(r['direct'])
kai = collections.Counter(r['year'] for yy in range(Y - 5, Y + 1) for r in by_year[yy] if r['planner_type'] == '北海道開発局')
out.append('**開発局 (直轄、億円) と開発局の届出** (D26: 増減は「当初 + 前年度の補正」と最もよく合う)\n')
out.append('| 年度 | 当初 | 前年度の補正 | 当初 + 前年度の補正 | 当該年度の補正 | ゼロ国債 | 開発局の届出 |')
out.append('|---|---:|---:|---:|---:|---:|---:|')
for yy in range(Y - 5, Y + 1):
    if yy in ini:
        out.append(f'| {short(yy)} | {ini[yy]:,.0f} | {sup[yy - 1]:,.0f} | {ini[yy] + sup[yy - 1]:,.0f} | {sup[yy]:,.0f} | {zero[yy]:,.0f} | {kai[yy]} |')
pb = {int(r['year']): r for r in csv.DictReader((ROOT / 'data/external/hokkaido-pref-budget-initial.csv').open())}
dou = collections.Counter(r['year'] for yy in range(Y - 5, Y + 1) for r in by_year[yy] if r['planner_type'] == '北海道')
out.append('\n**道 (当初予算の公共事業 補助事業費等、億円) と道の届出** (D25: 道の届出は予算の転換を写さない)\n')
out.append('| 年度 | 補助事業費等 | 投資的経費の計 | 道の届出 |')
out.append('|---|---:|---:|---:|')
for yy in range(Y - 5, Y + 1):
    b = pb.get(yy)
    out.append(f'| {short(yy)} | {int(b["public_subsidy"]):,} | {int(b["investment_total"]):,} | {dou[yy]} |' if b
               else f'| {short(yy)} | — | — | {dou[yy]} |')
out.append('\n道の当初予算の内訳は平成24〜令和4年度だけ (令和4年度「予算のポイント」のグラフ。令和7年度の資料は画像で内訳がない)。\n')
con = list(csv.DictReader((ROOT / 'data/external/hokkaido-pref-contracts-h1.csv').open()))
cy = sorted({int(x['year']) for x in con})
if Y in cy:
    KEN = ['札幌', '小樽', '室蘭', '函館', '旭川', '留萌', '稚内', '網走', '帯広', '釧路']

    def dept(r):
        if re.search('(' + '|'.join(KEN) + ')建設管理部', r['charge_section']):
            return '建設管理部'
        return '産業振興部' if re.match(r'北海道.+?(総合)?振興局$', r['planner']) else None
    out.append('\n**道の委託契約 (上半期) と道の上期の届出** (D25)\n')
    out.append('| 年度 | 部 | 委託契約 | 上期の届出 | 届出の比率 |')
    out.append('|---|---|---:|---:|---:|')
    for yy in [x for x in cy if Y - 2 <= x <= Y]:
        for d in ('産業振興部', '建設管理部'):
            c = sum(int(x['contracts_h1']) for x in con if x['kind'] == '委託' and x['dept'] == d and int(x['year']) == yy)
            s = sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and r['half'] == '上期' and dept(r) == d)
            out.append(f'| {short(yy)} | {d} | {c} | {s} | {pct(s / c)} |')
else:
    out.append(f'\n道の委託契約の資料は {short(cy[0])}〜{short(cy[-1])} だけで、この年度はない。\n')

# ---- Y3 地勢の確認 ----
out.append('\n## Y3. 地勢の確認\n')
mc = collections.Counter(int(r['recept_date'][5:7]) for r in rows if r['recept_date'])
mt = sum(mc.values())
sh = lambda ms: sum(mc[m] for m in ms) / mt
fc = collections.Counter(r['field'] for r in rows)
pc = collections.Counter(r['planner_type'] for r in rows)
out.append('| 地勢の文 | 今年 | 判定の目安 |')
out.append('|---|---:|---|')
out.append(f'| 6〜8 月への集中 (北海道に固有、D28) | {pct(sh((6, 7, 8)))} (7 月 {pct(mc[7] / mt)}) | 他の都府県は 15〜45% (令和5〜7年度) |')
out.append(f'| 冬 (1〜3 月) の空白 (雪国に共通、D28) | {pct(sh((1, 2, 3)))} | 雪国の県は 8% 以下 |')
out.append(f'| 最多の受付月 | {mc.most_common(1)[0][0]} 月 | 北海道は 6〜7 月、雪国の他の県は 9〜10 月 |')
out.append(f'| 農業農村が件数で最大 (農村型の地方に共通、D21) | {fc.most_common(1)[0][0]} {pct(fc.most_common(1)[0][1] / N)} | |')
out.append(f'| 発注は道と国で 9 割 (D21) | 道 {pct(pc["北海道"] / N)}・開発局 {pct(pc["北海道開発局"] / N)}・市町村 {pct(pc["市町村"] / N)} | 市町村の発注は 10 地方で最少 |')
out.append('\n**月別の受付**\n')
out.append('| ' + ' | '.join(f'{m} 月' for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)) + ' |')
out.append('|' + '---:|' * 12)
out.append('| ' + ' | '.join(pct(mc[m] / mt) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)) + ' |')
SECS = 'BCDEFGHIJ'
if all((ROOT / f'data/raw/{s}-{Y}.json').exists() for s in SECS):
    g = collections.defaultdict(collections.Counter)
    for s in SECS:
        for it in json.loads((ROOT / f'data/raw/{s}-{Y}.json').read_text())['items']:
            m = re.match(r'\d{4}/(\d{2})/', it['dateReceptYmd'] or '')
            pref = it.get('areaPref') or ''
            if m and pref and ',' not in pref:
                g[pref][int(m.group(1))] += 1
    ss = {p: (sum(c[m] for m in (6, 7, 8)) / sum(c.values()), sum(c[m] for m in (1, 2, 3)) / sum(c.values()), sum(c.values()))
          for p, c in g.items() if sum(c.values()) >= 50}
    top3 = sorted(ss, key=lambda p: -ss[p][0])[:3]
    low3 = sorted(ss, key=lambda p: ss[p][1])[:3]
    out.append(f'\n**他の地方の都府県との比較 ({short(Y)}、件数 50 件以上の {len(ss)} 都府県)**: 6〜8 月の割合の上位 '
               + '、'.join(f'{p} {pct(ss[p][0])}' for p in top3) + '。1〜3 月の割合の下位 '
               + '、'.join(f'{p} {pct(ss[p][1])}' for p in low3) + '。\n')
else:
    out.append(f'\n他の地方のデータはこの年度は取得していない (取得済みは平成21・26年度、令和元・5〜7年度)。\n')

# ---- Y4 地域と市町村 ----
out.append('\n## Y4. 地域と市町村\n')
bc = collections.Counter(b for r in rows for b in r['bl'])
out.append('| 振興局 | 件数 | 割合 | 平年の割合 | z (平年) | z (傾向) | 段階 |')
out.append('|---|---:|---:|---:|---:|---:|---|')
for b in sorted(BUREAUS, key=lambda b: -bc[b]):
    key = f'地域:{b}'
    m, _ = normal(Y, key)
    out.append(f'| {b} | {bc[b]} | {pct(IND[Y][key])} | {pct(m)} | {z(Y, key):+.1f} | {zt(Y, key):+.1f} | {LEVEL[level(z(Y, key), zt(Y, key), 14)]} |')
mcnt = collections.Counter(c for r in rows for c in r['ml'] if c in active)
prev = collections.Counter(c for r in by_year[Y - 1] for c in r['ml'] if c in active)
out.append('\n**件数の多い市町村 (上位 10)**: ' + '、'.join(f'{active[c]["fullName"]} {n}' for c, n in mcnt.most_common(10)) + '\n')
zeros = sorted([c for c in active if mcnt[c] == 0], key=lambda c: (active[c]['bureau'], c))
out.append(f'**測量のない市町村 ({len(zeros)})**: ' + '、'.join(active[c]['fullName'] + ('*' if prev[c] == 0 else '') for c in zeros)
           + '。* は前年度も測量がなかった市町村。\n')
VIL = ['01470', '01404', '01562', '01485']   # 音威子府・神恵内・西興部・初山別
names = {c: active[c]['fullName'] for c in VIL if c in active}
out.append('**千人未満の 4 村 (D29)**: ' + '、'.join(
    f'{names[c]} {mcnt[c]} 件 (道 {sum(1 for r in rows if c in r["ml"] and r["planner_type"] == "北海道")}・'
    f'開発局 {sum(1 for r in rows if c in r["ml"] and r["planner_type"] == "北海道開発局")}・'
    f'村 {sum(1 for r in rows if c in r["ml"] and r["planner_type"] == "市町村" and names[c] in r["planner"])})' for c in VIL if c in names) + '\n')

# ---- Y5 テーマの定点 ----
out.append('\n## Y5. テーマの定点\n')
CITY = re.compile(r'都市計画|用途地域|立地適正')
MAPK = re.compile(r'撮影|図化|写測|修正測量|数値|写真地図|既成図')
TAX = re.compile(r'固定資産|家屋|課税|マッピング')
cityp = [r for r in rows if CITY.search(r['purpose']) and MAPK.search(r['kinds']) and r['planner_type'] != '国 (その他)']
tax = [r for r in rows if r['planner_type'] == '市町村' and TAX.search(r['purpose']) and MAPK.search(r['kinds'])]
out.append(f'- **都市計画図の作成・更新 ({len(cityp)} 件、D30 の周期は 7〜8 年)**: ' + ('、'.join(sorted({r['planner'].replace('北海道', '', 1) for r in cityp})) or 'なし'))
out.append(f'- **固定資産・家屋の航空写真 ({len(tax)} 件、3 年周期)**: ' + ('、'.join(sorted({r['planner'].replace('北海道', '', 1) for r in tax})) or 'なし'))
aer = sum(1 for r in rows if re.search(r'撮影|写真地図|写測', r['kinds']))
las = sum(1 for r in rows if '航空レーザ' in r['kinds'])
aer_m = statistics.mean(sum(1 for r in by_year[yy] if re.search(r'撮影|写真地図|写測', r['kinds'])) for yy in range(Y - 5, Y))
las_m = statistics.mean(sum(1 for r in by_year[yy] if '航空レーザ' in r['kinds']) for yy in range(Y - 5, Y))
out.append(f'- **航空写真を含む測量** {aer} 件 (平年 {aer_m:.0f})、**航空レーザ** {las} 件 (平年 {las_m:.0f})')
prevp = {r['planner'] for yy in range(Y - 5, Y) for r in by_year[yy]}
new = collections.Counter(r['planner'] for r in rows if r['planner'] not in prevp)
out.append('- **前 5 年度に登録のなかった計画機関**: ' + ('、'.join(f'{p} {n}' for p, n in new.most_common(8)) or 'なし'))
pp = collections.Counter(re.sub(r'[\s　]+', ' ', r['purpose'])[:24] for r in rows if len(r['purpose']) > 6)
out.append('- **件数の多い業務名 (先頭 24 字、自由記述のもの)**: ' + '、'.join(f'{p} ({n})' for p, n in pp.most_common(8) if n >= 2))

# ---- Y6 レンズの注意 ----
out.append('\n## Y6. レンズの注意\n')
free = sum(1 for r in rows if len(r['purpose']) > 6)
sec = sum(1 for r in rows if r['charge_section'].strip())
area = sum(1 for r in rows if r['area_km2'])
out.append('| 項目 | 今年 | 前年度 |')
out.append('|---|---:|---:|')
pr = by_year[Y - 1]
out.append(f'| 業務名が自由記述 (7 字以上) の割合 | {pct(free / N)} | {pct(sum(1 for r in pr if len(r["purpose"]) > 6) / len(pr))} |')
out.append(f'| 担当部署の記載がある割合 | {pct(sec / N)} | {pct(sum(1 for r in pr if r["charge_section"].strip()) / len(pr))} |')
out.append(f'| 実施地域図 (面積) がある割合 | {pct(area / N)} | {pct(sum(1 for r in pr if r["area_km2"]) / len(pr))} |')
out.append(f'| 分野が「不明」の割合 | {pct(fc["不明"] / N)} | {pct(sum(1 for r in pr if r["field"] == "不明") / len(pr))} |')
notes = []
if Y >= 2024:
    notes.append('令和6年度以降は道の農業農村整備の届出が段差で増えた後 (届出の比率 15% → 33%、D25)。令和5年度以前と農業の件数を比べる時は段差を差し引く。')
if Y == 2025:
    notes.append('令和7年 4〜8 月の受付は業務名が定型語だけの登録が多い (r07 素案 §0)。')
if Y <= 2011:
    notes.append('業務名は定型語が中心 (平成24年度ごろから自由記述)。事業の種類と段階は粗い。')
if Y <= 2013:
    notes.append('前 5 年度の平年に平成20年度以前 (届出の範囲が狭い時期) が入る (D24)。')
if 2020 <= Y <= 2023:
    notes.append('道の届出の比率がなだらかに下がっていた時期 (D25)。道の件数の減少は契約の減少ではない。')
out.append('\n' + '\n'.join(f'- {n}' for n in notes) + '\n' if notes else '')

d = ROOT / f'reports/yearly/{short(Y).lower().replace("r", "r0") if Y >= 2019 and Y - 2018 < 10 else short(Y).lower()}'
d.mkdir(parents=True, exist_ok=True)
(d / 'tables.md').write_text('\n'.join(out) + '\n')
print(f'wrote {d / "tables.md"}')
