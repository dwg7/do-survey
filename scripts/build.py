#!/usr/bin/env python3
"""data/raw/A-<year>.json (scripts/fetch.py の出力) を正規化し、GeoParquet とダッシュボード用の集計を作る。

全年度 (受付年度 1983〜) を対象とする。「測量地域 市区町村」の名前は tabularmaps/do の 179 市町村の正式名称で
引き、合併前の旧町村名・札幌市の区名などは data/name-aliases.csv で現在の市町村に読み替える (D6)。
どちらでも引けない名前 (例: 「北海道」) は unresolved_names に残し、市町村には数えない。

出力:
  data/surveys.parquet               GeoParquet。測量 1 件 = 1 行 (geometry は実施地域図のポリゴン、EPSG:4326)
  docs/data/matrix.json              ダッシュボード用の受付年度 × 市町村の関与件数 (計画機関別の内訳付き)
  docs/data/summary.json             年度ごとの件数など

変換に duckdb CLI (spatial 拡張) を使う。
"""
import collections
import csv
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALIASES = ROOT / 'data/name-aliases.csv'
MUNIS = ROOT / 'docs/vendor/do/data/municipalities.json'


def load_name_index():
    """正式名称 → コード。179 市町村 (status: active) だけを引く。

    根室振興局管内の 6 村 (北方領土) は市町村としての行政の実態がなく、公共測量の実施実績もないため
    照合対象にしない。これにより「泊村」は後志の泊村 (01403) に一意に決まる (D4)。
    """
    idx = {}
    for m in json.loads(MUNIS.read_text())['municipalities']:
        if m['status'] != 'active':
            continue
        if m['fullName'] in idx:
            raise SystemExit(f'duplicate fullName among active: {m["fullName"]}')
        idx[m['fullName']] = m['code']
    for a in csv.DictReader(ALIASES.open()):
        if a['alias'] in idx:
            raise SystemExit(f'alias shadows a current name: {a["alias"]}')
        idx[a['alias']] = idx[a['current']]
    return idx


def split_br(s):
    """複数の値は '</br>' 区切りで 1 つの文字列に入っている。空要素は落とす。"""
    return [x.strip() for x in (s or '').split('</br>') if x.strip()]


def to_date(s):
    """'YYYY/MM/DD' → 'YYYY-MM-DD'。未記入 ('--/--/--' など) は None。"""
    return s.replace('/', '-') if re.fullmatch(r'\d{4}/\d{2}/\d{2}', s or '') else None


def split_cities(s):
    return [c.strip() for c in re.split(r'[,、，]', s or '') if c.strip()]


def main():
    idx = load_name_index()
    rows, links, unresolved = [], [], collections.Counter()
    for f in sorted((ROOT / 'data/raw').glob('A-*.json')):
        d = json.loads(f.read_text())
        for it in d['items']:
            names = split_cities(it['areaCityName'])
            # 旧町村名と現在名が並ぶ時 (例: 「南区,札幌市」) は同じ市町村に重なるので 1 つにまとめる
            codes, missing = [], []
            for n in names:
                c = idx.get(n)
                if c is None:
                    missing.append(n)
                    unresolved[n] += 1
                elif c not in codes:
                    codes.append(c)
            for c in codes:
                links.append({'survey_id': it['id'], 'muni_code': c, 'year': d['year']})
            term = split_br(it['term'])
            # 冗長なキーは一致を確かめてから捨てる (SCHEMA.md「取り込まないキー」)
            assert it['yearRecept'] == d['year'] and it['jogenID'] == it['articleID']
            assert it['jogenRecept'] == it['dateReceptYmd']
            assert it['name'] == f"{it['jogenNo']} {it['plannerName']}"
            rows.append({
                'survey_id': it['id'],
                'jogen_no': it['jogenNo'],
                'jogen_section': it['jogenSection'],
                'jogen_serial': int(it['jogenID']),
                'year': it['yearRecept'],
                'section': it['articleSectionCode'],
                'recept_date': to_date(it['dateReceptYmd']),
                'planner': it['plannerName'],
                'charge_section': it['chargeSection'],
                'purpose': it['purpose'],
                'area_pref': it['areaPref'],
                'area_city_name': it['areaCityName'],
                'area_city_names': names,
                'muni_codes': codes,
                'unresolved_names': missing,
                'term_from': to_date(term[0]),
                'term_to': to_date(term[1]) if len(term) > 1 else None,
                'contents_types': split_br(it['contentsType']),
                'contents_ranks': split_br(it['contentsRankName']),
                'contents_amounts': split_br(it['pointsAreaDistance']),
                'worker': it['workerName'],
                'worker_code': it['workerCode'],
                'status': it['newStatus'],
                'region_source_pkey': it['regionSourcePkey'],
                'region_url': (it['dirPath'] + it['docName']) if it.get('docName') else None,
                'public_result_links': re.findall(r'>([^<>]+)</a>', it['publicResultHtml'] or ''),
                'geom': it['geom'],
                'fetched_at': d['fetchedAt'],
            })
    with tempfile.TemporaryDirectory() as tmp:
        nd = pathlib.Path(tmp) / 'surveys.ndjson'
        nd.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        out = ROOT / 'data/surveys.parquet'
        sql = f"""
INSTALL spatial; LOAD spatial;
CREATE TABLE s AS SELECT * FROM read_json('{nd}', format='newline_delimited', columns={{
  survey_id: 'BIGINT', jogen_no: 'VARCHAR', jogen_section: 'VARCHAR', jogen_serial: 'INTEGER', year: 'INTEGER',
  section: 'VARCHAR', recept_date: 'DATE', planner: 'VARCHAR', charge_section: 'VARCHAR', purpose: 'VARCHAR',
  area_pref: 'VARCHAR', area_city_name: 'VARCHAR', area_city_names: 'VARCHAR[]', muni_codes: 'VARCHAR[]',
  unresolved_names: 'VARCHAR[]', term_from: 'DATE', term_to: 'DATE', contents_types: 'VARCHAR[]',
  contents_ranks: 'VARCHAR[]', contents_amounts: 'VARCHAR[]', worker: 'VARCHAR', worker_code: 'VARCHAR',
  status: 'VARCHAR', region_source_pkey: 'BIGINT', region_url: 'VARCHAR', public_result_links: 'VARCHAR[]',
  geom: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'}});
COPY (
  SELECT * EXCLUDE (geom),
         CASE WHEN geom IS NULL OR geom = '' THEN NULL ELSE ST_GeomFromGeoJSON(geom) END AS geometry
  FROM s ORDER BY year, survey_id
) TO '{out}' (FORMAT parquet, COMPRESSION zstd);
"""
        subprocess.run(['duckdb', '-c', sql], check=True)

    write_dashboard_data(rows, links, unresolved)
    print(f'surveys={len(rows)} links={len(links)} unresolved={dict(unresolved)}', file=sys.stderr)


def write_dashboard_data(rows, links, unresolved):
    """docs/data/ にダッシュボード用の集計を書く (D10, D11)。

    matrix.json: 受付年度 × 市町村の関与件数と、年度 × 市町村 × 計画機関の件数。
      ブラウザ側で任意の年度範囲を合算する (期間スライダー)。
    summary.json: 年度ごとの測量件数など。
    """
    by_id = {r['survey_id']: r for r in rows}
    years = list(range(min(r['year'] for r in rows), max(r['year'] for r in rows) + 1))
    yi = {y: i for i, y in enumerate(years)}
    counts = collections.defaultdict(lambda: [0] * len(years))
    cp = collections.Counter()
    for l in links:
        counts[l['muni_code']][yi[l['year']]] += 1
        cp[(l['muni_code'], yi[l['year']], by_id[l['survey_id']]['planner'])] += 1
    planners = sorted({k[2] for k in cp})
    pi = {p: i for i, p in enumerate(planners)}
    by_code = collections.defaultdict(list)
    for (code, y, p), n in sorted(cp.items()):
        by_code[code].append([y, pi[p], n])
    data = ROOT / 'docs/data'
    data.mkdir(parents=True, exist_ok=True)
    (data / 'matrix.json').write_text(json.dumps({
        'years': years,
        'involved': dict(sorted(counts.items())),
        'planners': planners,
        'plannerCounts': dict(sorted(by_code.items())),
    }, ensure_ascii=False, separators=(',', ':')) + '\n')
    per_year = collections.Counter(r['year'] for r in rows)
    geo_year = collections.Counter(r['year'] for r in rows if r['geom'])
    (data / 'summary.json').write_text(json.dumps({
        'source': '国土地理院「公共測量実施情報」',
        'sourceUrl': 'https://psgsv4.gsi.go.jp/giaSearch/',
        'section': 'A 北海道地方測量部',
        'fetchedAt': max(r['fetched_at'] for r in rows),
        'lastReceptDate': max(r['recept_date'] for r in rows if r['recept_date']),
        'years': [{'year': y, 'surveys': per_year[y], 'withRegion': geo_year[y]} for y in years],
        'unresolved': dict(unresolved.most_common()),
    }, ensure_ascii=False, indent=1) + '\n')
    shutil.rmtree(data / 'series', ignore_errors=True)   # D10 の旧形式 (期間ごとのファイル)


if __name__ == '__main__':
    main()
