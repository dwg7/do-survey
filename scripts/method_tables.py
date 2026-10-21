#!/usr/bin/env python3
"""方法論 (reports/method/) の根拠表 (D44)。

使い方: python3 scripts/method_tables.py   → reports/method/tables.md
入力: analysis/classified.csv、data/external/hkd-budget-initial.csv
- M1〜M4: 1 つの事業が複数の届出に分けられる程度。業務名から番号 (「その N」「第 N 工区」「N 工区」、末尾の数字、括弧の中の数字) と
  予算の注記 ((補正)(明許) など) を除いた名前を「事業の名前」とみなし、同じ年度・同じ計画機関・同じ名前の届出を 1 つのまとまりとする。
  業務名が自由記述の平成24〜令和7年度で、7 字未満の業務名 (決まり文句) は除く。名前の書き方が違えば別のまとまりになるので、分割の下限の目安。
- M5: 物差し (平年・傾向・しきい値) の定義の値。
"""
import collections
import csv
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
rows = [r for r in csv.DictReader((ROOT / 'analysis/classified.csv').open()) if 2012 <= int(r['year']) <= 2025]
rows = [r for r in rows if len(r['purpose'].strip()) > 6]
Z = '0-9０-９一二三四五六七八九十'


def base(p):
    p = p.strip()
    p = re.sub(r'[（(](補正|明許|繰越|ゼロ債|ゼロ国債|債務|単独)[)）]', '', p)
    p = re.sub(rf'その\s*[{Z}]+', '', p)
    p = re.sub(rf'第\s*[{Z}]+\s*工区', '', p)
    p = re.sub(rf'[{Z}]+\s*工区', '', p)
    p = re.sub(rf'[（(]\s*[{Z}]+\s*[)）]', '', p)
    p = re.sub(rf'[{Z}]+\s*$', '', p)
    return re.sub(r'[\s　・、,]', '', p)


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '—'


for r in rows:
    r['base'] = base(r['purpose'])
g = collections.defaultdict(list)
for r in rows:
    g[(r['year'], r['planner'], r['base'])].append(r)

out = ['# 方法論 — 根拠表\n',
       '`scripts/method_tables.py` が生成。国土地理院「公共測量実施情報」(北海道地方測量部、区分 A) を dwg7 が編集・加工。'
       '対象は業務名が自由記述の平成24〜令和7年度の届出 (業務名が 7 字以上)。\n']

out.append('## M1. 同じ年度に同じ事業の名前で出た届出のまとまり\n')
n = len(rows)
multi = sum(len(v) for v in g.values() if len(v) > 1)
SONO = re.compile(rf'その\s*[{Z}]+')
n_sono = sum(1 for r in rows if SONO.search(r['purpose']))
sizes = collections.Counter(len(v) for v in g.values())
out.append(f'届出 {n} 件、まとまり {len(g)} (届出 / まとまり = {n / len(g):.2f})。2 件以上のまとまりに入る届出は {multi} 件 ({pct(multi, n)})。'
           f'業務名に「その N」がある届出は {n_sono} 件。\n')
out.append('| まとまりの届出の数 | まとまりの数 | 届出の数 |')
out.append('|---:|---:|---:|')
for k in sorted(sizes):
    out.append(f'| {k} | {sizes[k]} | {k * sizes[k]} |')

out.append('\n## M2. 発注主体・分野ごとの分割の程度\n')
out.append('| 区分 | 届出 | まとまり | 届出 / まとまり | 2 件以上のまとまりに入る届出 |')
out.append('|---|---:|---:|---:|---:|')
for lab, f in ([('発注: ' + t, (lambda t: lambda r: r['planner_type'] == t)(t)) for t in ('北海道', '北海道開発局', '市町村')]
               + [('分野: ' + x, (lambda x: lambda r: r['field'] == x)(x)) for x in ('農業農村', '道路', '防災・治水', '公物管理', '位置基盤')]
               + [('開発局の分野: ' + x, (lambda x: lambda r: r['planner_type'] == '北海道開発局' and r['field'] == x)(x)) for x in ('農業農村', '道路', '防災・治水')]):
    gg = collections.defaultdict(int)
    for r in rows:
        if f(r):
            gg[(r['year'], r['planner'], r['base'])] += 1
    tn = sum(gg.values())
    out.append(f'| {lab} | {tn} | {len(gg)} | {tn / len(gg):.2f} | {pct(sum(v for v in gg.values() if v > 1), tn)} |')
out.append('\n開発局の 100 億円あたりの届出は農業農村と道路で約 8 倍違う ([budget](../budget/compare.md) B2) が、届出 / まとまりの比は分野でほとんど違わない。'
           '密度の差の大部分は、同じ名前の分割ではなく、名前の違う業務 (地区・路線・段階) の数の差。\n')

out.append('## M3. 届出の数の多いまとまり (上位 10)\n')
out.append('| 届出の数 | 年度 | 計画機関 | 事業の名前 (番号を除いた業務名、先頭 30 字) | 元の業務名の例 |')
out.append('|---:|---|---|---|---|')
for k, v in sorted(g.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]:
    out.append(f'| {len(v)} | {k[0]} | {k[1]} | {k[2][:30]} | {v[0]["purpose"].strip()[:30]} / {v[-1]["purpose"].strip()[:30]} |')

out.append('\n## M4. 年度をまたぐ事業の名前 (同じ計画機関・同じ名前が複数の年度に出る)\n')
yrs = collections.defaultdict(set)
for (y, pl, b) in g:
    yrs[(pl, b)].add(int(y))
span = collections.Counter(len(v) for v in yrs.values())
cross = sum(len(v) for k, v in g.items() if len(yrs[(k[1], k[2])]) > 1)
out.append(f'事業の名前 {len(yrs)} のうち、2 年度以上に出るもの {sum(c for s, c in span.items() if s > 1)}。'
           f'その名前の届出は {cross} 件 ({pct(cross, n)})。\n')
out.append('| 出た年度の数 | 事業の名前の数 |')
out.append('|---:|---:|')
for k in sorted(span):
    out.append(f'| {k} | {span[k]} |')

# M6: 1 つの事業 (予算の上の事業) が届出にどう分かれるか — 事業の名前を含む届出を全年度で数える
allr = list(csv.DictReader((ROOT / 'analysis/classified.csv').open()))
CASES = [('国営環境保全型かんがい排水事業 別海北部地区 (開発局、農業)', '別海北部'),
         ('一般国道 39 号 端野高野道路 (開発局、道路)', '端野高野'),
         ('国営かんがい排水事業 当麻永山用水地区 (開発局、農業)', '当麻永山'),
         ('一級河川ペケレベツ川 (道、河川・砂防、台風 10 号の災害復旧助成を含む)', 'ペケレベツ')]
out.append('\n## M6. 1 つの事業が届出に分かれる例 (事業の名前を業務名に含む届出、全年度)\n')
out.append('| 事業 | 届出 | 年度の数 (最初〜最後) | 異なる業務名 (番号を除く) | 段階の内訳 | 業務名の例 |')
out.append('|---|---:|---|---:|---|---|')
for lab, key in CASES:
    s_ = [r for r in allr if key in r['purpose']]
    ys = sorted({int(r['year']) for r in s_})
    names = {base(r['purpose']) for r in s_}
    st = collections.Counter(r['stage'] for r in s_)
    ex = sorted({r['purpose'].strip()[:26] for r in s_})[:2]
    out.append(f'| {lab} | {len(s_)} | {len(ys)} ({ys[0]}〜{ys[-1]}) | {len(names)} | ' + '、'.join(f'{k} {v}' for k, v in st.most_common())
               + ' | ' + ' / '.join(ex) + ' |')
out.append('\n1 つの事業が、工区 (地名で呼ばれることが多い)・施設・段階 (計画・用地)・年度ごとに別の業務として発注され、それぞれが 1 件の届出になる。'
           'M1 の「番号だけが違う業務名」の分割は、この分け方のうち番号で呼ぶ部分だけで、地名の工区による分割は数えていない (下限)。\n')

out.append('\n## M5. 物差しの定義の値 (scripts/annual_overview.py)\n')
out.append('| 項目 | 値 |')
out.append('|---|---|')
out.append('| 平年 | 前 5 年度の平均。ばらつきは前 5 年度の標準偏差と、偶然のぶれ (割合は二項 √(p(1−p)/n)、件数はポアソン √平均) の大きい方 |')
out.append('| 傾向 | 前 5 年度の直線の延長。ばらつきは直線からの残差 (自由度 3) と偶然のぶれの大きい方 |')
out.append('| 比べる指標の数 k | 件数 1、発注 3、分野 6、地域 14、時期 1、広がり 1 (群ごと) |')
out.append('| しきい値 (k 個の最大の |z| が偶然超える確率 32% / 5%) | k=1: 1.0 / 2.0、k=3: 1.61 / 2.39、k=6: 1.93 / 2.64、k=14: 2.21 / 2.91 |')
out.append('| 段階 | 平年並み (平年から外れない)、平年と違うが短期傾向どおり、予想外 (平年と傾向の両方から 32% のしきい値を超える)、かなり予想外 (両方で 5% のしきい値を超える) |')
out.append('| 後の 5 年度との比較 | 平成21〜令和2年度の予想外について、後の 5 年度の平均とばらつきで同じ z を出す (D38・D41) |')
out.append('')
(ROOT / 'reports/method').mkdir(parents=True, exist_ok=True)
(ROOT / 'reports/method/tables.md').write_text('\n'.join(out) + '\n')
print('wrote reports/method/tables.md')
