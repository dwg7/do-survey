#!/usr/bin/env python3
"""「令和7年度 北海道測量概況」の根拠表 reports/r07/tables.md を作る (D16)。

中身は scripts/year_tables.py (受付年度を引数に取る、D18)。素案 reports/r07/draft.md はこの表を引用する。
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
subprocess.run([sys.executable, str(HERE / 'year_tables.py'), '2025', 'reports/r07/tables.md'], check=True)
