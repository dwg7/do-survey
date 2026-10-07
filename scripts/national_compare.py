#!/usr/bin/env python3
"""北海道の「地勢」(毎年ほぼ同じ特徴) を、他の地方と比べて北海道に固有かを試す (D21)。

入力: data/raw/<区分>-<年度>.json (scripts/fetch.py --section <区分> --years 2023 2024 2025)。区分 A〜J (K・L は企画部で除く)
出力: reports/national/compare.md

- 期間は令和5〜7年度 (2023〜2025) の 3 年度。
- 物差し: 他の 9 地方 (東北〜沖縄) の平均と標準偏差から、北海道がいくつ離れているか (z)。|z| ≥ 2 を北海道の特徴とする。
  地方は 9 つしかないので標準偏差は粗い。順位 (10 地方中の何位か) も併記する。
- 発注主体は計画機関名から県名を除いた残りで分ける。分野は scripts/classify.py の規則 (業務名・担当部署) をそのまま使う。
  北海道向けの規則なので他の地方では「不明」が多くなりうる。不明の割合も出す。
- 「分野: 行政情報」は北海道の業務名の書き方に合わせた規則で、他の地方の航空写真は定型語「固定資産」「都市計画」として
  別の分野に入る。比べるのは「航空写真・オルソを含む測量」(業務名と測量種別) と「固定資産 (課税) の測量」で行う (D21)。
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
import classify  # noqa: E402

YEARS = (2023, 2024, 2025)
SECTIONS = {'A': '北海道', 'B': '東北', 'C': '関東', 'D': '北陸', 'E': '中部', 'F': '近畿', 'G': '中国', 'H': '四国', 'I': '九州', 'J': '沖縄'}
PREFS = ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県', '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都',
         '神奈川県', '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府',
         '大阪府', '兵庫県', '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県',
         '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
NATIONAL = re.compile(r'(国土交通省|地方整備局|開発局|農政局|農林水産省|森林管理|林野庁|法務|防衛|自衛隊|環境省|内閣府|総合事務局|水資源機構|国土地理院)')
OFFICE = re.compile(r'(振興局|事務所|県民局|土木|農林|建設|センター|整備局|支庁|農務|局|部|課|庁|委員会|港務所)')
OTHER = re.compile(r'(土地改良区|土地改良事業|組合|機構|株式会社|会社|公社|共同施行|区画整理|大学|協会|公益|財団|社団|協議会)')
AERIAL = re.compile(r'(航空写真|写真撮影|オルソ|写真地図|数値撮影|空中写真|カラー撮影|モノクロ撮影)')
FIELDS = ['農業農村', '道路', '防災・治水', '公物管理', '地籍・登記・課税', '位置基盤', '都市・まちづくり', '行政情報', '上下水道・衛生', '港湾・空港・鉄道', '不明']


def planner_kind(name):
    if NATIONAL.search(name):
        return '国'
    if OTHER.search(name):
        return 'その他'
    rest = name
    for p in PREFS:
        if name.startswith(p):
            rest = name[len(p):]
            break
    m = re.match(r'^[^\d\s]{1,7}?[市区町村]', rest)
    if m and not OFFICE.search(m.group(0)):
        return '市区町村'
    if rest == '' or OFFICE.search(rest) or rest.startswith(('企業局', '住宅供給公社', '道路公社')):
        return '都道府県'
    return 'その他'


arules = classify.load_rules('aim-rules.csv')
data = {}
for sec in SECTIONS:
    recs = []
    for y in YEARS:
        d = json.loads((ROOT / f'data/raw/{sec}-{y}.json').read_text())
        for it in d['items']:
            row = {'planner': it['plannerName'] or '', 'purpose': it['purpose'] or '', 'charge_section': it['chargeSection'] or ''}
            field, aim, _ = classify.aim_of(row, arules)
            m = re.match(r'\d{4}/(\d{2})/', it['dateReceptYmd'] or '')
            text = (it['purpose'] or '') + ' ' + (it['contentsType'] or '')
            recs.append({'aerial': bool(AERIAL.search(text)), 'tax': bool(re.search(r'固定資産|課税|家屋異動', text + (it['chargeSection'] or ''))),
                         'year': y, 'month': int(m.group(1)) if m else None, 'kind': planner_kind(row['planner']),
                         'field': field, 'aim': aim, 'multi': len([c for c in re.split(r'[,、，]', it['areaCityName'] or '') if c.strip()]) > 1})
    data[sec] = recs


def share(recs, pred):
    return sum(1 for r in recs if pred(r)) / len(recs)


METRICS = []   # (名前, 関数)
METRICS.append(('件数 (年平均)', lambda rs: len(rs) / len(YEARS)))
METRICS.append(('上期 (4〜9 月) の割合', lambda rs: share([r for r in rs if r['month']], lambda r: 4 <= r['month'] <= 9)))
for mth in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3):
    METRICS.append((f'{mth} 月の割合', lambda rs, m=mth: share([r for r in rs if r['month']], lambda r: r['month'] == m)))
for k in ('都道府県', '国', '市区町村', 'その他'):
    METRICS.append((f'発注: {k}', lambda rs, k=k: share(rs, lambda r: r['kind'] == k)))
for f in FIELDS:
    METRICS.append((f'分野: {f}', lambda rs, f=f: share(rs, lambda r: r['field'] == f)))
METRICS.append(('複数市町村の測量', lambda rs: share(rs, lambda r: r['multi'])))
METRICS.append(('航空写真・オルソを含む測量', lambda rs: share(rs, lambda r: r['aerial'])))
METRICS.append(('固定資産 (課税) の測量', lambda rs: share(rs, lambda r: r['tax'])))

vals = {name: {sec: fn(data[sec]) for sec in SECTIONS} for name, fn in METRICS}

out = ['# 北海道の「地勢」は北海道に固有か — 地方測量部の比較 (令和5〜7年度)\n',
       '`scripts/national_compare.py` が生成。データは国土地理院「公共測量実施情報」の地方測量部区分 A〜J の令和5〜7年度 (受付年度)。'
       'z は北海道が他の 9 地方の平均から標準偏差のいくつ分離れているか (|z| ≥ 2 を太字)。順位は 10 地方中で大きい方から。\n']


def fmt(name, v):
    return f'{v:.0f}' if name.startswith('件数') else f'{100 * v:.0f}%'


out.append('\n## 地方ごとの値\n')
heads = ['指標'] + [f'{SECTIONS[s]}' for s in SECTIONS] + ['北海道の z', '北海道の順位']
out.append('| ' + ' | '.join(heads) + ' |')
out.append('|' + '|'.join('---' if i == 0 else '---:' for i in range(len(heads))) + '|')
flags = []
for name, _ in METRICS:
    v = vals[name]
    others = [v[s] for s in SECTIONS if s != 'A']
    m, sd = statistics.mean(others), statistics.stdev(others)
    zv = (v['A'] - m) / sd if sd > 0 else 0.0
    rank = 1 + sum(1 for s in SECTIONS if v[s] > v['A'])
    zs = f'**{zv:+.1f}**' if abs(zv) >= 2 else f'{zv:+.1f}'
    if abs(zv) >= 2:
        flags.append((name, zv, rank))
    out.append('| ' + ' | '.join([name] + [fmt(name, v[s]) for s in SECTIONS] + [zs, f'{rank}']) + ' |')
out.append('')
out.append('\n## 北海道の特徴 (|z| ≥ 2)\n')
for name, zv, rank in sorted(flags, key=lambda x: -abs(x[1])):
    out.append(f'- {name}: z = {zv:+.1f} (10 地方中 {rank} 位)')
out.append('')

# 受付月の形 (山の位置) を地方ごとに
out.append('\n## 受付の山の月 (3 年度の合計で最も多い月と、その割合)\n')
out.append('| 地方 | 最多の月 | 割合 | 2 番目の月 | 割合 |')
out.append('|---|---:|---:|---:|---:|')
for s in SECTIONS:
    c = collections.Counter(r['month'] for r in data[s] if r['month'])
    (m1, n1), (m2, n2) = c.most_common(2)
    tot = sum(c.values())
    out.append(f'| {SECTIONS[s]} | {m1} 月 | {100 * n1 / tot:.0f}% | {m2} 月 | {100 * n2 / tot:.0f}% |')
out.append('')

# 年ごとの安定性 (北海道の特徴が 3 年とも同じ向きか)
out.append('\n## 特徴の年ごとの安定性 (北海道の値と他の 9 地方の範囲、年ごと)\n')
out.append('| 指標 | ' + ' | '.join(f'R{y - 2018}' for y in YEARS) + ' |')
out.append('|---|' + '|'.join('---:' for _ in YEARS) + '|')
fn = dict(METRICS)
for name, zv, rank in sorted(flags, key=lambda x: -abs(x[1])):
    cells = []
    for y in YEARS:
        per = {s: fn[name]([r for r in data[s] if r['year'] == y]) for s in SECTIONS}
        others = [per[s] for s in SECTIONS if s != 'A']
        cells.append(f'{fmt(name, per["A"])} ({fmt(name, min(others))}〜{fmt(name, max(others))})')
    out.append(f'| {name} | ' + ' | '.join(cells) + ' |')
out.append('')

(ROOT / 'reports/national').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/national/compare.md').write_text('\n'.join(out) + '\n')
print('wrote reports/national/compare.md')
