# HANDOVER.md — 引き継ぎ (2026-10-16 時点)

規約は `CLAUDE.md`、経緯は `DECISIONS.md` (D1〜D48)、列と読み替えは `SCHEMA.md`、レポートの案内は `reports/README.md`。
このファイルは「今どこまで進んでいて、次に何をするか」と、ファイルに書いていない作業の型だけを書く (都度まるごと書き直す)。

## 今の段階

**年度ごとの北海道測量概況 (D32) を、令和7年度から平成21年度まで 17 年度すべて書き終えた** (`reports/yearly/`、D37・D38)。
平成21〜25年度は、平年に平成20年度以前が入るので、Y1 に後の 5 年度との比較を足して読んだ (D38)。その過程で annual の読みを 3 つ直した。
続けて、17 年度の出来事の表と全期間の長期概況を書いた (`reports/overview/`、D39)。2026-10-21 に reports/ 全体を独立したレビュアー 4 人で確かめ、指摘を直した (D41、`reports/README.md` の「検証の記録」)。次は hfu の判断を待つ。候補は下の「次の候補」。
年度ごとの概況の仕分けを変えたら、`reports/overview/events.csv` も直して `python3 scripts/overview_tables.py` を流す (集合が合わないと止まる)。

年度ごとの概況を書き直す・足す時の手順 (1 年度ごと):

1. `python3 scripts/yearly_tables.py <受付年度>` で根拠表を作る (`reports/yearly/h25/tables.md` など)。
2. 予想外 (Y1) を中身で読み、Y7 の内訳と、必要なら元データへの問い合わせで原因を探す。問い合わせた数は、本文に使う前に `yearly_tables.py` に足す。
3. `summary.md` を型 (`reports/yearly/README.md`) どおりに書く。足し算などは `checks.csv`。
4. `check_numbers.py`・`check_findings.py`・`verify_findings.py` を通し、本文の主張を根拠表と手で照合する。新しい発見は台帳と `verify_findings.py` に足す。
5. `reports/yearly/README.md` の一覧を直して、コミットと push。

## 現在の状態

- データ: `data/surveys.parquet` (受付年度 1983〜2026 の 17,583 件、2026 年度は 2026-10-21 に取り直して 10/15 受付分まで。それ以前の年度は 2026-09-24 取得)。
- ダッシュボード: https://dwg7.unopengis.org/do-survey/ (GitHub Pages、main の /docs)。D10〜D15。
- 分析: `reports/` のレポート 16 本 (D16〜D31・D39。うち 2 本は `reports/archive/` に移した、D40)、年度ごとの概況 17 年度 (D32・D37・D38)、コラム 1 本 (D33)、方法の振り返り (D34)、発見の台帳 82 件、長期概況 (D39)。
  2026-10-13 に全体を検証し直した (D35、`reports/README.md` の「検証の記録」)。2026-10-14 にドキュメントを整合させた (D36)。2026-10-16 に平成28〜21年度を書いた (D37・D38)。
- 検査: 本文の数字 (`check_numbers.py`)、台帳 (`check_findings.py`)、主張の再計算 (`verify_findings.py`、50 項目) が通る状態。
- 手元にだけあるデータ (`data/raw/`、コミットしない):
  - 区分 A (北海道) の全年度 `A-1968.json`〜`A-2026.json` — `scripts/fetch.py`
  - 区分 B〜K の 2009・2014・2019・2023・2024・2025 年度 (K は 2023〜2025 のみ) — `fetch.py --section`
  - 開発局の当初予算の PDF `budget/t*.pdf` — `fetch_budget.py`、補正予算の PDF `budget/hosei/` — `fetch_budget_supp.py`
  - 道の入札監視委員会の資料 1-1 `budget/pref/nyusatsu-*.pdf` — `fetch_pref_contracts.py`。道の予算のポイント `budget/pref/r*-point.pdf` は手で取得
    (北海道「予算の概要」の各年度のページ)
  - 道の住民基本台帳人口 `population/jumin-2026.xlsx` — 北海道統計課のページから手で取得 (読むのは `scripts/xlsx_rows.py`)
  - 都市計画基礎調査の業務処理要領 `cityplan/*.pdf` — 道の都市計画課の入札公告 (令和7・8年度) から手で取得
  - 計画機関の語で引いた結果 `gsdf/planner-search.json`・`gsdf/defense-bureau-search.json` — 検索 API (D33 の手順)
- `analysis/classified.csv` も派生物でコミットしない (`python3 scripts/classify.py`、数十秒)。

## 作業の型 (ファイルに書いていない約束ごと)

- **数字は書く前に根拠表と照合し、書いた後に検査と手の照合をする。** 検査は「どの項目の数か」までは見ない (平成30年度の「続く空白 7」は手で見つけた)。
- **前の主張を後の分析で覆したら**、本文を直し、`reports/README.md` の「後のレポートで修正された主張」と台帳 (否定・置き換え) に残す。
  DECISIONS は追記専用なので、古い D の本文は書き換えず、新しい D に書く。
- **分類規則を変えたら**: CLAUDE.md の「分類」の手順。全スクリプトを流し直して `git diff` で根拠表の変化を見ると、本文の古い値は検査で拾える。
- **コミットと push**: 作業の単位ごとにコミットし、hfu の了承のもとで push してきた (リポジトリは公開)。新しい種類の公開物を
  初めて push する時は一言確認する。author は `18297+hfu@users.noreply.github.com`、メッセージは日本語。
- **外部サイトへの取得は 1 秒間隔**、CI では回さない。外部資料の取得は hfu が了承してきた範囲 (予算・契約・人口・基礎調査・検索 API)。
  新しい種類の外部取得 (例: 気象庁の平年値) は一言確認する。
- 会話は日本語 (敬語)。hfu は「信じるのではなく検証」「自明か情報か」を重視し、ハーネス (物差し・検査・oracle) が分析の質を決めると考えている。
  推定には推定と明記し、要確認を残す。

## 次の候補

- 時系列の筋の残り (`reports/README.md`「まだやっていないこと」): 密度で補正した分野の推移、
  人口・面積あたりの件数、分野別の補正予算。
- 外部資料の要確認: 台帳の「推定」の行 (`reports/findings.md`)。主なものは、令和6年度の届出増と農林水産省・道の通知の日付、令和7年 4〜8 月の業務名の欠落、
  台風 10 号・胆振東部地震の復旧の予算、令和5年度の新しい型 (5 か年加速化対策) の予算、地理情報隊が令和5年度から届け出始めた理由。
- 季節の形の掘り下げ (D28 の残り): 気象庁の平年値 (最深積雪・根雪の期間) で緯度の代わりを置き換える (外部取得、未着手、要確認)。
- cafebabe への寄稿 (未): 分析の知見 (件数と事業費の密度、天気予報の物差し、地方と都道府県の比較、差の差、工期が暦で決まること) と、
  ハーネス (本文の数字の検査・発見の台帳・主張の再計算、D34・D35)。cafebabe セッション宛てに送り、取捨選択は cafebabe に任せる。
- ダッシュボード: 実施地域図のポリゴンのビュー (bvmap-starlight の MapLibre GL JS、別の機会)、GeoParquet をウェブから問い合わせる経路 (DuckDB-WASM など)。

## 再開の一文

「`HANDOVER.md` を読み、hfu に次の候補を確かめてから進める。本文を書いたら 3 つの検査と手の照合を通す。」
