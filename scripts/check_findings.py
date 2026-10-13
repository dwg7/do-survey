#!/usr/bin/env python3
"""発見の台帳 (reports/findings.csv) の検査と、読む用の一覧 reports/findings.md の生成 (D34)。

使い方: python3 scripts/check_findings.py

台帳は 1 行 1 発見。列: id, claim (主張), status, evidence (根拠のレポート), oracle (確かめた外部資料), years, decision (D 番号), superseded_by。
status:
  確認     外部資料 (oracle) か独立のデータで裏付けた
  集計     公共測量実施情報の集計で示した (外部の裏付けはない)
  推定     原因や意味の解釈。外部資料で確かめる必要がある (要確認)
  否定     後の分析で誤りと分かった
  置き換え 誤りではないが、後の発見がより正確に言い直した
検査: status の値、evidence のファイルの存在、decision の D 番号が DECISIONS.md にあること、superseded_by の id の存在、
置き換えには superseded_by が必須、確認には oracle が必須。失敗があれば終了コード 1。
"""
import collections
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATUS = ['確認', '集計', '推定', '否定', '置き換え']
rows = list(csv.DictReader((ROOT / 'reports/findings.csv').open()))
ids = {r['id'] for r in rows}
decisions = set(re.findall(r'^## (D\d+)', (ROOT / 'DECISIONS.md').read_text(), re.M))
errors = []
if len(ids) != len(rows):
    errors.append('id の重複')
for r in rows:
    i = r['id']
    if r['status'] not in STATUS:
        errors.append(f'{i}: status が不正 ({r["status"]})')
    if not (ROOT / r['evidence']).exists():
        errors.append(f'{i}: evidence がない ({r["evidence"]})')
    if r['decision'] and r['decision'] not in decisions:
        errors.append(f'{i}: decision が DECISIONS.md にない ({r["decision"]})')
    if r['superseded_by'] and r['superseded_by'] not in ids:
        errors.append(f'{i}: superseded_by の id がない ({r["superseded_by"]})')
    if r['status'] == '置き換え' and not r['superseded_by']:
        errors.append(f'{i}: 置き換えには superseded_by が要る')
    if r['status'] == '確認' and not r['oracle']:
        errors.append(f'{i}: 確認には oracle が要る')

by = collections.defaultdict(list)
for r in rows:
    by[r['status']].append(r)
out = ['# 発見の台帳\n',
       '`reports/findings.csv` から `scripts/check_findings.py` が生成。1 行 1 発見。状態の意味は台帳のスクリプトの冒頭。',
       '主張の言い回しは要約で、正確な内容は根拠のレポートにある。\n',
       '| 状態 | 件数 |', '|---|---:|'] + [f'| {s} | {len(by[s])} |' for s in STATUS]
for s in STATUS:
    if not by[s]:
        continue
    out.append(f'\n## {s}\n')
    out.append('| id | 主張 | 根拠 | 外部資料 | 年度 | 記録 | 置き換えた発見 |')
    out.append('|---|---|---|---|---|---|---|')
    for r in by[s]:
        ev = r['evidence'].replace('reports/', '')
        out.append(f'| {r["id"]} | {r["claim"]} | [{ev}]({ev}) | {r["oracle"] or "—"} | {r["years"]} | {r["decision"]} | {r["superseded_by"] or ""} |')
(ROOT / 'reports/findings.md').write_text('\n'.join(out) + '\n')
print(f'{len(rows)} 件 (' + '、'.join(f'{s} {len(by[s])}' for s in STATUS) + ')。reports/findings.md を書いた。')
for e in errors:
    print('  ' + e)
sys.exit(1 if errors else 0)
