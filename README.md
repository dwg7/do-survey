# do-survey — 北海道の公共測量はどこで行われたか

国土地理院「公共測量実施情報」のうち、地方測量部区分 A (北海道地方測量部) の全件 (受付年度 1983〜) を
GeoParquet にまとめる。これを元に、「測量地域 市区町村」を [tabularmaps/do](https://github.com/tabularmaps/do) の
16×16 表形式地図で見る Open MCT ダッシュボードと、実施地域図のポリゴンを MapLibre GL JS で見るビューを作る (作業中)。

## ダッシュボード

公開版: https://dwg7.unopengis.org/do-survey/ (GitHub Pages: main の /docs)

```bash
python3 -m http.server 8767 --directory docs   # http://localhost:8767/
```

左のツリー「北海道の公共測量」を開き、「期間を選んで見る」でスライダーの 2 つのつまみで年度の範囲を選ぶか、
「年度別」から年度を選ぶと、市町村ごとの件数で [tabularmaps/do](https://github.com/tabularmaps/do) の 16×16 表形式地図が
塗られる (6 段の順序尺度。セルに触れると件数と主な計画機関)。ルートを選ぶと年度ごとの件数の概要。

## 北海道測量概況 (分析)

公共測量を観測窓に「北海道で何が行われているか」を読む試み。
[令和7年度 北海道測量概況 (改訂版) 素案](reports/r07/draft.md) と [根拠表](reports/r07/tables.md)。
長期の変化が取れるかの見積もりは [reports/longterm/estimate.md](reports/longterm/estimate.md)、
平成22・27年度、令和2・7年度の飛び石の比較は [reports/stepping/summary.md](reports/stepping/summary.md)、
事業費 (北海道開発局関係予算) との突き合わせは [reports/budget/summary.md](reports/budget/summary.md)、
単年度の概況の自然文と情報量の評価は [reports/annual/summary.md](reports/annual/summary.md)、
北海道の「地勢」を他の地方と比べたものは [reports/national/summary.md](reports/national/summary.md)、
測量期間 (工期) の分析は [reports/term/summary.md](reports/term/summary.md)。

```bash
python3 scripts/classify.py     # 発注主体・分野・ねらい (行政目的 6 分類)・段階に分類 → analysis/classified.csv
python3 scripts/r07_tables.py   # 根拠表 reports/r07/tables.md
python3 scripts/longterm_tables.py   # 長期の飛び石 reports/longterm/tables.md
python3 scripts/year_tables.py 2010 reports/h22/tables.md   # 任意の年度の根拠表 (r07_tables.py は 2025 の版)
python3 scripts/stepping_compare.py  # 飛び石の比較 reports/stepping/compare.md
python3 scripts/fetch_budget.py      # 開発局の当初予算 → data/external/hkd-budget-initial.csv (PDF は data/raw/budget/)
python3 scripts/budget_compare.py    # 件数と事業費 reports/budget/compare.md
python3 scripts/annual_overview.py   # 単年度の概況 reports/annual/overviews.md と情報量 reports/annual/skill.md
for s in B C D E F G H I J K; do python3 scripts/fetch.py --section $s --years 2023 2024 2025; done   # 他の地方
python3 scripts/national_compare.py  # 地方の比較 reports/national/compare.md
python3 scripts/term_analysis.py     # 工期の分析 reports/term/tables.md
```

分類の規則は `analysis/planner-rules.csv`・`analysis/aim-rules.csv`・`analysis/stage-rules.csv` (DECISIONS.md D16)。

## データ

| ファイル | 内容 |
|---|---|
| `data/surveys.parquet` | GeoParquet 1.0.0 (zstd)。測量 1 件 = 1 行、17,514 件。`geometry` は実施地域図 (EPSG:4326、2004 年度以降)、`muni_codes` は現在の市町村コードのリスト |
| `data/name-aliases.csv` | 旧町村名・札幌市の区名などを現在の市町村に読み替える表 (施行日と根拠付き) |

列の定義、CSV・API の項目との対応、読み替えの規則は [SCHEMA.md](SCHEMA.md)。

```sql
-- duckdb: 受付年度 2019〜 に件数の多い市町村
LOAD spatial;
SELECT code, count(*) AS n
FROM (SELECT unnest(muni_codes) AS code FROM 'data/surveys.parquet' WHERE year >= 2019)
GROUP BY code ORDER BY n DESC LIMIT 10;
```

件数は、測量が関わった市町村それぞれに 1 件と数える (複数の市町村にまたがる測量は各市町村に 1 件。DECISIONS.md D11)。

## 作り直す

```bash
python3 scripts/fetch.py    # data/raw/A-<受付年度>.json を取得 (全年度、1 秒間隔、数分)。data/raw/ はコミットしない
python3 scripts/build.py    # data/surveys.parquet と docs/data/ の集計を作る (duckdb CLI の spatial 拡張を使う)
```

## 出典・ライセンス

- 事業費: 北海道開発局「予算概要」https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4.html (各年度の当初予算の PDF から dwg7 が抜き出し)

- 出典: 国土地理院ウェブサイト「公共測量実施情報」 https://psgsv4.gsi.go.jp/giaSearch/
- `data/surveys.parquet` は上記を dwg7 が編集・加工して作成したもの (列の整理、日付・複数値の分割、
  市町村名の現在の市町村コードへの読み替え)。国土地理院が作成したものではない。
  国土地理院のコンテンツは公共データ利用規約 (第 1.0 版) で提供されている
  (https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)。
- 市町村マスター・配置・描画コアは tabularmaps/do (CC0) を `docs/vendor/do/` に複製
  (複製元 tabularmaps/do@2439872、2026-09-20)。
- 判断の経緯は [DECISIONS.md](DECISIONS.md)、作業の状態は [HANDOVER.md](HANDOVER.md)。
