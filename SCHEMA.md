# SCHEMA.md — 公共測量実施情報から GeoParquet への対応

`data/surveys.parquet` の列が、国土地理院「公共測量実施情報」の検索画面・CSV・API のどの項目から来るかと、
「測量地域 市区町村」を現在の市町村に読み替える規則を書く。変換の実装は `scripts/build.py`。

## 取得元

- 検索 API: `POST https://psgsv4.gsi.go.jp/giaSearch/RegionMapsSearch` (JSON)。
  本文 `{"JyogenYear": "<受付年度>", "JyogenSection": "A", "PageIndex": n, "PageSize": 200, ...}`、
  応答 `{items, totalCount, pageIndex, pageSize}`。1 ページ最大 200 件。
- 画面の「CSVダウンロード」は同じ API をページ送りで呼び、ブラウザ内で CSV を組み立てる (UTF-8 BOM 付き、
  1 回の検索で最大 1,000 件、`</br>` は `|` に置換)。CSV の列はすべて API の JSON キーに 1 対 1 で対応する。
  このリポジトリは CSV を経由せず、JSON を `data/raw/A-<受付年度>.json` に保存してから変換する。

## 列の対応

1 行 = 1 件の公共測量 (助言番号 1 つ)。`survey_id` で一意。

| GeoParquet 列 | 型 | CSV 列 (画面の表記) | API キー | 変換 |
|---|---|---|---|---|
| `survey_id` | BIGINT | ID | `id` | そのまま |
| `jogen_no` | VARCHAR | 助言番号 | `jogenNo` | そのまま (例 `令7道公第817号`) |
| `jogen_section` | VARCHAR | — | `jogenSection` | そのまま (区分 A は全件 `道公`) |
| `jogen_serial` | INTEGER | (受付番号) | `jogenID` | 整数化。`articleID` と全件一致 |
| `year` | INTEGER | (受付年度) | `yearRecept` | そのまま。4 月〜翌 3 月の年度 |
| `section` | VARCHAR | (測量地域 地方測量部区分) | `articleSectionCode` | そのまま (全件 `A`) |
| `recept_date` | DATE | — | `dateReceptYmd` | `YYYY/MM/DD` → DATE。`--/--/--` は NULL |
| `planner` | VARCHAR | 計画機関名称 | `plannerName` | そのまま |
| `charge_section` | VARCHAR | 担当部署 | `chargeSection` | そのまま |
| `purpose` | VARCHAR | 測量目的 | `purpose` | そのまま (自由記述) |
| `area_pref` | VARCHAR | 測量地域_都道府県 | `areaPref` | そのまま (古い年度は空あり) |
| `area_city_name` | VARCHAR | 測量地域_市区町村 | `areaCityName` | 元の文字列のまま |
| `area_city_names` | VARCHAR[] | 〃 | 〃 | カンマ (`,` `、` `，`) で分割 |
| `muni_codes` | VARCHAR[] | 〃 | 〃 | 分割した名前を現在の市町村コード (全国地方公共団体コード上 5 桁) に読み替え、重複を除いて元の順に並べる (下記) |
| `unresolved_names` | VARCHAR[] | 〃 | 〃 | 読み替えできなかった名前 |
| `term_from` / `term_to` | DATE | 測量期間 | `term` | `</br>` の前後を DATE に |
| `contents_types` | VARCHAR[] | 測量種別 | `contentsType` | `</br>` で分割 |
| `contents_ranks` | VARCHAR[] | 等級・縮尺 | `contentsRankName` | `</br>` で分割 |
| `contents_amounts` | VARCHAR[] | 作業量 | `pointsAreaDistance` | `</br>` で分割 |
| `worker` | VARCHAR | 作業機関名称 | `workerName` | そのまま |
| `worker_code` | VARCHAR | 業者登録番号 | `workerCode` | そのまま |
| `status` | VARCHAR | 進捗状況 | `newStatus` | そのまま (`審査済み` `測量中` `審査中` `成果受付済`) |
| `region_source_pkey` | BIGINT | — | `regionSourcePkey` | そのまま (実施地域図の内部キー) |
| `region_url` | VARCHAR | (実施地域図) | `dirPath` + `docName` | 実施地域図 KML の URL。無ければ NULL |
| `public_result_links` | VARCHAR[] | — | `publicResultHtml` | HTML からリンクの文言だけを抜き出す (`基準点配置図を見る` `地図を見る`) |
| `geometry` | GEOMETRY (WKB) | (実施地域図) | `geom` | GeoJSON 文字列 → ジオメトリ。EPSG:4326。無ければ NULL |
| `fetched_at` | TIMESTAMPTZ | — | — | その年度を取得した時刻 (UTC) |

注意:
- `contents_types` / `contents_ranks` / `contents_amounts` は**位置で対応しない**。1 つの測量種別に等級が 2 つ並ぶ
  (`基準点測量` × `２級|３級`)、見出し (`【大分類】 基準点測量`) が混じる、などがあり、要素数が一致するのは全体の約 7 割。
- 実施地域図は受付年度 2004 以降にしかない (2012〜2025 はほぼ 100%、2004〜2011 は 76〜96%)。当年度は受付から
  登録まで時間差がある。北海道の外にあるポリゴンが 2 件ある (DECISIONS.md D5)。
- 1984〜1991 年度には「測量地域 市区町村」が空のレコードが 237 件ある。`muni_codes` は空。

### 取り込まないキー

冗長なものは `build.py` が一致を確かめてから捨てる。

| API キー | 理由 |
|---|---|
| `name` | `jogenNo` + 半角空白 + `plannerName` と全件一致 |
| `jogenRecept` | `dateReceptYmd` と全件一致 |
| `articleID` | `jogenID` と全件一致 |
| `regionFileName`, `regionFormat`, `documentsCode`, `dirPath` | `region_url` に集約 (形式は全件 `kml`) |
| `publicResultHtml` | HTML。`public_result_links` に文言だけ残す |

## 「測量地域 市区町村」の読み替え

1. カンマで分割し、前後の空白を除く。
2. [tabularmaps/do](https://github.com/tabularmaps/do) の `municipalities.json` の 179 市町村 (`status: active`) の
   正式名称 (`fullName`) と照合する。根室振興局管内の 6 村は照合対象にしない (D4)。これにより「泊村」は後志の泊村
   (01403) に決まる。
3. 一致しなければ `data/name-aliases.csv` で現在の市町村に読み替える。
4. どちらでも引けない名前は `unresolved_names` に残し、市町村には数えない。
5. 読み替えの結果、同じ市町村が重なる時 (例: `南区,札幌市`) は 1 つにまとめる。

`data/name-aliases.csv` (列 `alias,current,kind,effective,source,note`) が一次データで、下の表はその要約
(件数は 1983〜2026 年度に現れた延べ回数)。

| 現在の市町村 | 施行日 | 種類 | 読み替える名前 |
|---|---|---|---|
| 函館市 | 2004-12-01 | 合併 | 南茅部町 22、戸井町 6、恵山町 5、椴法華村 5 |
| 森町 | 2005-04-01 | 合併 | 砂原町 13 |
| せたな町 | 2005-09-01 | 合併 | 北檜山町 24、北桧山町 (異体字) 8、北檜山 (「町」の脱落) 1、瀬棚町 19、大成町 16 |
| 士別市 | 2005-09-01 | 合併 | 朝日町 13 |
| 遠軽町 | 2005-10-01 | 合併 | 生田原町 20、丸瀬布町 11、白滝村 16 |
| 石狩市 | 2005-10-01 | 合併 | 浜益村 30、厚田村 24 |
| 八雲町 | 2005-10-01 | 合併 | 熊石町 10 |
| 釧路市 | 2005-10-11 | 合併 | 音別町 20、阿寒町 20 |
| 北斗市 | 2006-02-01 | 合併 | 上磯町 35、大野町 34 |
| 幕別町 | 2006-02-06 | 合併 | 忠類村 20 |
| 伊達市 | 2006-03-01 | 合併 | 大滝村 6 |
| 日高町 | 2006-03-01 | 合併 | 門別町 34 |
| 北見市 | 2006-03-05 | 合併 | 端野町 30、常呂町 21、留辺蘂町 17、留辺蕊町 (異体字) 16 |
| 枝幸町 | 2006-03-20 | 合併 | 歌登町 11 |
| 岩見沢市 | 2006-03-27 | 合併 | 北村 39、栗沢町 30 |
| 名寄市 | 2006-03-27 | 合併 | 風連町 20 |
| 安平町 | 2006-03-27 | 合併 | 追分町 24、早来町 11 |
| むかわ町 | 2006-03-27 | 合併 | 穂別町 28、鵡川町 24 |
| 洞爺湖町 | 2006-03-27 | 合併 | 虻田町 21、洞爺村 4 |
| 大空町 | 2006-03-31 | 合併 | 女満別町 29、東藻琴村 12 |
| 新ひだか町 | 2006-03-31 | 合併 | 静内町 30、三石町 20 |
| 湧別町 | 2009-10-05 | 合併 | 上湧別町 25 |
| 石狩市 | 1996-09-01 | 市制施行 | 石狩町 23 |
| 北広島市 | 1996-09-01 | 市制施行・改称 | 広島町 8 |
| 札幌市 | — | 区 | 中央区 1、北区 5、東区 2、白石区 2、厚別区 2、豊平区 4、清田区 0、南区 8、西区 1、手稲区 2 |
| 上ノ国町 | — | 表記ゆれ | 上ノ国 1 |

- 合併の施行日と組み合わせは北海道庁「合併市町村一覧 (平成 22 年 4 月 1 日現在)」
  (https://www.pref.hokkaido.lg.jp/ss/scs/gappei/top.html) の 22 件と全件照合済み (`source: hokkaido-gappei`)。
- 石狩町・広島町の市制施行は石狩市年表 (https://www.city.ishikari.hokkaido.jp/shisei/gaiyo/1001902/1003671.html)
  「石狩市、北広島市とともに市制施行」による (`source: ishikari-nenpyo`)。
- 区名は 1997〜2000 年度にだけ「札幌市」を付けずに現れる。北海道の政令指定都市は札幌市だけなので札幌市とする。
- 旧町村名が施行日より後の年度に現れることがある (例: 上湧別町は 2009 年度まで)。登録時の名称のまま読み替える。

読み替えない名前 (`unresolved_names`): `富良野町` (2002、`占冠村,富良野町`。富良野市・上富良野町・中富良野町・
南富良野町のどれか決められない)、`北海道` (2006、道全域の意か特定できない)。
