# ボーナス管理表（Excel）と src/chars/config.json の行き来。
#   python3 tools_bonus_sheet.py to-sheet   ボーナス管理表.xlsx   … config.json からExcelを作る
#   python3 tools_bonus_sheet.py to-config  ボーナス管理表.xlsx   … Excelの内容を config.json に書き戻す（間違いがあれば知らせて止まる）
# Excelの使い方：野手用・投手用・兼用の3シート。A列に項目名を上から順に並べ、
# 「▼ここから下はタップ欄」の行より上が『上に出す』、下が『タップ欄に隠す』。行を動かして並べ替える。
import json, sys
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: F401

CONFIG = Path(__file__).parent / "src" / "chars" / "config.json"
SEP = "▼ここから下はタップ欄（隠す）"
TYPES = ("野手用", "投手用", "兼用")


def to_sheet(dest):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("使い方")
    for i, t in enumerate([
        "ボーナス管理表（キャラページの『上に出す／タップ欄に隠す』と並び順）",
        "野手用・投手用・兼用の3シートに、項目名がA列に上から順に並んでいます。",
        f"『{SEP}』の行より上＝ページ上部に出す重要ボーナス、下＝タップ欄に隠すボーナスです。",
        "並べ替えは、行を選んで切り取り→挿入（または行ごとドラッグ）で動かします。項目名は打ち直さないでください。",
        "区切り行（▼…）を上下に動かすと、上に出す数を変えられます。",
        "B列は自動の確認欄です（「重複」「区切りなし」などが出たら直してください）。",
        "終わったらファイルを渡してください。内容を取り込んで反映します。"], 1):
        ws.cell(i, 1, t)
    ws.column_dimensions["A"].width = 100
    for t in TYPES:
        w = wb.create_sheet(t)
        rows = cfg["重要ボーナス"][t] + [SEP] + cfg["タップ欄のボーナス"][t]
        for i, name in enumerate(rows, 1):
            c = w.cell(i, 1, name)
            if name == SEP:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="1D5E43")
        n = len(rows) + 30
        for i in range(1, n):
            w.cell(i, 2, f'=IF(A{i}="","",IF(COUNTIF($A$1:$A${n},A{i})>1,"重複",IF(A{i}="{SEP}",IF(COUNTIF($A$1:$A${n},"{SEP}")=1,"","区切りが複数"),"")))')
        w.cell(1, 4, "確認：")
        w.cell(1, 5, f'=IF(COUNTIF(A1:A{n},"{SEP}")=1,"区切りOK","区切りが無い／複数")')
        w.column_dimensions["A"].width = 40
        w.column_dimensions["B"].width = 14
    wb.save(dest)
    print("作りました:", dest)


def to_config(src):
    wb = openpyxl.load_workbook(src)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    problems = []
    for t in TYPES:
        names = [str(c.value).strip() for c in wb[t]["A"] if c.value not in (None, "")]
        if names.count(SEP) != 1:
            problems.append(f"{t}：区切り行が{names.count(SEP)}個（1個にしてください）")
            continue
        dup = sorted({n for n in names if names.count(n) > 1 and n != SEP})
        if dup:
            problems.append(f"{t}：重複 {dup}")
        i = names.index(SEP)
        cfg["重要ボーナス"][t], cfg["タップ欄のボーナス"][t] = names[:i], names[i + 1:]
    # 3区分でそろっているか（項目の過不足）
    base = set(cfg["重要ボーナス"]["兼用"]) | set(cfg["タップ欄のボーナス"]["兼用"])
    for t in TYPES:
        cur = set(cfg["重要ボーナス"][t]) | set(cfg["タップ欄のボーナス"][t])
        if cur != base:
            problems.append(f"{t}：兼用と項目が違います 足りない={sorted(base - cur)} 余分={sorted(cur - base)}")
    if problems:
        print("取り込めません：\n  " + "\n  ".join(problems))
        sys.exit(1)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("config.json に反映しました")


if __name__ == "__main__":
    {"to-sheet": to_sheet, "to-config": to_config}[sys.argv[1]](sys.argv[2])
