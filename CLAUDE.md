# do-survey — 規約 (現在形)

「今なにが正しいか」だけを書く。経緯は `DECISIONS.md` (追記専用)、作業の状態と次の候補は `HANDOVER.md`、
列の定義と市町村名の読み替えは `SCHEMA.md`。

## 使命

国土地理院「公共測量実施情報」の北海道地方測量部 (区分 A) の実施情報を、市町村単位で一望できるようにする。
このリポジトリはその元データ (GeoParquet) を作り、ビューは 2 つを別々の機会に入れる:
市町村名のビュー = tabularmaps/do の Open MCT ダッシュボード、ポリゴンのビュー = bvmap-starlight の MapLibre GL JS。
将来は GeoParquet を Open MCT 経由でウェブから問い合わせられるようにする。
あわせて、公共測量を観測窓に「北海道で何が行われているか」を読む分析 (北海道測量概況) を `reports/` に書く (D16〜)。

## データの流れ

1. `scripts/fetch.py`: `POST /giaSearch/RegionMapsSearch` を受付年度ごとにページ送り (200 件/ページ、1 秒間隔) で取得し、
   `data/raw/A-<年度>.json` に保存。CSV ダウンロードは使わない (1,000 件上限、ダイアログ)。公開サービスなので
   CI で定期再取得しない。手動で実行する。
2. `scripts/build.py`: 正規化して `data/surveys.parquet` (GeoParquet 1.0.0) と、ダッシュボード用の
   `docs/data/matrix.json` (受付年度 × 市町村の件数、計画機関別の内訳付き)・`docs/data/summary.json` を作る。
   冗長なキーは一致を assert してから捨てる。読み替えできない名前があっても止めず、`unresolved_names` に残す。
3. 分析で使う外部の資料は、取得のスクリプトが `data/raw/` に原本を保存し、抜き出した表を `data/external/` (出典 URL 付き) に書く:
   開発局の当初予算 `fetch_budget.py`・補正予算 `fetch_budget_supp.py`、道の委託契約 `fetch_pref_contracts.py`。道の予算のポイント・
   住民基本台帳人口・都市計画基礎調査の業務処理要領は手で取得し、表に写した時は写した元を表に書く。外部サイトへの取得は 1 秒間隔。
4. 他の地方 (区分 B〜K) は `fetch.py --section <区分> --years ...` で `data/raw/<区分>-<年度>.json` に取る (GeoParquet にはしない)。
   計画機関の語で全国・全年度を引く時は、検索 API の `PlanOrgKeywords` に語を入れ、`JyogenYear`・`JyogenSection` を空にする (D33)。

## コミットするもの

- する: `data/surveys.parquet`、`data/name-aliases.csv`、`scripts/`、`docs/` (ダッシュボードとその集計)、`analysis/*-rules.csv`、
  `data/external/` (外部資料から抜き出した表、出典 URL 付き)、`reports/` (根拠表・本文・`checks.csv`・発見の台帳 `findings.csv`)、ドキュメント。
- しない: `data/raw/` (公共測量実施情報の JSON、予算・契約の PDF、人口の Excel、基礎調査の PDF、計画機関の語で引いた結果。取得のスクリプトか
  HANDOVER の手順で取り直せる)、`analysis/classified.csv` (`classify.py` の派生物)。

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
- Open MCT は unpkg の 4.3.1 に固定 (tabularmaps/do と同じ)。`window.SharedWorker = undefined` を先に置く。時刻は使わないが、時刻系 `utc` と固定モードを設定しておく (しないと起動時に落ちる、D47)。
- ローカル確認は `.claude/launch.json` の `docs` (python http.server 8767)。ツリーは見えている分しか描かれないので、
  奥のリーフは URL `#/browse/dosurvey:root/dosurvey:map:range` や
  `#/browse/dosurvey:root/dosurvey:folder:years/dosurvey:map:year:<年度>` で開く。
- 画面に出典 (国土地理院) と、dwg7 が加工したことを必ず出す (概要ビューと各地図の注記)。

## 分析 (北海道測量概況)

### 分類

- `scripts/classify.py` が `analysis/*-rules.csv` を上から順に当てて、発注主体 (planner)・分野とねらい (aim)・段階 (stage) を決める。
  ねらいは「計画機関 → 業務名 → 担当部署 (と計画機関名)」の順で最初に当たった規則。`section_pattern` のある規則は担当部署も当たる時だけ有効。
  結果の `analysis/classified.csv` は派生物でコミットしない。
- 規則の pattern は正規表現。CSV の列を割るので `{1,6}` のようなカンマを含む書き方は使わない (D35)。
- 決まらない案件 (`*-none`、classify.py が表示) は、計画機関 0 件。ねらい 1,237 件 (平成23年度以前の定型語がほとんどで、平成24年度以降は 28 件)、
  段階 3,450 件 (平成24年度以降 756 件)。ねらいと段階の「不明」は業務名から決められない案件として残す (D35 の時点の値、D41 でも同じ)。
- 規則を変えたら: 決まらない案件が増えていないこと、無作為抽出での読み合わせ、全スクリプトの流し直しと `git diff` での根拠表の変化の確認、
  下の検査をして、DECISIONS に書く。

### 根拠表

- 各レポートの数は、そのフォルダの根拠表 (`tables.md`・`compare.md` など、`scripts/` の生成物) から引く。本文に数の表を置く時も根拠表の値を写し、
  推移の表のような根拠表の写しでない表は、根拠表の生成に移す (stepping の C9、D35)。
- 年度ごとの概況 (`reports/yearly/<r07・h30 など>/`) の根拠表は `scripts/yearly_tables.py <受付年度>`。型は `reports/yearly/README.md` (D32)。
- 令和7年度の旧素案 `reports/archive/r07/draft.md` の根拠表は `scripts/r07_tables.py` (中身は `scripts/year_tables.py`、受付年度を引数に取る)。
  `year_tables.py` を変えたら `r07_tables.py` の出力が変わらないかを確かめ、変わるなら素案の数字も同じコミットで直す。

- 置き換わったレポートは `reports/archive/` に移す (本文は書いた時のまま、冒頭に置き換え先、検査は続ける、D40)。

### 書き方

- 長期の比較は平成21年度以降を土台にする (D17)。平成22年度は業務名がなく、事業の種類と段階は比べない。
- 件数は「測量の需要」であって事業の規模ではない。件数の増減を事業の増減として読むのは、100 億円あたりの件数 (密度) が安定している区間・分野だけ (D19)。
  道の届出は届出の運用で揺れる (D25)。開発局の件数は「当初 + 前年度の補正」と合わせて読む (D26)。
- 受付は契約の時点、工期は契約の窓、令和7年 4〜8 月は業務名の欠落がある、実施地域図の面積は作業範囲の外形、を前提として書く。
- 推定は推定と書き、外部資料で確かめることを「要確認」に残す。覆した主張は本文を直し、`reports/README.md` の「後のレポートで修正された主張」と台帳に残す。

### 検査 (D34・D35)

本文を書いたら、次の 3 つを通してからコミットする。

- `python3 scripts/check_numbers.py`: 本文 (各フォルダの `summary.md` と、column・longterm の本文。meta の振り返りと archive の旧素案は対象外) の 2 桁以上の数と小数が、同じフォルダの根拠表にあるか、`checks.csv` の
  式 (expr、使う数も根拠表にあること) か参照先 (ref) で裏付けられること。会話の中で問い合わせた数は、まず根拠表の生成に足す。
  限界: どの項目の数かまでは見ないので、手の照合も続ける。
- `python3 scripts/check_findings.py`: 発見の台帳 `reports/findings.csv` (1 行 1 発見、状態は 確認・集計・推定・否定・置き換え) の検査と
  `reports/findings.md` の生成。新しい発見は台帳に足し、覆した発見は「否定」か「置き換え」にして置き換えた発見を書く。
- `python3 scripts/verify_findings.py`: 台帳の主な主張を、根拠表とは別に書いた計算で元データから再現する。数量の主張を台帳に足したら、ここにも足す。

## 出典表記

公共データ利用規約 (第 1.0 版) に従い、「出典: 国土地理院ウェブサイト「公共測量実施情報」 (URL)」と、
dwg7 が編集・加工したことを併記する。加工したデータを国土地理院が作成したように見せない。
分析で使う他の資料 (北海道開発局「予算概要」、北海道「予算の概要」・北海道入札監視委員会の資料・「住民基本台帳人口・世帯数」・
都市計画基礎調査の業務処理要領) も、レポートと `data/external/` の表に出典を書き、dwg7 が抜き出し・加工したことを併記する。

## tabularmaps/do の取り込み

`docs/vendor/do/` に複製する (submodule・実行時の直接読み込みはしない。dwg7/cafebabe `patterns/interoperability.md`)。
複製元のコミットを README に記録し、更新する時は同じコミットで書き換える。複製したファイルには手を入れない
(do の `openmct-plugin.js` は複製していない。ツリーは `survey-plugin.js` で作る)。

## 言語・コミット

会話は日本語 (敬語)。ドキュメント・コメントも日本語、識別子は英語。
コミットの author は `18297+hfu@users.noreply.github.com`。コミットメッセージは日本語。
