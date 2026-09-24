# do-survey — 規約 (現在形)

「今なにが正しいか」だけを書く。経緯は `DECISIONS.md` (追記専用)、作業の状態と次の候補は `HANDOVER.md`、
列の定義と市町村名の読み替えは `SCHEMA.md`。

## 使命

国土地理院「公共測量実施情報」の北海道地方測量部 (区分 A) の実施情報を、市町村単位で一望できるようにする。
このリポジトリはその元データ (GeoParquet) を作り、ビューは 2 つを別々の機会に入れる:
市町村名のビュー = tabularmaps/do の Open MCT ダッシュボード、ポリゴンのビュー = bvmap-starlight の MapLibre GL JS。
将来は GeoParquet を Open MCT 経由でウェブから問い合わせられるようにする。

## データの流れ

1. `scripts/fetch.py`: `POST /giaSearch/RegionMapsSearch` を受付年度ごとにページ送り (200 件/ページ、1 秒間隔) で取得し、
   `data/raw/A-<年度>.json` に保存。CSV ダウンロードは使わない (1,000 件上限、ダイアログ)。公開サービスなので
   CI で定期再取得しない。手動で実行する。
2. `scripts/build.py`: 正規化して `data/surveys.parquet` (GeoParquet 1.0.0) と、ダッシュボード用の
   `docs/data/matrix.json` (受付年度 × 市町村の件数、計画機関別の内訳付き)・`docs/data/summary.json` を作る。
   冗長なキーは一致を assert してから捨てる。読み替えできない名前があっても止めず、`unresolved_names` に残す。

## コミットするもの

- する: `data/surveys.parquet`、`data/name-aliases.csv`、`scripts/`、`docs/` (ダッシュボードとその集計)、ドキュメント。
- しない: `data/raw/` (27MB、`fetch.py` で再現できる)。

## 市町村の照合

- tabularmaps/do の `municipalities.json` (`docs/vendor/do/data/` に複製) の 179 市町村 (`status: active`) の
  `fullName` で引く。根室振興局管内の 6 村は照合しない (「泊村」は後志の泊村 01403)。
- 旧町村名・札幌市の区名・表記ゆれは `data/name-aliases.csv` で読み替える。行を足す時は施行日と根拠
  (`source`) を必ず書き、`SCHEMA.md` の表も同じコミットで更新する。
- 北方領土の 6 村に触れる時は tabularmaps/do の `CLAUDE.md`「北方領土の 6 村の扱い」の表記に従う。

## 数え方

- 件数: 測量が関わった市町村それぞれに 1 件 (複数の市町村にまたがる測量は各市町村に 1 件)。按分はしない (D11)。
- 受付年度 (`year`) は 4 月〜翌 3 月。当年度は途中。

## ダッシュボード (docs/)

- `docs/survey-plugin.js` が Open MCT のツリーを作る。objects / composition / objectViews の provider だけを使い、
  Telemetry API は使わない。ルートは独自 type `dosurvey.root` (概要ビュー)、その下にリーフ `dosurvey.map` の
  「期間を選んで見る」(年度範囲のスライダー付き) と、組み込み `folder` の「年度別」→ 各年度 (新しい順)。
- 描画は `docs/vendor/do/tabularmap.js` の `TabularMap.create`。値は段階の番号 (順序尺度 6 段、区切りは選んだ年数で
  伸縮)。マウスオーバーは「件数」と「計画機関」(全部、件数の多い順) だけで、`survey-plugin.js` が描画コアのツールチップの中身を
  差し替える。区切りやツールチップを変えたら DECISIONS に書く。
- Open MCT は unpkg の 4.3.1 に固定 (tabularmaps/do と同じ)。`window.SharedWorker = undefined` を先に置く。
- ローカル確認は `.claude/launch.json` の `docs` (python http.server 8767)。ツリーは見えている分しか描かれないので、
  奥のリーフは URL `#/browse/dosurvey:root/dosurvey:map:range` や
  `#/browse/dosurvey:root/dosurvey:folder:years/dosurvey:map:year:<年度>` で開く。
- 画面に出典 (国土地理院) と、dwg7 が加工したことを必ず出す (概要ビューと各地図の注記)。

## 出典表記

公共データ利用規約 (第 1.0 版) に従い、「出典: 国土地理院ウェブサイト「公共測量実施情報」 (URL)」と、
dwg7 が編集・加工したことを併記する。加工したデータを国土地理院が作成したように見せない。

## tabularmaps/do の取り込み

`docs/vendor/do/` に複製する (submodule・実行時の直接読み込みはしない。dwg7/cafebabe `patterns/interoperability.md`)。
複製元のコミットを README に記録し、更新する時は同じコミットで書き換える。複製したファイルには手を入れない
(do の `openmct-plugin.js` は複製していない。ツリーは `survey-plugin.js` で作る)。

## 言語・コミット

会話は日本語 (敬語)。ドキュメント・コメントも日本語、識別子は英語。
コミットの author は `18297+hfu@users.noreply.github.com`。コミットメッセージは日本語。
