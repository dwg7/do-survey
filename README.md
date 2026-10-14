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
塗られる (6 段の順序尺度。セルに触れると件数と計画機関 (全部、件数の多い順))。ルートを選ぶと年度ごとの件数の概要。

## 北海道測量概況 (分析)

公共測量を観測窓に「北海道で何が行われているか」を読む試み。入口は **[reports/README.md](reports/README.md)** (レポートの案内、
レンズの癖、テーマ別の索引、後で修正した主張、検証の記録、再現の手順)。

- 結論を一覧で読む: [発見の台帳](reports/findings.md) (主な発見を 1 行ずつ、状態と根拠つき)
- 年度ごとに読む: [年度ごとの北海道測量概況](reports/yearly/README.md) (令和7年度から 1 年度ずつ、地勢と今年の天気の 2 層)
- 方法: [ハーネスは分析の質を上げるか](reports/meta/harness.md) (本文の数字の検査・発見の台帳・主張の再計算)

## データ

| ファイル | 内容 |
|---|---|
| `data/surveys.parquet` | GeoParquet 1.0.0 (zstd)。北海道 (区分 A) の測量 1 件 = 1 行、17,514 件。`geometry` は実施地域図 (EPSG:4326、2004 年度以降)、`muni_codes` は現在の市町村コードのリスト |
| `data/name-aliases.csv` | 旧町村名・札幌市の区名などを現在の市町村に読み替える表 (施行日と根拠付き) |
| `data/external/*.csv` | 分析で使う外部資料から抜き出した表 (開発局の当初・補正予算、道の当初予算・委託契約、住民基本台帳人口、都市計画基礎調査の対象と基準日)。各行に出典 URL |
| `analysis/*-rules.csv` | 発注主体・分野とねらい・段階の分類規則 (`scripts/classify.py` が使う) |

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
python3 scripts/classify.py # 分析の分類 analysis/classified.csv (派生物、コミットしない)
```

分析のレポートの作り直しと、外部資料・他の地方のデータの取得の手順は [reports/README.md](reports/README.md) の「再現」。
本文を書いたら `scripts/check_numbers.py`・`check_findings.py`・`verify_findings.py` を通す ([CLAUDE.md](CLAUDE.md) の「検査」)。

## 出典・ライセンス

- 出典: 国土地理院ウェブサイト「公共測量実施情報」 https://psgsv4.gsi.go.jp/giaSearch/
- `data/surveys.parquet` は上記を dwg7 が編集・加工して作成したもの (列の整理、日付・複数値の分割、
  市町村名の現在の市町村コードへの読み替え)。国土地理院が作成したものではない。
  国土地理院のコンテンツは公共データ利用規約 (第 1.0 版) で提供されている
  (https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)。
- 分析で使った他の資料 (`data/external/` の表とレポートは、いずれも dwg7 が抜き出し・加工したもの):
  - 北海道開発局「予算概要」(当初予算・補正予算) https://www.hkd.mlit.go.jp/ky/ki/keikaku/u23dsn0000000hh4.html
  - 北海道「予算の概要」https://www.pref.hokkaido.lg.jp/sm/zsi/95714.html
  - 北海道入札監視委員会「発注機関別入札・契約実績」https://www.pref.hokkaido.lg.jp/sm/gms/nyuusatu/nyusatukansiho-mupe-ji.html
  - 北海道「住民基本台帳人口・世帯数」https://www.pref.hokkaido.lg.jp/ss/tuk/900brr/index2.html
  - 北海道 都市計画基礎調査の業務処理要領 (令和7・8年度の入札公告) https://www.pref.hokkaido.lg.jp/kn/tki/docs/index.p2.html
- 市町村マスター・配置・描画コアは tabularmaps/do (CC0) を `docs/vendor/do/` に複製
  (複製元 tabularmaps/do@2439872、2026-09-20)。
- 規約は [CLAUDE.md](CLAUDE.md)、判断の経緯は [DECISIONS.md](DECISIONS.md)、作業の状態は [HANDOVER.md](HANDOVER.md)。
