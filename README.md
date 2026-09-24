# do-survey — 北海道の公共測量はどこで行われたか

国土地理院「公共測量実施情報」のうち、地方測量部区分 A (北海道地方測量部) の全件 (受付年度 1983〜) を
GeoParquet にまとめる。これを元に、「測量地域 市区町村」を [tabularmaps/do](https://github.com/tabularmaps/do) の
16×16 表形式地図で見る Open MCT ダッシュボードと、実施地域図のポリゴンを MapLibre GL JS で見るビューを作る (作業中)。

## ダッシュボード

公開版: https://dwg7.github.io/do-survey/ (GitHub Pages: main の /docs)

```bash
python3 -m http.server 8767 --directory docs   # http://localhost:8767/
```

左のツリー「北海道の公共測量」を開き、「関与件数」「按分件数」から令和・全期間・各年度を選ぶと、
市町村ごとの件数で [tabularmaps/do](https://github.com/tabularmaps/do) の 16×16 表形式地図が塗られる
(6 段の順序尺度。セルに触れると正確な件数と主な計画機関)。ルートを選ぶと年度ごとの件数の概要。

## データ

| ファイル | 内容 |
|---|---|
| `data/surveys.parquet` | GeoParquet 1.0.0 (zstd)。測量 1 件 = 1 行、17,514 件。`geometry` は実施地域図 (EPSG:4326、2004 年度以降)、`muni_codes` は現在の市町村コードのリスト |
| `data/name-aliases.csv` | 旧町村名・札幌市の区名などを現在の市町村に読み替える表 (施行日と根拠付き) |

列の定義、CSV・API の項目との対応、読み替えの規則は [SCHEMA.md](SCHEMA.md)。

```sql
-- duckdb: 令和 (受付年度 2019〜) に関与件数の多い市町村
LOAD spatial;
SELECT code, count(*) AS n
FROM (SELECT unnest(muni_codes) AS code FROM 'data/surveys.parquet' WHERE year >= 2019)
GROUP BY code ORDER BY n DESC LIMIT 10;
```

複数の市町村にまたがる測量は、関与した各市町村に 1 件ずつ数える「関与件数」を主、1/関与市町村数ずつ按分する
「按分件数」を補助とする (DECISIONS.md D3)。

## 作り直す

```bash
python3 scripts/fetch.py    # data/raw/A-<受付年度>.json を取得 (全年度、1 秒間隔、数分)。data/raw/ はコミットしない
python3 scripts/build.py    # data/surveys.parquet と docs/data/ の集計を作る (duckdb CLI の spatial 拡張を使う)
```

## 出典・ライセンス

- 出典: 国土地理院ウェブサイト「公共測量実施情報」 https://psgsv4.gsi.go.jp/giaSearch/
- `data/surveys.parquet` は上記を dwg7 が編集・加工して作成したもの (列の整理、日付・複数値の分割、
  市町村名の現在の市町村コードへの読み替え)。国土地理院が作成したものではない。
  国土地理院のコンテンツは公共データ利用規約 (第 1.0 版) で提供されている
  (https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)。
- 市町村マスター・配置・描画コアは tabularmaps/do (CC0) を `docs/vendor/do/` に複製
  (複製元 tabularmaps/do@2439872、2026-09-20)。
- 判断の経緯は [DECISIONS.md](DECISIONS.md)、作業の状態は [HANDOVER.md](HANDOVER.md)。
