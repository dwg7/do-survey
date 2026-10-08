# 北海道測量概況 — レポートの案内

国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) を観測窓にして、「北海道で何が行われているか」を読む試みの
レポート群。2026-10-07〜08 に作成。すべて素案で、レビューを前提とする。

- 数字は各レポートの根拠表 (スクリプトの生成物) から引いている。判断の経緯は [../DECISIONS.md](../DECISIONS.md) の D 番号を参照。
- 出典: 国土地理院ウェブサイト「公共測量実施情報」(https://psgsv4.gsi.go.jp/giaSearch/)、北海道開発局「予算概要」、北海道「予算の概要」と北海道入札監視委員会の資料を dwg7 が編集・加工して作成。

## まず押さえる「レンズの癖」

レポートを通じて分かった、このデータで北海道を見る時の前提。各レポートはこれを踏まえて読む。

1. **件数は事業の規模ではない。** 測量の需要 (土地に手を入れる回数) を表す。金額では道路が最大でも、件数では農業が最大 ([budget](budget/summary.md))。
2. **届出の範囲が広がり続けている。** 平成20年代初めまでは登録する機関そのものが増え ([longterm](longterm/estimate.md))、その後も 100 億円あたりの
   件数 (密度) が上がり続けた。令和6年度の道営農業の倍増は、会計検査院の指摘を受けた届出の増加で、道の委託契約は増えていない ([r07](r07/draft.md) §5、[budget](budget/summary.md)、[contracts](contracts/summary.md))。
   **道の届出は事業の量より届出の運用に左右される** (契約に対する比率が年で揺れる、[contracts](contracts/summary.md))。
3. **記録の形が年代で変わる。** 業務名 (自由記述) は平成24年度ごろから、担当部署と実施地域図は平成21年度ごろから。令和7年 4〜8 月は業務名が欠ける。
   計画機関名は現在の組織名に置き換えて記録されている。
4. **受付は契約の時点、工期は契約の窓。** 作業の時期や作業時間ではない ([term](term/summary.md))。
5. **毎年同じことは、年の比較では情報がないが、地方の比較では北海道の特徴になりうる** ([annual](annual/summary.md)、[national](national/summary.md))。

## レポート一覧 (推奨の読む順)

| # | レポート | 問い | 結論 (一行) | 根拠表 | 記録 |
|---|---|---|---|---|---|
| 1 | [令和7年度 北海道測量概況 (改訂版) 素案](r07/draft.md) | 試行版の概況文は正しいか。仮説 A〜C は | 試行版の多くは支持、「空知は中山間」「自治体の航空写真は固定資産税」は否定。仮説 A は件数では支持・規模では否定、B は「土地に手を入れる行政」のセンサーとして支持、C は日高は接続・胆振は復旧と生産 | [tables](r07/tables.md) | D16 |
| 2 | [件数と事業費の突き合わせ](budget/summary.md) | 件数は事業費の動きを写すか | 予算の大きな転換点は増幅されて写るが、年ごとの増減は合わない。密度が上がり続け、令和6年度の倍増は予算では説明できない | [compare](budget/compare.md) | D19 |
| 3 | [長期の変化は取れるか — 見積もり](longterm/estimate.md) | どの年代まで遡って比べられるか | 比べる土台は平成21年度以降。それ以前は幅付き・参考 | [tables](longterm/tables.md) | D17 |
| 4 | [飛び石で見た北海道の 15 年](stepping/summary.md) | 平成22・27年度、令和2・7年度で何が変わったか | 測量の構成は道路から農業へ (事業費の重心は動いていない)、上期集中の進行、十勝・空知への重心移動、日高の接続の持続 | [compare](stepping/compare.md)、[H22](h22/tables.md)・[H27](h27/tables.md)・[R2](r02/tables.md) | D18 |
| 5 | [単年度の概況は「薄曇り」か「太陽は東から昇る」か](annual/summary.md) | 単年度の概況はどれだけ情報を持つか | 「最も多いのは〜」は自明か偶然のぶれ。「平年と比べて」は 17 年中 15 年に予想外があり、多くは予算・災害・施策、4 割ほどはレンズの変化。概況を「地勢」と「今年の天気」の 2 層で書く提案 | [overviews](annual/overviews.md)、[skill](annual/skill.md) | D20 |
| 6 | [北海道の「地勢」は北海道に固有か](national/summary.md) | 毎年同じ特徴は北海道に固有か | 7 月の山・冬の空白は北海道に固有。農業が最大は農村型の地方に共通。市町村・民間の発注と固定資産の航空写真は 10 地方で最少 | [compare](national/compare.md) | D21 |
| 7 | [受付の季節の形の分解](season/summary.md) | 夏の集中の強まりは全国一律か | 元からの地勢に、全国共通の前倒し (約半分) と北海道に固有の上乗せ (夏の山の鋭化、開発局の早期発注) が重なった | [compare](season/compare.md) | D23 |
| 8 | [測量期間 (工期) の分析](term/summary.md) | 航空撮影は季節に従うか。工期はどう決まるか | 航空写真は春・レーザは晩秋に窓を開け、工期は 30〜45 日長い。工期は歩掛ではなく暦 (契約時期と旬の締め切り) で決まる | [tables](term/tables.md) | D22 |
| 9 | [原因の分からない「予想外」4 件の掘り下げ](anomaly/summary.md) | annual で原因を「不明」に残した 4 件は何か | H23 空知は主に物差しと分母 (件数は平常)。H26 上川は国営 2 地区と道営の重なり、H28 釧路は道の事業の終わりの重なりで端境期の始まり。R4 上川は道の発注の谷の底で、契約は平常 (10 で届出の変化と判明) | [tables](anomaly/tables.md) | D24 |
| 10 | [道の発注: 届出と委託契約の突き合わせ](contracts/summary.md) | 道の届出の増減は事業の増減か、届出の仕方の変化か | 令和6年度の倍増も令和4年度の上川の減少も、委託契約は動かず届出の比率が動いた (レンズ)。道の届出は道の予算の転換 (令和元〜2年度の増額) も写さない | [compare](contracts/compare.md) | D25 |
| 11 | [開発局の補正予算・ゼロ国債と届出](supplementary/summary.md) | 補正予算は件数に写るか。ゼロ国債は冬の受付を作るか | 開発局の件数の増減は「当初 + 前年度の補正」と最もよく合う (相関 +0.70)。ゼロ国債は 1〜3 月の受付を作っていない | [compare](supplementary/compare.md) | D26 |

データの定義と市町村名の読み替えは [../SCHEMA.md](../SCHEMA.md)、分類の規則は [../analysis/](../analysis/) の `*-rules.csv`。

## 後のレポートで修正された主張

先に書いたレポートの一部は、後の分析で直した (直した文はレポート本文にも反映済み)。読み違いを防ぐため一覧にする。

| 最初の主張 | 修正 | 修正したレポート |
|---|---|---|
| 令和6年度の農業の倍増は「事業の着手の増加」 | 会計検査院の指摘を受けた**届出の増加**とみられ、予算 (横ばい) では説明できない | r07 §5 (D16 追記)、budget (D19) |
| 長期の比較は平成21年度以降なら「登録の顔ぶれが一定」で比べられる | 顔ぶれは一定でも、機関の中の届出の範囲 (密度) は広がり続けた | budget (D19) |
| 飛び石: 「社会資本から農業へ」 | **測量の届出の構成**の変化であって、事業費の重心は動いていない (道路は直轄で農業の 3 倍) | stepping §1・§2 (D19) |
| r07 仮説 A: 「件数については支持」 | 件数では支持、**事業の規模では否定** | r07 §8 (D19) |
| r07 の公共事業執行 131 件・防災減災 131 件 | 分類規則の追加 (地すべり) で 128 件・134 件 | r07 §4 (D17) |
| 飛び石: 「歌志内市は令和元〜7年度も 0 件」 | 令和元・4・5年度に計 6 件ある | stepping §5 (D18) |
| 地方の比較: 「分野: 行政情報」は北海道の特徴 (z = +7.5) | 分類規則のずれ。他の地方の航空写真は定型語「固定資産」で別の分野に入る | national (D21) |
| annual: 平成23年度は「空知の割合がかなり高い」(原因不明) | 件数は平常。前 5 年度の平年に届出の狭い平成20年度以前と平成22年度の谷が入り、開発局の谷で分母が縮んだ。平成21〜25年度の概況の「平年」は平成20年度以前を含む点に注意 | anomaly (D24) |
| anomaly: 令和4年度の上川の減少は原因未確定 (道の予算か届出か) | 道の委託契約は平常で、届出の比率が下がった (レンズ寄り) | contracts (D25)、anomaly §4 追記 |
| r07・budget: 令和6年度の倍増は届出の増加と「みられる」(推定) | 道の委託契約が増えていないことで裏付け (推定から確認へ) | contracts (D25) |
| budget: 件数は予算の転換点は写すが「年ごとの増減は合わない」 | 前年度の補正予算を足すと増減の相関は +0.31 → +0.70。合わなかった一部は補正を入れていなかったため | supplementary (D26) |

## レビューで見てほしい点

- **分類の妥当性**: 行政目的 6 分類 (生産力維持・地域維持・公共事業執行・防災減災・資産管理・制度・権利管理) の定義と、ねらいと段階を
  分けた案 1 の扱い ([../analysis/aim-rules.csv](../analysis/aim-rules.csv)、r07「方法」)。
- **推定の強さ**: 原因の推定 (予算・災害・届出・記録の形) のうち、外部資料で裏が取れていないもの。各レポートの「残り」「要確認」に列挙。
- **概況の 2 層の書き方** (地勢 + 今年の天気) が、読み手 (行政・業界・一般) にとって有用か ([annual](annual/summary.md))。
- **件数の読み方**: 件数を「測量の需要」として読むことの是非と、密度の扱い ([budget](budget/summary.md))。

## まだやっていないこと (時系列の筋の残り)

- 密度 (100 億円あたりの件数) で補正した分野の推移
- 出来事の年表 (原因の分からない予想外 4 件は [anomaly](anomaly/summary.md) で掘り下げ済み。令和4年度の上川は未確定)
- 地域 (振興局) の推移と、測量のない市町村の変化
- 分野別の補正予算と分野別の届出 (補正の総額は 11、道の当初予算の推移と委託契約は 10 で取得済み)

## 再現

```bash
python3 scripts/classify.py          # 発注主体・分野・ねらい (行政目的 6 分類)・段階に分類 → analysis/classified.csv
python3 scripts/r07_tables.py        # 1 の根拠表 reports/r07/tables.md
python3 scripts/fetch_budget.py      # 開発局の当初予算 → data/external/hkd-budget-initial.csv (PDF は data/raw/budget/)
python3 scripts/budget_compare.py    # 2 reports/budget/compare.md
python3 scripts/longterm_tables.py   # 3 reports/longterm/tables.md
python3 scripts/year_tables.py 2010 reports/h22/tables.md   # 任意の年度の根拠表 (r07_tables.py は 2025 の版)
python3 scripts/stepping_compare.py  # 4 reports/stepping/compare.md
python3 scripts/annual_overview.py   # 5 reports/annual/overviews.md・skill.md
for s in B C D E F G H I J K; do python3 scripts/fetch.py --section $s --years 2023 2024 2025; done   # 他の地方
python3 scripts/national_compare.py  # 6 reports/national/compare.md
for s in B C D E F G H I J; do python3 scripts/fetch.py --section $s --years 2009 2014 2019; done
python3 scripts/season_did.py        # 7 reports/season/compare.md
python3 scripts/term_analysis.py     # 8 reports/term/tables.md
python3 scripts/anomaly_drill.py     # 9 reports/anomaly/tables.md
python3 scripts/fetch_pref_contracts.py   # 道の委託・工事の契約 → data/external/hokkaido-pref-contracts-h1.csv (PDF は data/raw/budget/pref/)
python3 scripts/pref_contracts_compare.py # 10 reports/contracts/compare.md
python3 scripts/fetch_budget_supp.py      # 開発局の補正予算・ゼロ国債 → data/external/hkd-budget-supplementary.csv (PDF は data/raw/budget/hosei/)
python3 scripts/budget_supp_compare.py    # 11 reports/supplementary/compare.md
```
