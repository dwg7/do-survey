# HANDOVER.md — 引き継ぎ (2026-09-24 時点)

規約は `CLAUDE.md`、経緯は `DECISIONS.md` (D1〜D9)、列と読み替えは `SCHEMA.md`。このファイルは「今どこまで進んでいて、
次に何をするか」だけを書く。

## 現在の状態

- `data/surveys.parquet`: 受付年度 1983〜2026 の 17,514 件 (2026-09-24 取得、2026 年度は 9/17 受付分まで)。
  実施地域図のポリゴン 13,291 件。読み替えできない名前は 2 件 (`富良野町`、`北海道`)。
- `docs/data/counts.json` (年度・令和・全期間 × 市町村の関与件数・按分件数) と `docs/vendor/do/` (tabularmaps/do@2439872
  の描画コア・Open MCT プラグイン・配置データ) は作ってあるが、ダッシュボードと一緒にコミットするため未コミット。
- ダッシュボードはまだ無い。hfu とチャットで統計を確認した段階 (令和の関与件数の上位: 帯広 193、旭川 164、札幌 164、
  北見 148、深川 147)。
- dwg7/cafebabe の `PROJECTS.md` に登録済み。cafebabe への寄稿候補: 市区町村欄の複数値、1997〜2000 年度の区名の
  「札幌市」脱落、GeoParquet の実地知見 (泊村の同名衝突は cafebabe が反映済み)。

## 次にやること

1. Open MCT ダッシュボード (tabularmaps/do): 年度ごと + 令和 + 全期間をツリーのリーフとして並べる (cafebabe の助言)。
   主は関与件数、補助に按分件数。GitHub Pages (main の /docs)。
2. 実施地域図のポリゴンのビュー (bvmap-starlight の MapLibre GL JS)。別の機会に。
3. GeoParquet をウェブから問い合わせる (DuckDB-WASM など) 経路の検討。
4. cafebabe への寄稿。
