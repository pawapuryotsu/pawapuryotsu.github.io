# キャラページ（/chars/<名前>/）を chars.json から作る。build.py から呼ばれる。
# データ（ボーナス・金特・能力）は chars.json から自動。評価・イベントは src/chars/texts/*.json（管理人が書く）。
# ボーナスの『上に出す／タブに隠す』と並び順は src/chars/config.json で一括管理。
import html as _h, json, re
from pathlib import Path

e = _h.escape


def slug_of(c):
    return f'{c["苗字"]}{c["名前"] or ""}' + (f'-{c["二つ名"]}' if c.get("二つ名") else "")


# 選手ランク（総合値）→ランク。管理人指定の表（2026-11-03）。表に無い値（180以上など）はランクを付けず数値のみ
RANK_TABLE = [(0, "G"), (20, "F"), (40, "E"), (50, "D"), (60, "C"), (70, "B"), (80, "A"), (90, "S"), (100, "S1"), (110, "S2"),
              (120, "S3"), (130, "S4"), (140, "S5"), (150, "S6"), (160, "S7"), (170, "S8")]


def player_rank(n):
    if not isinstance(n, (int, float)) or n < 0 or n >= 180:
        return None
    return [r for lo, r in RANK_TABLE if n >= lo][-1]


def player_rank_text(n):
    r = player_rank(n)
    return f"{r}（{n}）" if r else str(n)


def fmt(n):
    return str(int(n)) if float(n) == int(n) else str(n)


def bonus_lines(entry):
    """1つのボーナスを『基準値 →変化(Lv)』の形に。ラベル：共通＝Lv45、PSRのみ＝PSR42（PSR50だけLv50）、SRのみ＝SR37"""
    shown, unit = entry.get("表示") or {}, entry.get("単位") or ""
    pts = {}  # lv -> {"SR": v, "PSR": v}
    for rar, tbl in shown.items():
        for lv, v in tbl.items():
            pts.setdefault(int(lv), {})[rar] = v
    if not pts:
        return None
    first_lv = min(pts)
    base = pts[first_lv]
    # 基準：SR35とPSR40が違う値なら『70(SR) 80(PSR)』
    if len(base) == 2 and base["SR"] != base["PSR"]:
        head = f'{fmt(base["SR"])}{unit}(SR) {fmt(base["PSR"])}{unit}(PSR)'
        last = None
    else:
        v = next(iter(base.values()))
        head, last = f"{fmt(v)}{unit}", v
    steps = []
    for lv in sorted(pts):
        if lv == first_lv:
            continue
        d = pts[lv]
        if len(d) == 2 and d["SR"] == d["PSR"]:
            val, label = d["SR"], f"Lv{lv}"
        elif len(d) == 2:
            steps.append((f'{fmt(d["SR"])}{unit}', f"SR{lv}"))
            steps.append((f'{fmt(d["PSR"])}{unit}', f"PSR{lv}"))
            last = None
            continue
        elif "PSR" in d:
            val, label = d["PSR"], (f"Lv{lv}" if lv == 50 else f"PSR{lv}")
        else:
            val, label = d["SR"], f"SR{lv}"
        if val != last:
            steps.append((f"{fmt(val)}{unit}", label))
            last = val
    return head, steps


def unique_mark(entry):
    return "(固有)" if entry.get("固有") is not None and not entry.get("SR") and not entry.get("PSR") else ""


def bonus_table(rows):
    out = ['<table class="cp-bonus"><tbody>']
    for name, entry in rows:
        r = bonus_lines(entry)
        if not r:
            continue
        head, steps = r
        cell = f'<b>{e(head)}</b>{e(unique_mark(entry))}' + "".join(
            f'<span class="step">→{e(v)}<small>({e(l)})</small></span>' for v, l in steps)
        out.append(f"<tr><th>{e(name)}</th><td>{cell}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def join_patterns(pats):
    seen, out = set(), []
    for p in pats:
        if p and tuple(p) not in seen:
            seen.add(tuple(p))
            out.append("＋".join(p))
    return out


def gold_text(c, kind):
    pats = join_patterns([p.get(kind) for p in c["金特"].get("パターン", [])])
    return "<br>".join(e(p) for p in pats) if pats else "なし"


def friend_text(c):
    f = c["金特"].get("友情", {})
    parts = [f"{k}で獲得：{'、'.join(f[k])}" for k in ("野手", "投手") if f.get(k)]
    return "<br>".join(e(p) for p in parts) if parts else "なし"


def paras(lst):
    return "".join(f"<p>{e(t)}</p>" for t in lst)


def section(title, inner, empty="準備中です。"):
    return f'<section class="cp-sec"><h2>{e(title)}</h2>{inner or f"<p class=muted>{e(empty)}</p>"}</section>'


def deck_examples(name, decks, root):
    out = []
    for school, d in decks.items():
        for k in d["list"]:
            names = [m[0] for m in k["main"] + k["sub"]]
            if name in names:
                imgs = "".join(f'<img src="{root}img/decks/{k[x]}.jpg" alt="{e(d["title"])}のデッキ画像" loading="lazy">' for x in ("r", "d") if k.get(x))
                role = "メイン" if name in [m[0] for m in k["main"]] else "サポート"
                out.append(f'<div class="cp-deck"><p><a href="{root}decks/{school}/">{e(d["title"])}</a>（{e(k["pos"])}・{role}）</p>{imgs}</div>')
    return "".join(out)


def build_page(c, text, config, decks, root="../../"):
    p = c.get("プロフィール", {})
    bonus = c["bonus"]
    important = [(n, bonus[n]) for n in config["重要ボーナス"] if n in bonus and bonus_lines(bonus[n])]
    others = [(n, b) for n, b in bonus.items() if n not in config["重要ボーナス"] and bonus_lines(b)]
    caps = [(n, bonus[n]) for n in config["基礎上限の項目"] if n in bonus and bonus_lines(bonus[n])]
    cap_txt = "<br>".join(f'{e(n.replace("アップ", ""))}：{e(bonus_lines(b)[0])}' for n, b in caps) or "なし"
    ev = {"後": "後", "前": "前"}.get(p.get("前後イベ"), p.get("前後イベ") or "不明")
    basic = (f'<table class="cp-basic"><tbody>'
             f'<tr><th>得意練習</th><td>{e("、".join(c["得意練習"]) or "なし")}</td></tr>'
             f'<tr><th>イベント前後</th><td>{e(ev)}</td></tr>'
             f'<tr><th>基礎上限<sup>※3</sup></th><td>{cap_txt}</td></tr>'
             f'<tr><th>野手金特<sup>※1</sup></th><td>{gold_text(c, "野手")}</td></tr>'
             f'<tr><th>投手金特<sup>※1</sup></th><td>{gold_text(c, "投手")}</td></tr>'
             f'<tr><th>友情特殊能力<sup>※2</sup></th><td>{friend_text(c)}</td></tr>'
             f'</tbody></table>'
             '<p class="cp-note">※1 金特は全パターンを表記（2個獲得できる場合は「＋」でつなぐ）／※2 野手・投手のどちらで獲得できるかを表記／※3 覚醒で付く分も含む</p>')
    imp = bonus_table(important) + (
        f'<details class="cp-more"><summary>その他ボーナスはこちらをタップ</summary>{bonus_table(others)}</details>' if others else "")
    sub = "、".join(f"{k}{v}" for k, v in (p.get("サブポジ") or {}).items()) or "なし"
    ab = p.get("野手能力") or {}
    ab_t = ('<table class="cp-abil"><thead><tr>' + "".join(f"<th>{e(k)}</th>" for k in ab) + "</tr></thead><tbody><tr>"
            + "".join(f"<td>{e(str(v))}</td>" for v in ab.values()) + "</tr></tbody></table>") if ab else ""
    pab = p.get("投手能力") or {}
    pab_t = ('<h3>投手能力</h3><table class="cp-abil"><thead><tr>' + "".join(f"<th>{e(k)}</th>" for k in pab) + "</tr></thead><tbody><tr>"
             + "".join(f"<td>{e(str(v))}</td>" for v in pab.values()) + "</tr></tbody></table>") if pab else ""
    sp = p.get("特殊能力") or {}
    def sp_block(title, lst):
        return f"<h3>{e(title)}</h3><p>{'、'.join(e(x) for x in lst)}</p>" if lst else ""
    ability = (f'<table class="cp-basic"><tbody><tr><th>選手ランク</th><td>{e(player_rank_text(p["選手能力"]) if "選手能力" in p else "不明")}</td></tr>'
               f'<tr><th>メインポジション</th><td>{e(c["ポジション"] or "不明")}</td></tr>'
               f'<tr><th>サブポジション</th><td>{e(sub)}</td></tr>'
               f'<tr><th>利き腕</th><td>{e(p.get("利き腕", "不明"))}</td></tr></tbody></table>'
               f'<h3>野手能力</h3>{ab_t}{pab_t}' + sp_block("野手特殊能力", sp.get("野手")) + sp_block("投手特殊能力", sp.get("投手"))
               + sp_block("その他特殊能力", sp.get("その他")))
    name = c["name"]
    friend_ev = text.get("友情イベント") if (c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手")) else None
    parts = [
        section(f"{name}の基本情報", basic),
        section(f"{name}の重要ボーナス", imp),
        section(f"{name}の金特イベント選択肢", paras(text.get("金特イベント", []))),
        section(f"{name}の共通イベント", paras(text.get("共通イベント", []))),
    ]
    if c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手"):
        parts.append(section("友情イベント", paras(text.get("友情イベント", []))))
    parts += [
        section("自己紹介", paras(text.get("自己紹介", []))),
        section(f"{name}の評価", paras(text.get("評価", []))),
        section(f"{name}の使用デッキ例", deck_examples(c["name"], decks, root), "このキャラを使ったデッキは準備中です。"),
        section(f"{name}の選手能力", ability),
    ]
    # 『【名前】』の見出しの前に『名前』だけ（二つ名を除く）の表記もタイトルに入れる
    return "\n".join(parts)


def generate(chars_path, src, decks, noindex=True):
    config = json.loads((src / "chars" / "config.json").read_text(encoding="utf-8"))
    chars = {c["name"]: c for c in json.loads(Path(chars_path).read_text(encoding="utf-8"))}
    pages = []
    for name in config["公開するキャラ"]:
        c = chars.get(name)
        if not c:
            continue
        tf = next((f for f in (src / "chars" / "texts").glob("*.json") if json.loads(f.read_text(encoding="utf-8")).get("name") == name), None)
        text = json.loads(tf.read_text(encoding="utf-8")) if tf else {}
        path = f"chars/{slug_of(c)}/"
        full = f'{c["二つ名"] and "[" + c["二つ名"] + "]" or ""}{c["苗字"]}{c["名前"] or ""}'
        meta = (f"title: {full}のデータ・イベントまとめ｜パワプロアプリ攻略ベース\n"
                f"description: パワプロアプリ（サクセス・パワクエ共通）のイベキャラ {full} のボーナス、金特、イベント選択肢、選手能力をまとめています。\n"
                f"path: {path}\nnav: none\n" + ("noindex: yes\n" if noindex else ""))
        body = (f'<section class="phead"><p class="eyebrow">イベキャラ データ</p><h1>{e(full)}のデータ・イベントまとめ</h1></section>\n'
                + build_page(c, text, config, decks))
        pages.append(f"<!--\n{meta}-->\n{body}")
    return pages
