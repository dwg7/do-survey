#!/usr/bin/env python3
"""人口千人前後の町村で、公共測量は local か — 主体と受益の 2 軸 (D29)。

入力: analysis/classified.csv、docs/vendor/do/data/municipalities.json、
      data/raw/population/jumin-2026.xlsx (北海道「住民基本台帳人口・世帯数」令和8年1月1日現在、
      https://www.pref.hokkaido.lg.jp/ss/tuk/900brr/index2.html)
出力: data/external/hokkaido-population-2026.csv、reports/smallvillage/tables.md

数え方: 平成21〜令和7年度。測量が関わった市町村それぞれに 1 件 (関与件数)。
主体の軸 (誰が発注したか):
  A 自らの市町村 / B 地域の団体ほか (土地改良区・組合・会社など) / C 道・国で、その市町村の中で完結 / D 道・国で、複数の市町村にまたがる / E 他の市町村
受益の軸 (測量が何に向いているか。規則は下の benefit()):
  1 自前 (A・B・E)
  2 道・国の事業で、その土地と暮らしに向くもの: 農業農村・水産・森林 (村の中)、道の防災 (砂防・急傾斜・ダム・海岸・河川)、道の道路 (道道)、地籍
  3 道・国の広域の網と一括業務: 開発局の道路・河川・管理 (国道・高規格道路・一級河川。業務名に国道・自動車道・河川・堤防・水防とあるものを含む)、4 市町村以上にまたがる測量、業務名に「管内」「地区道路航空」など一括の語があるもの
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
import xlsx_rows  # noqa: E402

SRC = 'https://www.pref.hokkaido.lg.jp/ss/tuk/900brr/index2.html'
YEARS = range(2009, 2026)
M = {m['code']: m for m in json.loads((ROOT / 'docs/vendor/do/data/municipalities.json').read_text())['municipalities'] if m['status'] == 'active'}
pop = {}
for r in xlsx_rows.rows(ROOT / 'data/raw/population/jumin-2026.xlsx'):
    if r and isinstance(r[0], str) and len(r) > 3 and isinstance(r[3], float):
        pop[r[0].replace('　', '').strip()] = int(r[3])
assert all(m['fullName'] in pop for m in M.values())
with (ROOT / 'data/external/hokkaido-population-2026.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['code', 'name', 'population', 'date', 'source'])
    for c, m in sorted(M.items()):
        w.writerow([c, m['fullName'], pop[m['fullName']], '2026-01-01', SRC])

rows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if int(r['year']) in YEARS]
WIDE = re.compile(r'管内|地区道路航空|一連|全域|森林計画')
NETWORK = re.compile(r'国道|自動車道|河川|堤防|水防')


def actor(r, c):
    pt = r['planner_type']
    if pt == '市町村':
        return 'A' if M[c]['fullName'] in r['planner'] else 'E'
    if pt == 'その他':
        return 'B'
    return 'C' if r['n_munis'] == '1' else 'D'


def benefit(r, c):
    a = actor(r, c)
    if a in 'ABE':
        return '1'
    n = int(r['n_munis'])
    if n >= 4 or (WIDE.search(r['purpose']) and n >= 2):
        return '3'
    if r['planner_type'] != '北海道' and r['field'] in ('道路', '公物管理', '防災・治水', '位置基盤', '行政情報'):
        return '3'   # 開発局などの国道・高規格道路・一級河川とその管理
    if r['planner_type'] != '北海道' and NETWORK.search(r['purpose']):
        return '3'   # 分野の規則で農業などに入った国の道路・河川 (例: 「名寄水防拠点整備…用地測量」)
    return '2'


def pclass(p):
    return ('1 千人未満' if p < 1000 else '2 千〜3千人' if p < 3000 else '3 3千〜1万人' if p < 10000
            else '4 1万〜5万人' if p < 50000 else '5 5万人以上')


pairs = [(r, c) for r in rows for c in r['muni_codes'].split() if c in M]
AN = {'A': '自らの市町村', 'B': '地域の団体ほか', 'C': '道・国 (中で完結)', 'D': '道・国 (またがる)', 'E': '他の市町村'}
BN = {'1': '自前', '2': '道・国: その土地と暮らし', '3': '道・国: 広域の網・一括'}

out = ['# 人口千人前後の町村の公共測量 — 主体と受益 — 根拠表\n',
       '`scripts/small_villages.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部) と北海道「住民基本台帳人口・世帯数」'
       '(令和8年1月1日現在) を dwg7 が編集・加工。平成21〜令和7年度、関与件数 (測量が関わった市町村それぞれに 1 件)。\n']

g = collections.defaultdict(list)
for r, c in pairs:
    g[pclass(pop[M[c]['fullName']])].append((r, c))
nm = collections.Counter(pclass(pop[m['fullName']]) for m in M.values())
popsum = collections.Counter()
for m in M.values():
    popsum[pclass(pop[m['fullName']])] += pop[m['fullName']]

out.append('## T1. 人口の規模ごとの主体 (関与件数の割合)\n')
out.append('| 人口の規模 | 市町村の数 | 関与件数 | 1 市町村・1 年度あたり | 人口千人・1 年度あたり | ' + ' | '.join(AN.values()) + ' |')
out.append('|---|---:|---:|---:|---:|' + '---:|' * len(AN))
for k in sorted(g):
    c = collections.Counter(actor(r, cc) for r, cc in g[k])
    n = len(g[k])
    out.append(f'| {k[2:]} | {nm[k]} | {n} | {n / nm[k] / len(YEARS):.1f} | {1000 * n / popsum[k] / len(YEARS):.2f} | '
               + ' | '.join(f'{100 * c[a] / n:.0f}%' for a in AN) + ' |')

out.append('\n## T2. 人口の規模ごとの受益 (関与件数の割合)\n')
out.append('| 人口の規模 | ' + ' | '.join(BN.values()) + ' |')
out.append('|---|' + '---:|' * len(BN))
for k in sorted(g):
    c = collections.Counter(benefit(r, cc) for r, cc in g[k])
    n = len(g[k])
    out.append(f'| {k[2:]} | ' + ' | '.join(f'{100 * c[b] / n:.0f}%' for b in BN) + ' |')

small = sorted([m for m in M.values() if pop[m['fullName']] < 1500], key=lambda m: pop[m['fullName']])
out.append('\n## T3. 人口 1,500 人未満の町村ごと\n')
out.append('| 町村 | 振興局 | 人口 | 関与件数 | ' + ' | '.join(f'{a} {AN[a]}' for a in AN) + ' | ' + ' | '.join(BN.values()) + ' |')
out.append('|---|---|---:|---:|' + '---:|' * (len(AN) + len(BN)))
for m in small:
    ps = [(r, c) for r, c in pairs if c == m['code']]
    ca = collections.Counter(actor(r, c) for r, c in ps)
    cb = collections.Counter(benefit(r, c) for r, c in ps)
    out.append(f'| {m["fullName"]} | {m["bureau"]} | {pop[m["fullName"]]:,} | {len(ps)} | ' + ' | '.join(str(ca[a]) for a in AN)
               + ' | ' + ' | '.join(str(cb[b]) for b in BN) + ' |')

out.append('\n## T4. 人口千人未満の 4 村の全件 (分類の確かめ用)\n')
out.append('| 村 | 年度 | 計画機関 | 市町村数 | 分野 | 業務名 (先頭 40 字) | 主体 | 受益 |')
out.append('|---|---:|---|---:|---|---|---|---|')
for m in [m for m in small if pop[m['fullName']] < 1000]:
    ps = sorted([(r, c) for r, c in pairs if c == m['code']], key=lambda x: (benefit(*x), actor(*x), x[0]['year']))
    for r, c in ps:
        out.append(f'| {m["fullName"]} | {r["year"]} | {r["planner"].replace("北海道開発局", "開発局")} | {r["n_munis"]} | {r["field"]} '
                   f'| {(r["purpose"] or "")[:40].replace("|", "／")} | {AN[actor(r, c)]} | {BN[benefit(r, c)]} |')

# 受益 2 の中身 (千人未満)
out.append('\n## T5. 「道・国: その土地と暮らし」の分野 (人口の規模ごと、件数)\n')
fs = ['農業農村', '防災・治水', '道路', '水産', '公物管理', '森林・林業', '地籍・登記・課税']
out.append('| 人口の規模 | ' + ' | '.join(fs) + ' | その他 |')
out.append('|---|' + '---:|' * (len(fs) + 1))
for k in sorted(g):
    c = collections.Counter(r['field'] for r, cc in g[k] if benefit(r, cc) == '2')
    out.append(f'| {k[2:]} | ' + ' | '.join(str(c[f]) for f in fs) + f' | {sum(v for f, v in c.items() if f not in fs)} |')
out.append('')
(ROOT / 'reports/smallvillage').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/smallvillage/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/smallvillage/tables.md')
