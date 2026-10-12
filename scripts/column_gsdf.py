#!/usr/bin/env python3
"""コラム: 陸上自衛隊の地理情報隊の公共測量 (全国) の根拠表 (D33)。

入力: data/raw/gsdf/planner-search.json (国土地理院「公共測量実施情報」の検索 API を、年度・区分を指定せず、計画機関のキーワード
      「地理情報隊」「中央情報隊」「自衛隊」「地理隊」「情報隊」で引いた結果の和。2026-10-13 取得、コミットしない)
      data/raw/[A-J]-2023〜2025.json (作業者の比較)
出力: reports/column/gsdf-tables.md
"""
import collections
import glob
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
items = json.loads((ROOT / 'data/raw/gsdf/planner-search.json').read_text())['items']
SEC = {'道公': '北海道', '東公': '東北', '関公': '関東', '北公': '北陸', '部公': '中部', '近公': '近畿', '中公': '中国', '四公': '四国',
       '九公': '九州', '沖公': '沖縄'}


def clean(s):
    return (s or '').replace('</br>', ' / ').replace('　', ' ').strip(' /')


out = ['# コラム: 地理情報隊の公共測量 — 根拠表\n',
       '`scripts/column_gsdf.py` が生成。国土地理院「公共測量実施情報」の検索 API を、年度と地方測量部を指定せず、計画機関の語'
       '「地理情報隊」「中央情報隊」「自衛隊」「地理隊」「情報隊」で引いた結果 (重複を除く) を dwg7 が編集・加工 (2026-10-13 取得)。\n']
out.append('## G1. 計画機関の語ごとの件数\n')
kw = collections.Counter()
for it in items:
    p = it['plannerName'] or ''
    kw['地理情報隊' if '地理情報隊' in p else '中央情報隊 (地理情報隊の語なし)' if '中央情報隊' in p else 'その他の自衛隊'] += 1
out.append(' / '.join(f'{k} {v}' for k, v in kw.items()) + f' (計 {len(items)} 件)\n')

out.append('## G2. 全件 (受付年度・受付日の順)\n')
out.append('| 受付年度 | 受付日 | 地方測量部 | 計画機関 | 目的 | 測量地域 | 測量の種類 | 等級・縮尺 | 数量 | 測量期間 | 作業者 |')
out.append('|---:|---|---|---|---|---|---|---|---|---|---|')
for it in sorted(items, key=lambda i: (i['yearRecept'], i['dateReceptYmd'])):
    out.append(f'| {it["yearRecept"]} | {it["dateReceptYmd"]} | {SEC.get(it["jogenSection"], it["jogenSection"])} | {clean(it["plannerName"])} | '
               f'{clean(it["purpose"])} | {clean(it["areaPref"])} {clean(it["areaCityName"])} | {clean(it["contentsType"]).replace("【大分類】 ", "")} | '
               f'{clean(it["contentsRankName"])} | {clean(it["pointsAreaDistance"])} | {clean(it["term"]).replace(" / ", "〜")} | {clean(it["workerName"])} |')

# 作業者が計画機関自身 (直営) の測量は全国でどれだけあるか
tot, self_ = 0, collections.Counter()
for f in glob.glob(str(ROOT / 'data/raw/[A-J]-202[345].json')):
    for it in json.loads(pathlib.Path(f).read_text())['items']:
        tot += 1
        w, p = clean(it['workerName']), clean(it['plannerName'])
        if '直営' in w or (w and w.replace(' ', '') in p.replace(' ', '')):
            self_[p] += 1
out.append(f'\n## G3. 作業者が計画機関自身 (「直営」または同じ名前) の測量 — 全国 (区分 A〜J)、令和5〜7年度\n')
out.append(f'全 {tot:,} 件のうち {sum(self_.values())} 件。計画機関: ' + '、'.join(f'{p} {n}' for p, n in self_.most_common()) + '。\n')

out.append('## G4. 防衛省の地方防衛局 (参考) — 手元のデータ (北海道は全年度、他の地方は平成21・26年度、令和元・5〜7年度)\n')
dc = collections.Counter()
for f in glob.glob(str(ROOT / 'data/raw/[A-J]-*.json')):
    for it in json.loads(pathlib.Path(f).read_text())['items']:
        p = clean(it['plannerName'])
        if '防衛局' in p or '防衛支局' in p:
            dc[(pathlib.Path(f).stem[0], it['yearRecept'])] += 1
yrs = sorted({y for _, y in dc if y >= 2009})
out.append('| 地方 | ' + ' | '.join(str(y) for y in yrs) + ' |')
out.append('|---|' + '---:|' * len(yrs))
for s in 'ABCDEFGHIJ':
    out.append(f'| {s} | ' + ' | '.join(str(dc[(s, y)]) for y in yrs) + ' |')
out.append('\n地方防衛局 (防衛省の地方の機関) は基地・演習場の用地・境界・移転措置の測量を外部に委託して出す。地理情報隊とは別の機関。\n')
(ROOT / 'reports/column').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/column/gsdf-tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/column/gsdf-tables.md')
