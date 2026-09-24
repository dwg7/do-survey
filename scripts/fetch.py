#!/usr/bin/env python3
"""国土地理院「公共測量実施情報」から、地方測量部区分 A (北海道地方測量部) の全件を受付年度ごとに取得する。

検索画面 (https://psgsv4.gsi.go.jp/giaSearch/) が使う POST /giaSearch/RegionMapsSearch をそのまま呼ぶ。
1 ページ最大 200 件 (それ以上を指定しても 200 に丸められる)。公開サービスなのでリクエスト間に間隔を置く。

出力: data/raw/A-<year>.json  ({"year", "section", "fetchedAt", "totalCount", "items": [...]})
"""
import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.request

BASE = 'https://psgsv4.gsi.go.jp/giaSearch'
PAGE_SIZE = 200
INTERVAL_S = 1.0
UA = 'do-survey/0.1 (Hokkaido public survey dashboard; python-urllib)'


def post(body):
    req = urllib.request.Request(
        BASE + '/RegionMapsSearch', data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'RequestVerificationToken': '', 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def get(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_year(year, section):
    items, page, total = [], 0, None
    while total is None or len(items) < total:
        d = post({
            'GeoJson': None, 'BufferKm': 0, 'SurveyTypeCodes': [], 'ScaleIds': [], 'PeriodFrom': None,
            'PeriodTo': None, 'PurposeValues': [], 'PrefIds': [], 'CityName': None, 'PlanOrgKeywords': [],
            'WorkerOrgKeywords': [], 'JyogenYear': str(year), 'JyogenSection': section, 'JyogenNos': [],
            'PageIndex': page, 'PageSize': PAGE_SIZE})
        total = d['totalCount']
        if not d['items']:
            break
        items.extend(d['items'])
        page += 1
        time.sleep(INTERVAL_S)
    if len(items) != total:
        raise SystemExit(f'{year}: got {len(items)} items but totalCount={total}')
    ids = [i['id'] for i in items]
    if len(set(ids)) != len(ids):
        raise SystemExit(f'{year}: duplicate ids across pages')
    return total, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', default='A')
    ap.add_argument('--years', nargs='*', type=int, help='既定はマスターにある全年度')
    ap.add_argument('--out', default='data/raw')
    a = ap.parse_args()
    years = a.years or sorted(int(y['value']) for y in get('/api/masters/jyogen-year') if y['value'])
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for y in years:
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        total, items = fetch_year(y, a.section)
        items.sort(key=lambda i: i['id'])
        (out / f'{a.section}-{y}.json').write_text(json.dumps(
            {'year': y, 'section': a.section, 'fetchedAt': fetched_at, 'totalCount': total, 'items': items},
            ensure_ascii=False, indent=0) + '\n')
        print(f'{y}: {total}', file=sys.stderr)


if __name__ == '__main__':
    main()
