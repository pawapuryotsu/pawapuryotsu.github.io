"""パワクエ周回カウンターの記録（runs）から、1つのクエストの周だけを書き出して
src/pawaque_data/saikyuki_runs_<id>.json を作る／上書きする（2026-11-19 管理人「他のクエストのページでも使いたい」）。

使い方：
  1. Claude が ArtifactData でカウンター（https://claude.ai/artifact/2ownxm7McE3KRhMwycyGfd）の
     runs を out_dir 付きで読み出す（例：<作業フォルダ>/db/runs/r00001.json …）
  2. python3 tools/pawaque_runs_export.py <id> <クエスト名> <runsフォルダ> [取得日 YYYY-MM-DD]
       例： python3 tools/pawaque_runs_export.py q18 ⑱道中2 /tmp/.../db/runs 2026-11-19
  3. python3 tools/pawaque_run_stats.py <id> → python3 build.py
既にファイルがあれば「記録対象外」（集計から外すアイテム名）はそのまま引き継ぐ。
シナリオは西球記だけ。fp・slotNames など読み取り用のデータは入れない。数字は記録そのまま（推測で足さない）。"""
import datetime, json, sys
from pathlib import Path

here = Path(__file__).resolve().parent.parent
pid, quest, src = sys.argv[1], sys.argv[2], Path(sys.argv[3])
day = sys.argv[4] if len(sys.argv) > 4 else datetime.date.today().isoformat()
out = here / f"src/pawaque_data/saikyuki_runs_{pid}.json"
old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}

runs = []
for f in sorted(src.glob("*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    r = r.get("data", r)
    if r.get("scenario") != "西球記" or r.get("area", "").split(" ", 1)[-1] != quest:
        continue
    drops = [{k: x.get(k) for k in ("area", "boss", "name", "rarity", "skills", "slot")}
             for x in r.get("drops") or [] if not x.get("memo")]   # memo＝スキルのメモだけ（集計しない）
    runs.append({"no": r["no"], "date": r.get("date"), "area": r["area"], "result": r.get("result"), "period": r.get("period"),
                 "areaNums": r.get("areaNums"), "boss": r.get("boss") or {},
                 "prayers": r.get("prayers") or [], "drops": drops})
runs.sort(key=lambda r: r["no"])
assert runs, f"「{quest}」の周が見つからない（クエスト名は帯の表記どおりに）"
D = {"取得日": day, "元": "パワクエ周回カウンター", "クエスト": quest,
     "記録対象外": old.get("記録対象外", []),
     "期間の表示名": old.get("期間の表示名", {}), "runs": runs}
out.write_text(json.dumps(D, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("ok", out.name, len(runs), "周", "（ボス記録あり", sum(1 for r in runs if r["boss"]), "周）")
