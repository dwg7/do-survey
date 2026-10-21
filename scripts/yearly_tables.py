#!/usr/bin/env python3
"""年度ごとの北海道測量概況 (新しい型) の根拠表 (D32)。

使い方: python3 scripts/yearly_tables.py <受付年度>   → reports/yearly/<r07 など>/tables.md

型 (reports/yearly/README.md):
  Y1 年度偏差 — 指標ごとの平年・傾向との比較と、情報の段階 (annual_overview.py と同じ物差し)
  Y2 予算と契約 — 開発局の当初 + 前年度の補正と開発局の届出、道の当初予算、道の委託契約と届出の比率 (D19・D25・D26)
  Y3 長期構造の確認 — 季節の形 (7 月への集中・冬の空白)、農業の割合、発注主体。他の地方の都道府県と比べられる年度は比べる (D21・D28)
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


def head14(p):
    """業務名の先頭 14 字。括弧の後を落とす (先頭の「(路線番号)」などは外してから)。"""
    return re.sub(r'[（(].*', '', re.sub(r'^\s*[（(][^）)]*[）)]\s*', '', p))[:14]


LEVEL = {0: '平年並み', 1: '平年と違うが短期傾向どおり', 2: '**予想外**', 3: '**かなり予想外**'}
out = [f'# {era(Y)} 北海道測量概況 — 根拠表\n',
       f'`scripts/yearly_tables.py {Y}` が生成。国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) ほかを dwg7 が編集・加工。'
       f'受付年度 {Y} (令和/平成の年度は 4 月〜翌 3 月)。平年 = 前 5 年度 ({short(Y - 5)}〜{short(Y - 1)}) の平均、短期傾向 = 前 5 年度の直線の延長。'
       '比べる指標が k 個ある群 (発注 3、分野 6、地域 14) は、k 個の最大が偶然超える確率が 32% / 5% になるしきい値で段階を決める (D20)。\n']

# ---- Y1 年度偏差 ----
GROUPS = [('件数', ['件数'], 1), ('発注', ['発注:北海道', '発注:北海道開発局', '発注:市町村'], 3),
          ('分野', [f'分野:{f}' for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤')], 6),
          ('地域', [f'地域:{b}' for b in BUREAUS], 14),
          ('時期', ['上期の割合'], 1), ('広がり', ['測量のあった市町村', '上位10市町村の割合', '複数市町村の測量'], 1)]
out.append('## Y1. 年度偏差 — 指標ごとの平年・傾向との比較\n')
out.append('| 群 | 指標 | 今年 | 平年 | z (平年) | 短期傾向の予測 | z (短期傾向) | 段階 |')
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
           f'予想外 = 平年からも短期傾向からも外れる。予想外の指標: ' + ('、'.join(s[0] for s in surprises) or 'なし') + '。\n')

# 平年 (前 5 年度) に平成20年度以前 (届出の範囲が狭く、分野の「不明」が多い時期) が入る年度は、後の 5 年度とも比べて物差しを確かめる (D38)。
if Y - 5 <= 2008:
    sampling_sd = ns['sampling_sd']
    out.append(f'**物差しの確かめ: 後の 5 年度 ({short(Y + 1)}〜{short(Y + 5)}) との比較** (平年に平成20年度以前が入る年度だけ。'
               '前の平年と後の 5 年度の両方から同じ向きに外れれば出来事の候補、前とだけ外れれば物差しの問題の候補)\n')
    out.append('| 指標 | 今年 | 前の平年 | z (前) | 後の 5 年度 | z (後) |')
    out.append('|---|---:|---:|---:|---:|---:|')
    unk = statistics.mean(sum(1 for r in by_year[x] if r['field'] == '不明') / len(by_year[x]) for x in range(Y - 5, Y)) if all(x in by_year for x in range(Y - 5, Y)) else None
    for g, keys, k in GROUPS:
        for key in keys:
            vals = [IND[x][key] for x in range(Y + 1, Y + 6)]
            ma = statistics.mean(vals)
            za = (IND[Y][key] - ma) / max(statistics.stdev(vals), sampling_sd(Y, key, ma))
            mb, _ = normal(Y, key)
            if abs(z(Y, key)) < THR[k][0] and abs(za) < THR[k][0]:
                continue
            f = (lambda x: f'{x:.0f}') if key in ('件数', '測量のあった市町村') else pct
            out.append(f'| {key} | {f(IND[Y][key])} | {f(mb)} | {z(Y, key):+.1f} | {f(ma)} | {za:+.1f} |')
    out.append('\n前か後のどちらかで群のしきい値の低い方を超えた指標だけを並べる。前の平年の 5 年度で分野が「不明」の割合の平均: '
               + (pct(unk) if unk is not None else '—') + '。\n')

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
        if yy - 1 < 2009:   # 補正予算の表は平成21年度から。平成20年度の補正は 0 ではなく、ない (レビュー、D41)
            out.append(f'| {short(yy)} | {ini[yy]:,.0f} | — | {ini[yy]:,.0f} (前年度の補正を含まない) | {sup[yy]:,.0f} | {zero[yy]:,.0f} | {kai[yy]} |')
        else:
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

# ---- Y3 長期構造の確認 ----
out.append('\n## Y3. 長期構造の確認\n')
mc = collections.Counter(int(r['recept_date'][5:7]) for r in rows if r['recept_date'])
mt = sum(mc.values())
sh = lambda ms: sum(mc[m] for m in ms) / mt
fc = collections.Counter(r['field'] for r in rows)
pc = collections.Counter(r['planner_type'] for r in rows)
out.append('| 長期構造の文 | 今年 | 判定の目安 |')
out.append('|---|---:|---|')
out.append(f'| 6〜8 月への集中 (北海道に固有、D28) | {pct(sh((6, 7, 8)))} (7 月 {pct(mc[7] / mt)}) | 他の都府県は 15〜45% (令和5〜7年度の 3 年度の合計。単年度の最大は 38〜49%) |')
out.append(f'| 冬 (1〜3 月) の空白 (雪国に共通、D28) | {pct(sh((1, 2, 3)))} | 雪国の県は 8% 以下 |')
out.append(f'| 最多の受付月 | {mc.most_common(1)[0][0]} 月 | 北海道は 6〜7 月、雪国の他の県は 9〜10 月 |')
out.append(f'| 農業農村が件数で最大 (農村型の地方に共通、D21) | {fc.most_common(1)[0][0]} {pct(fc.most_common(1)[0][1] / N)} | |')
out.append(f'| 発注は道と国で 8 割台後半 (D21、17 年度で 81〜89%) | 道 {pct(pc["北海道"] / N)}・開発局 {pct(pc["北海道開発局"] / N)}・市町村 {pct(pc["市町村"] / N)} | 市町村の発注は 10 地方で最少 |')
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
out.append('| 振興局 | 件数 | 割合 | 平年の割合 | z (平年) | z (短期傾向) | 段階 |')
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
out.append(f'| 業務名が 7 字未満の件数 | {N - free} | {sum(1 for r in pr if len(r["purpose"]) <= 6)} |')
shr = [r for r in rows if len(r['purpose']) <= 6]
if shr:
    nw = 10 if len(shr) > N / 2 else 5   # 業務名が決まり文句の年度は、語の選び方を前年度と比べられるように多めに出す
    out.append('\n7 字未満の業務名 (今年): 多い語 ' + '、'.join(f'「{k or "(空)"}」{v}' for k, v in sorted(collections.Counter(r['purpose'].strip() for r in shr).items(), key=lambda kv: (-kv[1], kv[0]))[:nw])
               + '。発注主体 ' + '、'.join(f'{k} {v}' for k, v in sorted(collections.Counter(r['planner_type'] for r in shr).items(), key=lambda kv: (-kv[1], kv[0]))))
    if nw == 10:
        psh = collections.Counter(r['purpose'].strip() for r in pr if len(r['purpose']) <= 6)
        out.append('\n7 字未満の業務名 (前年度): 多い語 ' + '、'.join(f'「{k or "(空)"}」{v}' for k, v in sorted(psh.items(), key=lambda kv: (-kv[1], kv[0]))[:10]))
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

# ---- Y7 内訳 (本文で使う数の出どころ) ----
# 会話の中でその場で問い合わせていた数を、ここで再現できるようにする (D34)。
out.append('\n## Y7. 内訳\n')
PT = ['北海道', '北海道開発局', '市町村', 'その他']
FL = ['農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤', '都市・まちづくり', '行政情報']
for yy in (Y - 1, Y):
    rs = by_year[yy]
    out.append(f'\n**{short(yy)}: 発注主体 × 分野 (件数)**\n')
    out.append('| 発注主体 | 計 | ' + ' | '.join(FL) + ' | ほか |')
    out.append('|---|---:|' + '---:|' * (len(FL) + 1))
    for t in PT:
        sub = [r for r in rs if (r['planner_type'] == t if t != 'その他' else r['planner_type'] not in PT[:3])]
        fc_ = collections.Counter(r['field'] for r in sub)
        out.append(f'| {t} | {len(sub)} | ' + ' | '.join(str(fc_[f]) for f in FL) + f' | {sum(v for f, v in fc_.items() if f not in FL)} |')
    st_ = collections.Counter(r['stage'] for r in rs if r['planner_type'] == '北海道' and r['field'] == '農業農村')
    out.append(f'\n道の農業農村の段階 ({short(yy)}): ' + '、'.join(f'{k} {v}' for k, v in st_.most_common()) + f' (計 {sum(st_.values())})')

SUB = [('土砂・洪水氾濫対策', r'土砂・?洪水氾濫'), ('砂防メンテナンス', r'砂防.*メンテナンス|メンテナンス.*砂防'), ('災害復旧', r'災害復旧|災害関連|復旧'),
       ('砂防・急傾斜・地すべり', r'砂防|地すべり|急傾斜|治山'), ('河川', r'河川|川.*改修|堤防|総合流域'), ('海岸', r'海岸|高潮'), ('ダム', r'ダム')]


def subtype(r):
    for n, pat in SUB:
        if re.search(pat, r['purpose']):
            return n
    return 'その他'


out.append('\n**道の防災・治水の内訳 (業務名の語、上から順に当てる)**\n')
out.append('| 年度 | 計 | ' + ' | '.join(n for n, _ in SUB) + ' | その他 |')
out.append('|---|---:|' + '---:|' * (len(SUB) + 1))
for yy in (Y - 2, Y - 1, Y):
    sub = [r for r in by_year[yy] if r['planner_type'] == '北海道' and r['field'] == '防災・治水']
    c = collections.Counter(subtype(r) for r in sub)
    out.append(f'| {short(yy)} | {len(sub)} | ' + ' | '.join(str(c[n]) for n, _ in SUB) + f' | {c["その他"]} |')

out.append('\n**発注主体ごとの上期の割合と、複数市町村にまたがる割合**\n')
out.append('| 年度 | 発注主体 | 件数 | 上期 | 上期の割合 | 複数市町村 | 複数の割合 |')
out.append('|---|---|---:|---:|---:|---:|---:|')
for yy in (Y - 2, Y - 1, Y):
    for t in PT[:3]:
        sub = [r for r in by_year[yy] if r['planner_type'] == t]
        h = sum(1 for r in sub if r['half'] == '上期')
        mm = sum(1 for r in sub if int(r['n_munis']) > 1)
        out.append(f'| {short(yy)} | {t} | {len(sub)} | {h} | {pct(h / len(sub))} | {mm} | {pct(mm / len(sub))} |')
for yy in (Y - 1, Y):
    mc_ = collections.Counter(int(r['recept_date'][5:7]) for r in by_year[yy] if r['recept_date'])
    out.append(f'\n{short(yy)} の受付の月別件数: ' + '、'.join(f'{m} 月 {mc_[m]}' for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3))
               + f' (4〜6 月 {sum(mc_[m] for m in (4, 5, 6))}、10〜12 月 {sum(mc_[m] for m in (10, 11, 12))})')

out.append('\n**計画機関の上位 (件数、前年度と今年)**\n')
pc0 = collections.Counter(r['planner'] for r in by_year[Y - 1])
pc1 = collections.Counter(r['planner'] for r in rows)
out.append('| 計画機関 | 前年度 | 今年 |')
out.append('|---|---:|---:|')
for pl, n in pc1.most_common(15):
    out.append(f'| {pl} | {pc0[pl]} | {n} |')

for pl in sorted(pc1, key=lambda k: (pc0[k] - pc1[k], k))[:3]:   # 前年度から最も増えた計画機関、同点は名前の順
    pp = collections.Counter(head14(r['purpose']) for r in rows if r['planner'] == pl)
    out.append(f'\n前年度から増えた計画機関: {pl} {pc0[pl]} → {pc1[pl]} の業務名 (先頭 14 字): '
               + '、'.join(f'{k} ({v})' for k, v in sorted(pp.items(), key=lambda kv: (-kv[1], kv[0]))[:6]))
out.append('\n前年度から最も減った計画機関: ' + '、'.join(f'{pl} {pc0[pl]} → {pc1[pl]}' for pl in sorted(pc0, key=lambda k: (pc1[k] - pc0[k], k))[:5]))
out.append('\n**件数の多い市町村の中身 (上位 8、発注主体 × 分野の上位 3)**\n')
for c_, n in mcnt.most_common(8):
    sub = [r for r in rows if c_ in r['ml']]
    top = collections.Counter((r['planner_type'], r['field']) for r in sub).most_common(3)
    out.append(f'- {active[c_]["fullName"]} {n} (前年度 {prev[c_]}): ' + '、'.join(f'{t}・{f} {v}' for (t, f), v in top))

out.append('\n**件数の多い市町村の受付の月 (上位 5)**\n')
for c_, n in mcnt.most_common(5):
    mm_ = collections.Counter(int(r['recept_date'][5:7]) for r in rows if c_ in r['ml'] and r['recept_date'])
    out.append(f'- {active[c_]["fullName"]} {n}: ' + '、'.join(f'{m} 月 {mm_[m]}' for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3) if mm_[m])
               + f' (10〜3 月 {sum(mm_[m] for m in (10, 11, 12, 1, 2, 3))})')
win = [r for r in rows if r['recept_date'][5:7] in ('01', '02', '03')]
wb = collections.Counter(b for r in win for b in r['bl'])
out.append(f'\n**冬 (1〜3 月) の受付 {len(win)} 件の振興局**: ' + ('、'.join(f'{b} {n}' for b, n in wb.most_common()) or 'なし'))
sb = [b for b in BUREAUS if abs(z(Y, f'地域:{b}')) >= 2]
for b in sb:
    c0 = collections.Counter((r['planner_type'], r['field']) for r in by_year[Y - 1] if b in r['bl'])
    c1 = collections.Counter((r['planner_type'], r['field']) for r in rows if b in r['bl'])
    keys = sorted(set(c0) | set(c1), key=lambda k: (-abs(c1[k] - c0[k]), k))[:6]   # 同点は名前の順 (集合の並びは実行ごとに変わる)
    out.append(f'\n**平年から外れた振興局の内訳: {b}** (前年度 → 今年、差の大きい順): '
               + '、'.join(f'{t}・{f} {c0[(t, f)]} → {c1[(t, f)]}' for t, f in keys))
    dsh = lambda yy: pct(sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and b in r['bl']) / max(1, sum(1 for r in by_year[yy] if r['planner_type'] == '北海道')))
    out.append(f'  - 道の測量のうち {b} に関わる割合 (分母の効果を除いた見方): ' + '、'.join(f'{short(yy)} {dsh(yy)}' for yy in range(max(2009, Y - 2), min(2025, Y + 5) + 1)))
    big = max(keys, key=lambda k: c1[k] - c0[k])
    if c1[big] - c0[big] <= 0:
        continue
    pp = collections.Counter(head14(r['purpose']) for r in rows if b in r['bl'] and (r['planner_type'], r['field']) == big)
    out.append(f'  - 最も増えた {big[0]}・{big[1]} の業務名 (先頭 14 字): ' + '、'.join(f'{k} ({v})' for k, v in pp.most_common(8)))
FZ = [f for f in ('農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤') if abs(z(Y, f'分野:{f}')) >= 2]
for f in FZ:
    c0 = collections.Counter(r['planner'] for r in by_year[Y - 1] if r['field'] == f)
    c1 = collections.Counter(r['planner'] for r in rows if r['field'] == f)
    keys = sorted(set(c0) | set(c1), key=lambda k: (-abs(c1[k] - c0[k]), k))[:8]   # 同点は名前の順
    out.append(f'\n**平年から外れた分野の内訳: {f}** (計画機関、前年度 → 今年、差の大きい順): '
               + '、'.join(f'{k} {c0[k]} → {c1[k]}' for k in keys))
    big = max(keys, key=lambda k: (c1[k] - c0[k], k))
    if c1[big] - c0[big] <= 0:
        continue
    pp = collections.Counter(head14(r['purpose']) for r in rows if r['field'] == f and r['planner'] == big)
    out.append(f'  - 最も増えた {big} の業務名 (先頭 14 字): ' + '、'.join(f'{k} ({v})' for k, v in sorted(pp.items(), key=lambda kv: (-kv[1], kv[0]))[:8]))
# 災害の直後の調査・設計 (被害調査・災害調査・災害設計・災害復旧) の測量 (D42: 災害の写り方を受付日で見る)
dz = sorted((r for r in rows if re.search('被害調査|災害調査|災害設計|災害復旧|災害助成|災害関連|災害査定', r['purpose'])), key=lambda r: (r['recept_date'], r['purpose']))
out.append(f'\n**業務名に災害の調査・設計・復旧の語 (被害調査・災害調査・災害設計・災害復旧・災害助成・災害関連・災害査定) がある測量 {len(dz)} 件**'
           + ('' if not dz else ' (受付日順、先頭 14 件): ' + '、'.join(f'{r["recept_date"]} {"・".join(r["bl"]) or "—"} {r["planner_type"]} {r["purpose"].strip()[:24]}' for r in dz[:14])))
out.append('\n**振興局ごとの発注主体 (件数)**\n')
out.append('| 振興局 | 計 | 道 | 開発局 | 市町村 |')
out.append('|---|---:|---:|---:|---:|')
for b in sorted(BUREAUS, key=lambda b: -bc[b]):
    sub = [r for r in rows if b in r['bl']]
    out.append(f'| {b} | {len(sub)} | ' + ' | '.join(str(sum(1 for r in sub if r['planner_type'] == t)) for t in PT[:3]) + ' |')

ALLY = range(2009, 2026)


def series(fn):
    return '、'.join(f'{short(yy)} {fn(yy)}' for yy in ALLY)


def mshare(yy, ms):
    rs = [r for r in by_year[yy] if r['recept_date']]
    return pct(sum(1 for r in rs if int(r['recept_date'][5:7]) in ms) / len(rs))


out.append('\n**平成21〜令和7年度の推移 (「最多」「最も高い」の確かめ用)**\n')
out.append('- 件数: ' + series(lambda yy: len(by_year[yy])))
out.append('- 6〜8 月の割合: ' + series(lambda yy: mshare(yy, (6, 7, 8))))
out.append('- 7 月の割合: ' + series(lambda yy: mshare(yy, (7,))))
out.append('- 道の件数: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道')))
out.append('- 開発局の件数: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道開発局')))
out.append('- 開発局の割合: ' + series(lambda yy: pct(sum(1 for r in by_year[yy] if r['planner_type'] == '北海道開発局') / len(by_year[yy]))))
out.append('- 道の割合: ' + series(lambda yy: pct(sum(1 for r in by_year[yy] if r['planner_type'] == '北海道') / len(by_year[yy]))))
out.append('- 位置基盤: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['field'] == '位置基盤')))
out.append('- 冬 (1〜3 月) の受付: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['recept_date'][5:7] in ('01', '02', '03'))))
out.append('- 航空レーザ: ' + series(lambda yy: sum(1 for r in by_year[yy] if '航空レーザ' in r['kinds'])))
out.append('- 上期 (4〜9 月) の割合 (平成16年度から): ' + '、'.join(f'{short(yy)} {mshare(yy, (4, 5, 6, 7, 8, 9))}' for yy in range(2004, 2026)))
out.append('- 道の農業農村: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and r['field'] == '農業農村')))
out.append('- 道の防災・治水: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and r['field'] == '防災・治水')))
out.append('- 道の道路: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and r['field'] == '道路')))
out.append('- 開発局の道路: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道開発局' and r['field'] == '道路')))
out.append('- 複数市町村の測量の割合: ' + series(lambda yy: pct(sum(1 for r in by_year[yy] if int(r['n_munis']) > 1) / len(by_year[yy]))))
TK = lambda yy: [r for r in by_year[yy] if r['planner_type'] == '北海道' and '十勝' in r['bl']]
out.append('- 十勝の道の防災・治水: ' + series(lambda yy: sum(1 for r in TK(yy) if r['field'] == '防災・治水')))
out.append('- うち業務名に「災害」: ' + series(lambda yy: sum(1 for r in TK(yy) if r['field'] == '防災・治水' and '災害' in r['purpose'])))
out.append('- 十勝の道の「道単…改修」(業務名に「道単」と「改修」): ' + series(lambda yy: sum(1 for r in TK(yy) if '道単' in r['purpose'] and '改修' in r['purpose'])))
out.append('- 全道の道の「道単…改修」: ' + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and '道単' in r['purpose'] and '改修' in r['purpose'])))
out.append('- 平成28年台風 10 号の災害復旧助成・災害関連の 3 河川 (ペケレベツ川・パンケ新得川・芽室川) の名を含む道の測量 (D42): '
           + series(lambda yy: sum(1 for r in by_year[yy] if r['planner_type'] == '北海道' and re.search('ペケレベツ|パンケ新得|芽室川', r['purpose']))))
out.append('- 測量のない市町村: ' + series(lambda yy: sum(1 for c_ in active if not any(c_ in r['ml'] for r in by_year[yy]))))

d = ROOT / f'reports/yearly/{short(Y).lower().replace("r", "r0") if Y >= 2019 and Y - 2018 < 10 else short(Y).lower()}'
d.mkdir(parents=True, exist_ok=True)
(d / 'tables.md').write_text('\n'.join(out) + '\n')
print(f'wrote {d / "tables.md"}')
