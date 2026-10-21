#!/usr/bin/env python3
"""都市計画関係の公共測量: 毎年何件か、年度の山 (周期) はあるか (D30)。

入力: analysis/classified.csv
出力: reports/cityplan/tables.md

都市計画関係は業務名で定義する (分野の規則 R17・R18 は「都市計画図」を行政情報に入れるので使わない)。
- 都市計画図: 業務名に「都市計画・用途地域・立地適正」があり、測量の種類が図化・撮影・修正測量など地図を作るもの (都市計画基図の作成・更新)。
- 都市計画 (その他): 同じ語があり、基準点測量・用地測量など地図を作らないもの。
- 土地区画整理: 業務名に「土地区画整理」(市街地の区画整理。農地の「区画整理」は含まない)。
- 国の都市部の調査: 計画機関が国 (その他) で、業務名 (定型語) が「都市計画」のもの (平成20年度前後の国土交通省 地籍整備課の基準点測量)。
- 市町村の地形図・航空写真 (参考): 市町村の発注で、業務名に「都市計画」の語はないが地形図・数値地形図・航空写真などを作るもの。
  都市計画図と固定資産・統合型 GIS の背景図を兼ねるものが多く、都市計画関係かは業務名から決められない。
道の都市計画基礎調査 (T9) は data/external/hokkaido-toshikeikaku-kiso.csv (道の入札公告の業務処理要領の別表から手で写した表)。
業務名は平成23年度ごろまで定型語 (「都市計画」) で、平成24年度ごろから自由記述になる (レンズの癖 3)。
"""
import collections
import csv
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
rows = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
for r in rows:
    r['year'] = int(r['year'])
CITY = re.compile(r'都市計画|用途地域|立地適正')
LR = re.compile(r'土地区画整理')
MAPK = re.compile(r'撮影|図化|写測|修正測量|数値|写真地図|既成図')
BASE = re.compile(r'地形図|数値地形|基盤地図|現況図|白図|航空写真|写真撮影|オルソ|航空レーザ')
CATS = ['都市計画図', '都市計画 (その他)', '土地区画整理', '国の都市部の調査', '市町村の地形図・航空写真 (参考)']
YEARS = list(range(1984, 2027))


def cat(r):
    p = r['purpose']
    if LR.search(p):
        return '土地区画整理'
    if CITY.search(p):
        if r['planner_type'] == '国 (その他)':
            return '国の都市部の調査'
        return '都市計画図' if MAPK.search(r['kinds']) else '都市計画 (その他)'
    if r['planner_type'] == '市町村' and BASE.search(p) and MAPK.search(r['kinds']):
        return '市町村の地形図・航空写真 (参考)'
    return None


for r in rows:
    r['cat'] = cat(r)
sel = [r for r in rows if r['cat']]


def era(y):
    if y >= 2019:
        return 'R1' if y == 2019 else f'R{y - 2018}'
    return f'H{y - 1988}' if y >= 1989 else f'S{y - 1925}'


out = ['# 都市計画関係の公共測量 — 根拠表\n',
       '`scripts/city_planning.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部) を dwg7 が編集・加工。'
       '都市計画関係は業務名で定義した (定義はスクリプトの冒頭)。受付年度、測量 1 件を 1 件と数える。令和8年度 (2026) は途中。\n']

yc = {y: collections.Counter(r['cat'] for r in sel if r['year'] == y) for y in YEARS}
tot = collections.Counter(r['year'] for r in rows)
out.append('## T1. 年度ごとの件数\n')
out.append('| 年度 | ' + ' | '.join(CATS) + ' | 計 (参考を除く) | 全測量 |')
out.append('|---|' + '---:|' * (len(CATS) + 2))
for y in YEARS:
    core = sum(yc[y][c] for c in CATS[:4])
    out.append(f'| {era(y)} ({y}) | ' + ' | '.join(str(yc[y][c]) for c in CATS) + f' | {core} | {tot[y]} |')

# 周期: 都市計画図の年度系列の自己相関と、計画機関ごとの更新の間隔
mp = [r for r in sel if r['cat'] == '都市計画図']
s = [sum(1 for r in mp if r['year'] == y) for y in range(1984, 2020)]
m = statistics.mean(s)
var = sum((v - m) ** 2 for v in s)
out.append('\n## T2. 都市計画図の件数の自己相関 (昭和59〜令和元年度)\n')
out.append('| ずれ (年) | ' + ' | '.join(str(k) for k in range(1, 11)) + ' |')
out.append('|---|' + '---:|' * 10)
ac = [sum((s[i] - m) * (s[i + k] - m) for i in range(len(s) - k)) / var for k in range(1, 11)]
out.append('| 自己相関 | ' + ' | '.join(f'{a:+.2f}' for a in ac) + ' |')
out.append('\n件数の少ない近年 (令和2年度以降) は除いた。\n')

by = collections.defaultdict(set)
for r in mp:
    by[r['planner']].add(r['year'])
gaps = []
for ys in by.values():
    ys = sorted(ys)
    gaps += [b - a for a, b in zip(ys, ys[1:])]
g = collections.Counter(gaps)
out.append('## T3. 計画機関ごとの都市計画図の更新の間隔\n')
out.append(f'都市計画図を登録した計画機関 {len(by)}、うち 2 回以上 {sum(1 for v in by.values() if len(v) >= 2)}。'
           f'1 年の間隔 ({g[1]} 回) は撮影の翌年に図化するなどの続きの業務とみて、2 年以上の間隔だけを数える。\n')
out.append('| 間隔 (年) | ' + ' | '.join(str(k) for k in range(2, 16)) + ' | 16 年以上 |')
out.append('|---|' + '---:|' * 15)
out.append('| 回数 | ' + ' | '.join(str(g[k]) for k in range(2, 16)) + f' | {sum(v for k, v in g.items() if k >= 16)} |')
long_gaps = [x for x in gaps if x >= 2]
out.append(f'\n2 年以上の間隔の中央値 {statistics.median(long_gaps):.0f} 年、5〜8 年が {sum(g[k] for k in range(5, 9))} 回 '
           f'(2 年以上の {len(long_gaps)} 回のうち {100 * sum(g[k] for k in range(5, 9)) / len(long_gaps):.0f}%)。\n')

out.append('## T4. 都市計画図を 4 回以上登録した計画機関と年度\n')
out.append('| 計画機関 | 年度 |')
out.append('|---|---|')
for p, ys in sorted(by.items(), key=lambda x: (-len(x[1]), x[0])):
    if len(ys) >= 4:
        out.append(f'| {p} | ' + '、'.join(era(y) for y in sorted(ys)) + ' |')

out.append('\n## T5. 山の年度の顔ぶれ (都市計画図)\n')
for y in (1994, 2002, 2009, 2016):
    ps = sorted({r['planner'].replace('北海道', '', 1) if r['planner'].startswith('北海道') else r['planner'] for r in mp if r['year'] == y})
    out.append(f'- {era(y)} ({y}、{sum(1 for r in mp if r["year"] == y)} 件): ' + '、'.join(ps))

out.append('\n## T6. 受付の月 (都市計画図と全測量、平成21〜令和7年度)\n')
rec = [r for r in mp if 2009 <= r['year'] <= 2025 and r['recept_date']]
allr = [r for r in rows if 2009 <= r['year'] <= 2025 and r['recept_date']]
MS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)
for lab, rs in (('都市計画図', rec), ('全測量', allr)):
    c = collections.Counter(int(r['recept_date'][5:7]) for r in rs)
    out.append(f'- {lab} ({len(rs)} 件): ' + '・'.join(f'{mm} 月 {100 * c[mm] / len(rs):.0f}%' for mm in MS))

out.append('\n## T7. 発注主体 (都市計画関係、参考を除く、平成21〜令和7年度)\n')
core = [r for r in sel if r['cat'] in CATS[:4] and 2009 <= r['year'] <= 2025]
c = collections.Counter(r['planner_type'] for r in core)
out.append(' / '.join(f'{k} {v} ({100 * v / len(core):.0f}%)' for k, v in c.most_common()))

# 市町村の航空写真・地形図の目的 (都市計画の語のないもの): 固定資産・森林・その他
TAX = re.compile(r'固定資産|家屋|課税|マッピング')
FOREST = re.compile(r'森林|Ｊクレジット|Jクレジット')
mun = [r for r in rows if r['planner_type'] == '市町村' and MAPK.search(r['kinds']) and (BASE.search(r['purpose']) or TAX.search(r['purpose']))
       and not CITY.search(r['purpose']) and 2009 <= r['year'] <= 2026]


def sub(r):
    return '固定資産・家屋' if TAX.search(r['purpose']) else '森林' if FOREST.search(r['purpose']) else '地形図・航空写真 (目的の記載なし)'


SUBS = ['固定資産・家屋', '森林', '地形図・航空写真 (目的の記載なし)']
out.append('\n## T8. 市町村の航空写真・地形図の目的 (業務名に「都市計画」の語がないもの、年度ごと)\n')
out.append('| 年度 | ' + ' | '.join(SUBS) + ' | 都市計画図 (T1 の再掲) |')
out.append('|---|' + '---:|' * (len(SUBS) + 1))
for y in range(2009, 2027):
    c = collections.Counter(sub(r) for r in mun if r['year'] == y)
    out.append(f'| {era(y)} | ' + ' | '.join(str(c[k]) for k in SUBS) + f' | {yc[y]["都市計画図"]} |')
out.append('\n固定資産税の評価替えは 3 年ごと (基準年度は平成30・令和3・6・9年度など)。')
out.append('\n**固定資産・家屋の航空写真を 2 回以上登録した市町村**\n')
tb = collections.defaultdict(set)
for r in mun:
    if sub(r) == '固定資産・家屋':
        tb[r['planner']].add(r['year'])
for p_, ys in sorted(tb.items(), key=lambda x: (-len(x[1]), x[0])):
    if len(ys) >= 2:
        out.append(f'- {p_}: ' + '、'.join(era(y) for y in sorted(ys)))
out.append('')
# 道の都市計画基礎調査との照合
kiso = list(csv.DictReader((ROOT / 'data/external/hokkaido-toshikeikaku-kiso.csv').open()))
out.append('\n## T9. 道の都市計画基礎調査の対象と基準日 (令和7・8年度の入札公告の業務処理要領から)\n')
out.append('| 実施年度 | 業務 | 都市計画区域 | 市町 | 前回の基準日 | 今回の基準日 | 市町の都市計画図の登録 (年度) |')
out.append('|---|---|---|---|---|---|---|')
for k in kiso:
    ys = sorted({r['year'] for r in mp if r['planner'] == '北海道' + k['municipality']})
    out.append(f'| {era(int(k["fiscal_year"]))} | {k["part"]} | {k["planning_area"]} | {k["municipality"]} | {k["previous_base_date"]} | {k["current_base_date"]} | '
               + ('、'.join(era(y) for y in ys) or '—') + ' |')
out.append(f'\n基礎調査そのものは公共測量として登録されていない (業務名に「基礎調査」を含む都市計画の測量は 0 件)。'
           '建築確認と市町の地図データ (家屋所在図・地番図など) を集める調査で、測量を伴わない。\n')
yy = [r['year'] for r in mp if 1985 <= r['year'] <= 2024]
ph = collections.Counter(y % 5 for y in yy)
exp = len(yy) / 5
chi = sum((ph[k] - exp) ** 2 / exp for k in range(5))
out.append('## T10. 都市計画図の更新と国勢調査の年 (昭和60〜令和6年度)\n')
out.append('基礎調査の基準日は国勢調査 (10 月 1 日) にそろう。国勢調査の年度を 0 として、都市計画図の登録の年度のずれを数える。\n')
out.append('| 国勢調査の年度からのずれ | 0 (国勢調査の年度) | +1 | +2 | +3 | +4 (国勢調査の前年度) |')
out.append('|---|---:|---:|---:|---:|---:|')
out.append('| 件数 | ' + ' | '.join(f'{ph[k]} ({100 * ph[k] / len(yy):.0f}%)' for k in range(5)) + ' |')
out.append(f'\n一様なら各 20%。カイ二乗 {chi:.1f} (自由度 4、5% の棄却点 9.49)。\n')
# T11 次の更新の目安 (D49): 過去の間隔 (2 年以上) の中央値を最後の年度に足す。外部の計画では確かめていない目安。
NOW = 2026   # 当年度 (途中)


def outlook(ys):
    ys = sorted(ys)
    gs = [b - a for a, b in zip(ys, ys[1:]) if b - a >= 2]
    if not gs:
        return None
    m = int(statistics.median(gs))
    nxt = ys[-1] + m
    state = '当年度に登録あり' if ys[-1] == NOW else ('間隔を過ぎた (まだ登録がない)' if nxt < NOW else ('当年度が目安' if nxt == NOW else '先'))
    return ys, gs, m, nxt, state


# 市町村の航空写真は業務名 (固定資産の語) ではなく測量の種類 (写真地図作成・オルソ) で拾う: 業務名に「固定資産」がなくても同じ周期で続く (D49)
ortho = collections.defaultdict(set)
for r in rows:
    if r['planner_type'] == '市町村' and r['year'] <= NOW and ('写真地図作成' in r['kinds'] or 'オルソ' in r['kinds']):
        ortho[r['planner']].add(r['year'])
out.append('\n## T11a. 市町村の航空写真 (写真地図作成・オルソ) の周期と固定資産税の評価替え\n')
out.append('測量の種類に「写真地図作成」か「オルソ」がある市町村の登録 (3 回以上)。評価替えの基準年度は平成30 (2018)・令和3 (2021)・6 (2024)・9 (2027)・12 (2030) 年度。'
           '「基準年度の何年前か」は、各登録の年度から次の基準年度までの年数。\n')
out.append('| 市町村 | 登録の年度 | 間隔 (年) | 基準年度の何年前か | 次の目安 | 状態 |')
out.append('|---|---|---|---|---|---|')
for p_, ys in sorted(ortho.items(), key=lambda x: (-len(x[1]), x[0])):
    if len(ys) < 3:
        continue
    ys_ = sorted(ys)
    gs = [b - a for a, b in zip(ys_, ys_[1:])]
    lead = [((2018 - y) % 3) or 3 for y in ys_]
    o = outlook(ys)
    nxt, state = (o[3], o[4]) if o else (None, '—')
    out.append(f'| {p_} | ' + '、'.join(era(y) for y in ys_) + f' | {"・".join(str(x) for x in gs)} | {"・".join(str(x) for x in lead)} | '
               + (f'{era(nxt)} ({nxt})' if nxt else '—') + f' | {state} |')
out.append('')
NEWFORM = re.compile(r'点群|ＭＭＳ|MMS|車載写真レーザ|地理情報システム|ＧＩＳ|GIS|デジタル化')
nf = sorted((r for r in rows if r['planner_type'] == '市町村' and 2019 <= r['year'] <= NOW and NEWFORM.search(r['purpose'] + r['kinds'])), key=lambda r: (r['year'], r['planner']))
out.append(f'\n## T12. 市町村の新しい形の地図の整備 (令和元年度以降、業務名か測量の種類に点群・MMS・GIS・デジタル化の語がある登録 {len(nf)} 件)\n')
out.append('| 年度 | 計画機関 | 業務名 (先頭 30 字) | 測量の種類 (先頭 30 字) |')
out.append('|---|---|---|---|')
for r in nf:
    out.append(f'| {era(r["year"])} | {r["planner"]} | {r["purpose"].strip()[:30]} | {r["kinds"][:30]} |')
out.append('')

for title, src, minn in (('都市計画図 (3 回以上登録した計画機関)', by, 3),):
    out.append(f'\n## T11b. 次の更新の目安: {title}\n')
    out.append('過去の更新の間隔 (2 年以上) の中央値を、最後の登録の年度に足した目安。間隔がそろっているかも並べる。令和8年度 (2026) は途中。\n')
    out.append('| 計画機関 | 登録の年度 | 間隔 (年) | 間隔の中央値 | 次の目安 | 状態 |')
    out.append('|---|---|---|---:|---|---|')
    for p_, ys in sorted(src.items(), key=lambda x: (x[0])):
        if len(ys) < minn:
            continue
        o = outlook(ys)
        if not o:
            continue
        ys_, gs, m, nxt, state = o
        out.append(f'| {p_} | ' + '、'.join(era(y) for y in ys_) + f' | {"・".join(str(x) for x in gs)} | {m} | {era(nxt)} ({nxt}) | {state} |')
    out.append('')

(ROOT / 'reports/cityplan').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/cityplan/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/cityplan/tables.md')
