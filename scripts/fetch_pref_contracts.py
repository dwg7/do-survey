#!/usr/bin/env python3
"""北海道 (道) の発注機関別の入札・契約実績 (上半期、9 月末) を年度ごとに抜き出す (D25)。

出典: 北海道入札監視委員会 (https://www.pref.hokkaido.lg.jp/sm/gms/nyuusatu/nyusatukansiho-mupe-ji.html) の各年度第 2 回の
資料 1-1「入札契約執行状況」の表「発注機関別入札・契約実績 (工事・委託)」。
PDF は data/raw/budget/pref/ に保存し (コミットしない)、pdftotext -layout で読む。
出力: data/external/hokkaido-pref-contracts-h1.csv (件数。随意契約を含む合計。4〜9 月の契約のみ)

- 産業振興部 = 総合振興局・振興局の調整 (農村振興) 課・水産課・林務課 (道営の農業農村整備はここ)。
- 建設管理部 = 道路・河川・砂防など。管轄は振興局と一致しない (旭川建設管理部 = 上川総合振興局、札幌建設管理部 = 空知総合振興局など)。
- 委託は測量・設計・調査などの業務委託で、公共測量の届出と最も近い。工事は参考。
- 表を読んだあと、各機関の件数の和が「計」の行と一致することを確かめる。
"""
import csv
import pathlib
import re
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / 'data/raw/budget/pref'
B = 'https://www.pref.hokkaido.lg.jp/fs/'
SRC = 'https://www.pref.hokkaido.lg.jp/sm/gms/nyuusatu/'
FILES = {   # 年度: (保存名, PDF, 委員会のページ)
    2020: ('nyusatsu-r2h1-summary.pdf', '5/1/6/5/8/1/4/_/02-2-1_1shikkoujoukyou.pdf', '65menu0202.html'),
    2021: ('nyusatsu-r3h1-summary.pdf', '5/4/0/2/0/8/5/_/01_(%E8%B3%87%E6%96%991-1)%E5%85%A5%E6%9C%AD%E5%A5%91%E7%B4%84%E5%9F%B7%E8%A1%8C%E7%8A%B6%E6%B3%81(R3%E5%B9%B4%E5%BA%A6%E4%B8%8A%E5%8D%8A%E6%9C%9F%E5%AE%9F%E7%B8%BE)20220119%E4%BF%AE%E6%AD%A3.pdf', '97510.html'),
    2022: ('nyusatsu-r4h1-summary.pdf', '8/3/1/9/2/2/7/_/%E8%B3%87%E6%96%991-1_%E5%85%A5%E6%9C%AD%E5%A5%91%E7%B4%84%E5%9F%B7%E8%A1%8C%E7%8A%B6%E6%B3%81(R4%E5%B9%B4%E5%BA%A6%E4%B8%8A%E5%8D%8A%E6%9C%9F%E5%AE%9F%E7%B8%BE).pdf', '146882.html'),
    2023: ('nyusatsu-r5h1-summary.pdf', '1/3/2/1/0/9/0/3/_/%E4%BF%AE%E6%AD%A3%E5%BE%8C%20%E4%BB%A4%E5%92%8C5%E5%B9%B4%E5%BA%A6%E7%AC%AC2%E5%9B%9E%E5%85%A5%E6%9C%AD%E7%9B%A3%E8%A6%96%E5%A7%94%E5%93%A1%E4%BC%9A%E8%B3%87%E6%96%991-1%E5%9F%B7%E8%A1%8C%E7%8A%B6%E6%B3%81(R5.9).pdf', '269382.html'),
    2024: ('nyusatsu-r6h1-summary.pdf', '1/1/2/1/8/5/0/1/_/01_R6%E7%AC%AC2%E5%9B%9E%E5%A7%94%E5%93%A1%E4%BC%9A%E8%B3%87%E6%96%99%E4%B8%80%E5%BC%8F(HP).pdf', '212743.html'),
}
SANGYO = ['空知', '石狩', '後志', '胆振', '日高', '渡島', '檜山', '上川', '留萌', '宗谷', 'ｵﾎｰﾂｸ', '十勝', '釧路', '根室']
KENSETSU = ['札幌', '小樽', '室蘭', '函館', '旭川', '留萌', '稚内', '網走', '帯広', '釧路']
UA = 'do-survey/0.1 (Hokkaido public survey dashboard; python-urllib)'


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, path, _ in FILES.values():
        p = RAW / name
        if p.exists():
            continue
        req = urllib.request.Request(B + path, headers={'User-Agent': UA})
        p.write_bytes(urllib.request.urlopen(req).read())
        time.sleep(1)


def parse(text, kind):
    """kind = '工事' / '委託'。産業振興部と建設管理部のブロックを読み、{(部, 機関): 合計件数} を返す。"""
    start = re.search(r'発注機関別入札・契約実績\s*（[^）]*）\s*【' + kind + '】', text)
    body = text[start.end():]
    names = '|'.join(sorted(set(SANGYO + KENSETSU + ['計']), key=len, reverse=True))
    out, block = {}, 0
    for line in body.splitlines():
        m = re.search(r'(?:^|\s)(' + names + r')\s+([\d,.\s]+)$', line)
        if not m:
            continue
        toks = m.group(2).split()
        if kind == '工事':   # 最後の列は一般競争入札の執行率
            toks = toks[:-1]
        n = int(toks[-1].replace(',', ''))
        dept = ['産業振興部', '建設管理部'][block]
        if m.group(1) == '計':
            got = sum(v for (d, _), v in out.items() if d == dept)
            assert got == n, (kind, dept, got, n)
            block += 1
            if block == 2:
                return out
            continue
        assert m.group(1) in (SANGYO if block == 0 else KENSETSU), (kind, block, line)
        out[(dept, m.group(1))] = n
    raise SystemExit(f'{kind}: blocks not found')


def main():
    fetch()
    rows = []
    for y, (name, path, page) in sorted(FILES.items()):
        text = subprocess.run(['pdftotext', '-layout', str(RAW / name), '-'], capture_output=True, text=True, check=True).stdout
        for kind in ('委託', '工事'):
            for (dept, office), n in parse(text, kind).items():
                rows.append({'year': y, 'kind': kind, 'dept': dept, 'office': office.replace('ｵﾎｰﾂｸ', 'オホーツク'),
                             'contracts_h1': n, 'source': SRC + page})
    out = ROOT / 'data/external/hokkaido-pref-contracts-h1.csv'
    with out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {out} ({len(rows)} rows)')


if __name__ == '__main__':
    main()
