#!/usr/bin/env python3
"""公共測量を「発注主体」「分野」「ねらい (行政目的 6 分類)」「段階」に分類する (D16)。

入力: data/surveys.parquet (duckdb CLI で必要な列だけ書き出して読む)
規則: analysis/planner-rules.csv (発注主体)、analysis/aim-rules.csv (分野・ねらい)、analysis/stage-rules.csv (段階)
出力: analysis/classified.csv (全年度の 1 件 = 1 行。どの規則で決まったかを残す)

ねらいの規則は「計画機関 → 業務名 (目的) → 担当部署」の順に当て、最初に当たったものを採る。
section_pattern がある規則は、担当部署 (と計画機関名) もその正規表現に当たる時だけ有効。
"""
import csv
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
A = ROOT / 'analysis'
FIRST_YEAR = 1983   # 全年度。令和7年度の根拠表 (r07_tables.py) は 2019〜2025 だけを読む
MUNIS = ROOT / 'docs/vendor/do/data/municipalities.json'
# 北海道の外にある実施地域図 (DECISIONS.md D5) は面積・重心に使わない
HOKKAIDO_BBOX = (139.3, 41.3, 146.0, 45.6)


def export_rows():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / 'rows.json'
        x0, y0, x1, y1 = HOKKAIDO_BBOX
        sql = f"""
LOAD spatial;
SET geometry_always_xy = true;
COPY (
  SELECT survey_id, year, recept_date, planner, charge_section, purpose, contents_types, muni_codes, area_city_name,
         CASE WHEN geometry IS NOT NULL AND ST_XMin(geometry) >= {x0} AND ST_YMin(geometry) >= {y0}
                   AND ST_XMax(geometry) <= {x1} AND ST_YMax(geometry) <= {y1}
              THEN ST_Area_Spheroid(geometry) END AS area_m2
  FROM 'data/surveys.parquet' WHERE year >= {FIRST_YEAR}
) TO '{out}' (FORMAT json);
"""
        subprocess.run(['duckdb', '-c', sql], check=True, cwd=ROOT)
        return [json.loads(line) for line in out.read_text().splitlines() if line.strip()]


def load_rules(name):
    rules = list(csv.DictReader((A / name).open()))
    for r in rules:
        r['re'] = re.compile(r['pattern'])
        r['sre'] = re.compile(r['section_pattern']) if r.get('section_pattern') else None
    return rules


def planner_type(planner, rules, muni_names):
    for r in rules:
        if r['re'].search(planner):
            return r['type'], r['subtype'], r['id']
    name = re.sub(r'^北海道', '', planner)
    for m in muni_names:
        if name.startswith(m):
            return '市町村', m, 'P-muni'
    return 'その他', '分類保留', 'P-none'


def aim_of(row, rules):
    # 担当部署が空や略記の時のため、計画機関名 (「…開発建設部岩見沢農業事務所」など) も担当部署の手がかりに含める
    section = (row['charge_section'] or '') + ' ' + (row['planner'] or '')
    texts = {'planner': row['planner'] or '', 'purpose': row['purpose'] or '', 'section': section}
    for target in ('planner', 'purpose', 'section'):
        for r in rules:
            if r['target'] != target or not r['re'].search(texts[target]):
                continue
            if r['sre'] and not r['sre'].search(texts['section']):
                continue
            return r['field'], r['aim'], r['id']
    return '不明', '不明', 'R-none'


def stage_of(row, rules):
    kinds = '|'.join(row['contents_types'] or [])
    for r in rules:
        text = (row['purpose'] or '') if r['target'] == 'purpose' else kinds
        if r['re'].search(text):
            return r['stage'], r['id']
    return '不明', 'S-none'


def main():
    munis = json.loads(MUNIS.read_text())['municipalities']
    bureau = {m['code']: m['bureau'] for m in munis}
    # 長い名前から当てる (「北広島市」より先に「北」で始まる短い名前に当たらないように)
    muni_names = sorted({m['fullName'] for m in munis if m['status'] == 'active'}, key=len, reverse=True)
    prules, arules, srules = load_rules('planner-rules.csv'), load_rules('aim-rules.csv'), load_rules('stage-rules.csv')
    out = []
    for row in export_rows():
        ptype, psub, pid = planner_type(row['planner'] or '', prules, muni_names)
        field, aim, aid = aim_of(row, arules)
        stage, sid = stage_of(row, srules)
        codes = row['muni_codes'] or []
        bureaus = sorted({bureau[c] for c in codes})
        month = int(row['recept_date'][5:7]) if row['recept_date'] else None
        out.append({
            'survey_id': row['survey_id'], 'year': row['year'], 'recept_date': row['recept_date'],
            'half': ('上期' if 4 <= month <= 9 else '下期') if month else '',
            'planner': row['planner'], 'planner_type': ptype, 'planner_sub': psub, 'planner_rule': pid,
            'field': field, 'aim': aim, 'aim_rule': aid, 'stage': stage, 'stage_rule': sid,
            'muni_codes': ' '.join(codes), 'bureaus': ' '.join(bureaus), 'n_munis': len(codes), 'n_bureaus': len(bureaus),
            'area_km2': round(row['area_m2'] / 1e6, 4) if row['area_m2'] else '',
            'purpose': row['purpose'], 'charge_section': row['charge_section'],
            'kinds': '|'.join(row['contents_types'] or []),
        })
    with (A / 'classified.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    n = len(out)
    for key in ('planner_rule', 'aim_rule', 'stage_rule'):
        miss = sum(1 for r in out if r[key].endswith('-none'))
        print(f'{key}: unmatched {miss}/{n}', file=sys.stderr)


if __name__ == '__main__':
    main()
