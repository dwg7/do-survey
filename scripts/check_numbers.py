#!/usr/bin/env python3
"""概況の本文の数字の決定的な検査 (D34)。

使い方: python3 scripts/check_numbers.py [reports/yearly/r06 ...]   (省略すると reports/yearly/ の全年度と、summary.md のある reports/ の各フォルダ)

本文 (summary.md) の 2 桁以上の数と小数が、次のどれかで裏付けられることを確かめる。裏付けのない数があれば一覧を出して終了コード 1。
  1. 同じフォルダの根拠表 (summary.md 以外の .md、ふつうは tables.md か compare.md) に、その数が文字どおり出てくる (桁区切りのカンマは無視)。
  2. 同じフォルダの checks.csv に、その数の行がある。
     - kind = expr: value の式 (数と + - * / ( ) だけ) を計算して、本文の数と一致する。式に使った数は、すべて根拠表に出てくる (百分率に直す 100 は除く)。
     - kind = ref: value のファイル (リポジトリの相対パス) に、その数が文字どおり出てくる (他のレポートの結論を引く時)。
限界: 数が根拠表のどこかに出てくるかだけを見る。どの項目の数かは確かめない (別の項目に同じ数があれば通る)。
数えない数: 1 桁の整数、年度・月・日付、D/T/Y などの番号、「3 か年」「第 2 次」「国道 40 号」などの数え方の語に付く数。
"""
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NUM = r'(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])'
IGNORE = [r'\[[^\]]*\]\([^)]*\)', r'`[^`]*`',                       # リンクと code
          r'(?:令和|平成|昭和)(?:\d+|元)年度?(?:\s*\d+\s*月)?(?:\s*\d+\s*日)?', r'\d+\s*月', r'\d{4}-\d{2}(?:-\d{2})?',
          r'\b(?:D|T|Y|G|R|H|S|k=?)\s?\d+\b', r'§\d+', r'その\s?\d+', r'第\s?\d+\s?次',
          r'\d+\s?(?:か年|次|段|層|本|つ|周期|年おき|年ごと|区|字|点|周|号)', r'\b\d{1,2}/\d{1,2}\b', r'31 日の月',
          r'\d[\d,]*\s?(?:億円|km²)\s?あたり']


def numbers(text):
    for pat in IGNORE:
        text = re.sub(pat, ' ', text)
    return {n.replace(',', '') for n in re.findall(NUM, text) if len(n.replace(',', '').split('.')[0]) >= 2 or '.' in n}


def table_numbers(text):
    return {n.replace(',', '') for n in re.findall(r'\d[\d,]*(?:\.\d+)?', text)}


def check(d):
    summ = d / 'summary.md'
    tabs = [f for f in d.glob('*.md') if f.name != 'summary.md']
    if not summ.exists() or not tabs:
        return []
    tn = set().union(*(table_numbers(f.read_text()) for f in tabs))
    rows = {}
    ck = d / 'checks.csv'
    if ck.exists():
        for r in csv.DictReader(ck.open()):
            rows.setdefault(r['number'], []).append(r)
    bad = []
    for n in sorted(numbers(summ.read_text()), key=lambda x: float(x)):
        if n in tn:
            continue
        ok, why = False, 'checks.csv に行がない'
        for r in rows.get(n, []):
            if r['kind'] == 'expr':
                expr = r['value']
                if not re.fullmatch(r'[\d.\s+\-*/()]+', expr):
                    why = f'式に使えない文字: {expr}'
                    continue
                ops = set(re.findall(r'\d+(?:\.\d+)?', expr))
                missing = [o for o in ops if o not in tn and o != '100']   # 100 は百分率に直す定数として使ってよい
                val = eval(expr)   # noqa: S307 (数と演算子だけを許した式)
                dec = len(n.split('.')[1]) if '.' in n else 0
                if missing:
                    why = f'式の数が根拠表にない: {missing}'
                elif round(abs(val), dec) != float(n):
                    why = f'式の値 {val} が {n} と合わない'
                else:
                    ok = True
            elif r['kind'] == 'ref':
                f = ROOT / r['value']
                if f.exists() and n in table_numbers(f.read_text()):
                    ok = True
                else:
                    why = f'参照先に数がない: {r["value"]}'
        if not ok:
            bad.append((n, why))
    return bad


def main():
    dirs = [pathlib.Path(a) for a in sys.argv[1:]] or (
        sorted(p for p in (ROOT / 'reports/yearly').iterdir() if p.is_dir())
        + sorted(p.parent for p in (ROOT / 'reports').glob('*/summary.md')))
    total = 0
    for d in dirs:
        bad = check(d if d.is_absolute() else ROOT / d)
        total += len(bad)
        print(f'{d.name}: {"OK" if not bad else f"裏付けのない数 {len(bad)}"}')
        for n, why in bad:
            print(f'  {n}: {why}')
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
