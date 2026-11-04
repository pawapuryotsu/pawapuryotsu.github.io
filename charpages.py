# キャラページ（/chars/<ページ番号4桁>/）と一覧（/chars/）を chars.json から作る。build.py から呼ばれる。
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


def player_rank_html(n):
    if n is None:
        return "不明"
    r = player_rank(n)
    return '<div class="rkline">' + (badge(r) if r else "") + f'<b class="nm">{e(str(n))}</b></div>'


def player_rank_text(n):
    r = player_rank(n)
    return f"{r}（{n}）" if r else str(n)


# 能力値（ミート・パワー・走力・肩力・守備力・捕球・コントロール・スタミナ）→ランク。管理人指定の表（2026-11-03）。選手ランクとは区切りが1ずれる
ABILITY_TABLE = [(0, "G"), (20, "F"), (40, "E"), (50, "D"), (60, "C"), (70, "B"), (80, "A"), (90, "S"), (101, "S1"), (111, "S2"),
                 (121, "S3"), (131, "S4"), (141, "S5"), (151, "S6"), (161, "S7"), (171, "S8")]
RANKED_ABILITIES = ("ミート", "パワー", "走力", "肩力", "守備力", "捕球", "コントロール", "スタミナ")


def ability_text(name, v):
    if name in RANKED_ABILITIES and isinstance(v, (int, float)) and 0 <= v <= 180:
        return f"{[r for lo, r in ABILITY_TABLE if v >= lo][-1]}（{v}）"
    return str(v)


def rank_of(name, v):
    """能力値→ランク文字（S1など）。対象外・範囲外は None"""
    if name in RANKED_ABILITIES and isinstance(v, (int, float)) and 0 <= v <= 180:
        return [r for lo, r in ABILITY_TABLE if v >= lo][-1]
    return None


def badge(rank):
    """ゲーム画面ふうのランク文字。S1のような数字つきは、右下に小さく数字を出す"""
    base, num = rank[0], rank[1:]
    sub = f"<i>{e(num)}</i>" if num else ""
    return f'<span class="rk rk-{base}" aria-label="ランク{e(rank)}">{e(base)}{sub}</span>'


# 弾道：1=黄・横、2=Cの色・やや上向き、3=Bの色・45°、4=Aの色・60°（管理人指定）
TRAJ = {1: ("#ffd23c", 0), 2: ("#ff9a1a", 25), 3: ("#ff4040", 45), 4: ("#ff4fd8", 60)}


def traj_arrow(n):
    if n not in TRAJ:
        return ""
    color, deg = TRAJ[n]
    return (f'<svg class="traj" viewBox="-20 -20 40 40" role="img" aria-label="弾道{n}"><g transform="rotate({-deg})">'
            f'<path d="M-15 -5H2V-13L16 0L2 13V5H-15Z" fill="{color}" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></g></svg>')


def ability_tiles(d):
    out = [f'<div class="cp-tiles" style="--n:{len(d)}">']
    for k, v in d.items():
        r = rank_of(k, v)
        if k == "弾道" and isinstance(v, int):
            mid = traj_arrow(v)
        elif r:
            mid = badge(r)
        else:
            mid = ""
        unit = "<small>km/h</small>" if k == "球速" else ""
        out.append(f'<div class="at"><span class="lb">{e(k)}</span>{mid}<b class="nm">{e(str(v))}{unit}</b></div>')
    out.append("</div>")
    return "".join(out)


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
    # SRの基準とPSRの基準だけで、値が違う項目（初期評価など）は「60(SR) 70(PSR)」の形
    sr_pts, psr_pts = shown.get("SR") or {}, shown.get("PSR") or {}
    if len(sr_pts) == 1 and len(psr_pts) == 1:
        sv, pv = next(iter(sr_pts.values())), next(iter(psr_pts.values()))
        if sv != pv:
            return f"{fmt(sv)}{unit}(SR) {fmt(pv)}{unit}(PSR)", []
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


def item_rows(c):
    """追加枠「○○」・キャラ持参アイテム「○○」（chars.json の「アイテム」）。同じ種類は1行にまとめる"""
    by = {}
    for it in c.get("アイテム") or []:
        by.setdefault(it["種類"], []).append(it["名前"])
    return "".join(f'<tr><th>{e(k)}</th><td><b>{e("、".join(v))}</b></td></tr>' for k, v in by.items())


def bonus_table(rows, extra=""):
    out = ['<table class="cp-bonus"><tbody>']
    for name, entry in rows:
        r = bonus_lines(entry)
        if not r and entry.get("固有文字"):  # 固有の値がゲーム内で分からない項目（得意練習率アップα）は文字のまま出す
            r = (f'{entry["固有文字"]}', [])
            out.append(f'<tr><th>{e(name)}</th><td><b>{e(r[0])}</b>(固有)</td></tr>')
            continue
        if not r:
            continue
        head, steps = r
        cell = f'<b>{e(head)}</b>{e(unique_mark(entry))}' + "".join(
            f'<span class="step">⇒{e(v)}<small>({e(l)})</small></span>' for v, l in steps)
        out.append(f"<tr><th>{e(name)}</th><td>{cell}</td></tr>")
    out.append(extra)
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


def event_kinds(c, config, text, has_friend):
    """そのキャラのページに並べるイベントの種類（分類ごと。config.json「イベント構成」）"""
    kinds = list(config["イベント構成"].get(c.get("分類") or "選手", config["イベント構成"]["選手"]))
    if has_friend and "友情イベント" not in kinds and (c.get("分類") or "選手") == "選手":
        kinds.insert(kinds.index("共通イベント") + 1 if "共通イベント" in kinds else len(kinds), "友情イベント")
    # エピローグ：彼女・選手彼女・相棒は構成に含まれる。選手は、共通イベントの小イベントの1つとして texts に書く
    return kinds


def events_of(text, kinds):
    """texts の「イベント」（リスト）を種類ごとの辞書に。古い書き方（金特イベント等の段落リスト）も詳細として読む"""
    ev = {k: {} for k in kinds}
    for x in text.get("イベント", []):
        if x.get("種類") in ev:
            ev[x["種類"]] = x
    for old in ("金特イベント", "共通イベント", "友情イベント", "自己紹介"):
        if old in ev and not ev[old] and text.get(old):
            ev[old] = {"種類": old, "詳細": text[old]}
    return ev


_KINDS = None


def _is_gold_kotsu(item):
    """「○○コツLv3」の○○が金特の能力、または威圧感なら True（青太字で出す）"""
    global _KINDS
    if _KINDS is None:
        _KINDS = json.loads((Path(__file__).resolve().parent / "src" / "chars" / "skill_kinds.json").read_text(encoding="utf-8"))
    m = re.match(r"(.+?)コツ", item)
    if not m:
        return False
    n = m.group(1)
    return n == "威圧感" or any(g.get(n) == "金特" for g in _KINDS.values())


def _item(i):
    return f'<div class="cp-kotsu-gold">{e(i)}</div>' if _is_gold_kotsu(i) else f"<div>{e(i)}</div>"


def _choice_name(t):
    """選択肢の名前。（イベント継続）は青、（イベント終了）は赤で、改行して出す"""
    m = re.match(r"^(.*?)[（(](イベント継続|イベント終了)[）)]$", t)
    if not m:
        return e(t)
    cls = "cp-cont" if m.group(2) == "イベント継続" else "cp-end"
    return f'{e(m.group(1))}<br><span class="{cls}">（{m.group(2)}）</span>'


def _cell(x):
    """1行ぶんの「その他」欄。投手／野手ごとの項目と、共通のその他を縦に並べる"""
    out = ""
    for lab in ("投手", "野手"):
        if x.get(lab):
            out += f'<div class="cp-t-lab">【{lab}】</div>' + "".join(_item(i) for i in x[lab])
    out += "".join(_item(i) for i in x.get("その他", []))
    return out


def sub_table(rows):
    """イベントの表。選択肢ごとに1行。左＝選択肢名、中＝効果（＋）、右＝投手／野手などその他。選択肢が無いイベントは左の列を出さない"""
    has_name = any(r.get("選択肢") for r in rows)
    has_other = any(r.get("投手") or r.get("野手") or r.get("その他") for r in rows)  # コツなどが無いイベントは「その他」列を出さない
    head = ("<th></th>" if has_name else "") + "<th>＋</th>" + ("<th>その他</th>" if has_other else "")
    body = ""
    for r in rows:
        name = f'<th class="{"ok" if r.get("正解") else ""}">{"◎ " if r.get("正解") else ""}{_choice_name(r.get("選択肢", ""))}</th>' if has_name else ""
        eff = "".join(f"<div>{e(i)}</div>" for i in r.get("効果", []))
        body += f"<tr>{name}<td>{eff}</td>" + (f"<td>{_cell(r)}</td>" if has_other else "") + "</tr>"
    return f'<div class="cp-tbl-wrap"><table class="cp-tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def event_detail(ev):
    """イベント詳細。金特イベント・共通イベント・自己紹介など全部をここに並べる。
    「小イベント」（名前＋表の行）があれば表で、無ければ従来の書き方（体力・やる気・コツ・選択肢・詳細）で出す。
    小イベントに「折りたたむ: true」を付けると『詳細を表示』ボタンの中に入る"""
    parts = []
    for k, x in ev.items():
        inner = paras(x.get("詳細", [])) if x.get("小イベント") else ""
        for sub in x.get("小イベント", []):
            t = sub_table(sub["行"]) if sub.get("行") else ""
            if sub.get("名前"):
                head = f'<h4 class="cp-sub">・{e(sub["名前"])}</h4>'
            else:
                head = ""
            if sub.get("詳細"):
                t = paras(sub["詳細"]) + t if sub.get("行") else paras(sub["詳細"])
            elif not sub.get("行"):
                t = '<p class="muted">準備中です。</p>'
            inner += head + t
        eff = " / ".join(f"{lab}：{x[key]}" for key, lab in (("体力", "体力"), ("やる気", "やる気")) if x.get(key))
        if x.get("コツ"):
            eff += (" / " if eff else "") + "もらえるコツ：" + "、".join(x["コツ"])
        if eff:
            inner += f'<p class="cp-eff">{e(eff)}</p>'
        if not x.get("小イベント"):
            inner += paras(x.get("詳細", []))
        if x.get("選択肢"):
            inner += "<ul class=cp-choices>" + "".join(
                f'<li{" class=ok" if c.get("正解") else ""}>{"◎ " if c.get("正解") else ""}{e(c["文"])}'
                + (f'<br><span class="muted">{e(c["結果"])}</span>' if c.get("結果") else "") + "</li>" for c in x["選択肢"]) + "</ul>"
        parts.append(f"<h3>{e(k)}</h3>" + (inner or '<p class="muted">準備中です。</p>'))
    return "".join(parts)


def section(title, inner, empty="準備中です。"):
    return f'<section class="cp-sec"><h2>{e(title)}</h2>{inner or f"<p class=muted>{e(empty)}</p>"}</section>'


# 緑と赤が半々のボックスで出す特殊能力（管理人指定。データ上は青特で入っている）
# 青と赤が半々（波線）のボックスで出す特殊能力（管理人指定 2026-11-03。データ上は青特で入っている）
HALF_SP = ("悪球打ち", "気分屋", "荒れ球", "全開", "ポーカーフェイス")
KIND_CLASS = {"青特": "blue", "金特": "gold", "赤特": "red", "緑特": "green", "虹特": "rainbow"}


def sp_box(name, group, kinds):
    if name in HALF_SP:
        cls = "halfblue"
    else:
        kind = None
        for g in ([group] if group in kinds else list(kinds)):
            kind = kind or kinds[g].get(name)
        cls = KIND_CLASS.get(kind, "none")
    return f'<span class="sp sp-{cls}">{e(name)}</span>'


def deck_examples(name, decks, root):
    found = []
    for school, d in decks.items():
        for k in d["list"]:
            names = [m[0] for m in k["main"] + k["sub"]]
            if name in names:
                found.append((k["rank"], k["exp"], school, d, k))
    found.sort(key=lambda x: (-x[0], -x[1]))  # 選手ランクが高い順（同じなら総経験点が高い順）

    def one(school, d, k):
        imgs = "".join(f'<img class="{x}" src="{root}img/decks/{k[x]}.jpg" alt="{e(d["title"])}のデッキ画像" loading="lazy">' for x in ("r", "d") if k.get(x))
        role = "メイン" if name in [m[0] for m in k["main"]] else "サポート"
        return f'<div class="cp-deck"><p><a href="{root}decks/{school}/">{e(d["title"])}</a>（{e(k["pos"])}・{role}）</p>{imgs}</div>'
    cards = [one(sc, d, k) for _, _, sc, d, k in found]
    out = "".join(cards[:2])
    if len(cards) > 2:
        out += f'<details class="cp-more"><summary>その他のデッキはこちらをタップ</summary>{"".join(cards[2:])}</details>'
    return out


# 投手の変化球の図（ゲームの投手能力画面ふう）。変化量の数だけ、中心から色つき（赤→橙→黄）、残りは青
# 向き（管理人指定）：右投＝右スライダー・右下カーブ・下フォーク・左下シンカー・左シュート。左投は左右反転
SEG_COLORS = ["#ff6a1a", "#ff2f1a", "#ff3d1a", "#ff8a1a", "#ffc61a", "#ffe21a", "#ffec7a"]
DIR_ANGLE = {"スライダー方向": 0, "カーブ方向": 45, "フォーク方向": 90, "シンカー方向": 135, "シュート方向": 180}
CX, CY = 180, 82


def seg_color(i, n):
    """色つきの区画：中心＝赤、先端＝黄になるグラデーション（n個のとき）。1個だけのときは橙"""
    t = i / (n - 1) if n > 1 else 0.5
    g = int(0x2a + (0xe2 - 0x2a) * t)
    return f"#ff{g:02x}1a"


def pitch_chart(p):
    pitches = {x["方向"]: x for x in p.get("球種", [])}
    if not any(k in pitches for k in DIR_ANGLE):
        return ""
    lefty = str(p.get("利き腕", "")).startswith("左")
    out = ['<svg class="pchart" viewBox="0 0 360 240" role="img" aria-label="変化球の方向と変化量">']
    for direction, ang in DIR_ANGLE.items():
        x = pitches.get(direction)
        n = int(x["変化量"]) if x and x.get("変化量") else 0
        a = (180 - ang) if lefty else ang
        segs = []
        for i in range(7):
            col = seg_color(i, n) if i < n else "#46a8ff"
            segs.append(f'<rect x="{22 + i * 13}" y="-7" width="12" height="14" fill="{col}" stroke="#0b3f9e" stroke-width="1.5"/>')
        tip = '<path d="M113 -7L127 0L113 7Z" fill="#46a8ff" stroke="#0b3f9e" stroke-width="1.5"/>'
        out.append(f'<g transform="translate({CX} {CY}) rotate({a})">{"".join(segs)}{tip}</g>')
        if x:
            name = x.get("オリジナル名") or x.get("種類")  # オリジナル球種は、データに入力した名前を表記
            ex, ey = CX + 127 * __import__("math").cos(__import__("math").radians(a)), CY + 127 * __import__("math").sin(__import__("math").radians(a))
            if abs(a % 360 - 0) < 1:
                tx, ty, anc = ex - 4, CY - 18, "end"
            elif abs(a % 360 - 180) < 1:
                tx, ty, anc = ex + 4, CY - 18, "start"
            elif abs(a % 360 - 90) < 1:
                tx, ty, anc = ex, ey + 22, "middle"
            else:  # 斜め：先端の少し下に中央ぞろえ
                tx, ty, anc = ex, ey + 22, "middle"
            out.append(f'<text class="pc-lb" x="{tx:.0f}" y="{ty:.0f}" text-anchor="{anc}">{e(name)}</text>')
    out.append(f'<circle cx="{CX}" cy="{CY}" r="15" fill="#fff" stroke="#b83030" stroke-width="2"/>')
    st, st2 = pitches.get("ストレート"), pitches.get("第二ストレート")

    def sname(x):
        return (x.get("オリジナル名") or x.get("種類") or "ストレート") if x else ""
    arrow = lambda cx: f'<path d="M{cx - 8} 52L{cx} 42L{cx + 8} 52Z" fill="#ff9a1a" stroke="#0b3f9e" stroke-width="1.5"/>'
    if st2:
        out.append(arrow(CX - 12) + arrow(CX + 12))
        out.append(f'<text class="pc-lb" x="{CX - 6}" y="30" text-anchor="end">{e(sname(st) or "ストレート")}</text>'
                   f'<text class="pc-lb" x="{CX + 6}" y="30" text-anchor="start">{e(sname(st2))}</text>')
    else:
        out.append(arrow(CX) + f'<text class="pc-lb" x="{CX}" y="30" text-anchor="middle">{e(sname(st) or "ストレート")}</text>')
    out.append("</svg>")
    return "".join(out)


def max_value(entry):
    """判定用：PSRの最大Lvの値（PSRが無ければSRの最大Lv）"""
    shown = entry.get("表示") or {}
    for rar in ("PSR", "SR"):
        t = shown.get(rar)
        if t:
            return t[max(t, key=int)]
    return None


def char_type(c, rules):
    """野手用／投手用／兼用。どちらも満たさない（環境外）は兼用と同じ扱い"""
    def ok(conds):
        return all((max_value(c["bonus"].get(k, {})) or 0) >= v for k, v in conds.items())
    p, f = ok(rules["投手条件"]), ok(rules["野手条件"])
    return "兼用" if p == f else ("投手用" if p else "野手用")


def build_page(c, text, config, decks, kinds, root="../../"):
    p = c.get("プロフィール", {})
    bonus = c["bonus"]
    ctype = char_type(c, config["種別の判定"])
    top_names, tap = config["重要ボーナス"][ctype], config["タップ欄のボーナス"][ctype]
    important = [(n, bonus[n]) for n in top_names if n in bonus and (bonus_lines(bonus[n]) or bonus[n].get("固有文字"))]
    unknown = [n for n in bonus if n not in top_names and n not in tap]
    if unknown:
        print(f"【警告】{c['name']}：config.json にないボーナス {unknown}（タップ欄の一番下に出します）")
    others = sorted(((n, b) for n, b in bonus.items() if n not in top_names and (bonus_lines(b) or b.get("固有文字"))),
                    key=lambda nb: tap.index(nb[0]) if nb[0] in tap else len(tap))
    caps = [(n, bonus[n]) for n in config["基礎上限の項目"] if n in bonus and bonus_lines(bonus[n])]
    cap_txt = "<br>".join(f'{e(n.replace("アップ", ""))}：{e(bonus_lines(b)[0])}' for n, b in caps) or "なし"
    ev = {"後": "後", "前": "前"}.get(p.get("前後イベ"), p.get("前後イベ") or "不明")
    basic = (f'<table class="cp-basic"><tbody>'
             f'<tr><th>得意練習</th><td>{e(" / ".join(c["得意練習"]) or "なし")}</td></tr>'
             f'<tr><th>イベント前後</th><td>{e(ev)}</td></tr>'
             f'<tr><th>基礎上限<sup>※</sup></th><td>{cap_txt}</td></tr>'
             f'<tr><th>野手金特</th><td>{gold_text(c, "野手")}</td></tr>'
             f'<tr><th>投手金特</th><td>{gold_text(c, "投手")}</td></tr>'
             f'<tr><th>友情特殊能力</th><td>{friend_text(c)}</td></tr>'
             f'</tbody></table>'
             '<p class="cp-note">※ 覚醒で付く分も表記</p>')
    imp = bonus_table(important, item_rows(c)) + (
        f'<details class="cp-more"><summary>その他ボーナスはこちらをタップ</summary>{bonus_table(others)}</details>' if others else "")
    sub = "、".join(f"{k}{v}" for k, v in (p.get("サブポジ") or {}).items()) or "なし"
    ab = p.get("野手能力") or {}
    pab = p.get("投手能力") or {}
    ab_t = ability_tiles(ab) if ab else ""
    pab_t = ("<h3>投手能力</h3>" + ability_tiles(pab) + pitch_chart(p)) if pab else ""
    sp = p.get("特殊能力") or {}
    def sp_block(title, lst, group):
        lst = [x for x in (lst or []) if not str(x).startswith("オリジナル")]  # オリジナルストレート・変化球は特殊能力ではない（球種欄に名前が出る）
        if not lst:
            return ""
        return f"<h3>{e(title)}</h3>" + '<div class="cp-sp">' + "".join(sp_box(x, group, kinds) for x in lst) + "</div>"
    ability = (f'<table class="cp-basic"><tbody><tr><th>選手ランク</th><td>{player_rank_html(p.get("選手能力"))}</td></tr>'
               f'<tr><th>メインポジション</th><td>{e(c["ポジション"] or "不明")}</td></tr>'
               f'<tr><th>サブポジション</th><td>{e(sub)}</td></tr>'
               f'<tr><th>利き腕</th><td>{e(p.get("利き腕", "不明"))}</td></tr></tbody></table>'
               f'<h3>野手能力</h3>{ab_t}{pab_t}' + sp_block("野手特殊能力", sp.get("野手"), "野手") + sp_block("投手特殊能力", sp.get("投手"), "投手")
               + sp_block("その他特殊能力", sp.get("その他"), "その他"))
    name = c["name"]
    friend_ev = text.get("友情イベント") if (c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手")) else None
    has_friend = bool(c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手"))
    ev = events_of(text, event_kinds(c, config, text, has_friend))
    parts = [
        section(f"{name}の基本情報", basic),
        section(f"{name}の重要ボーナス", imp),
        section(f"{name}のイベント詳細", event_detail(ev)),
    ]
    parts += [
        section(f"{name}の評価", paras(text.get("評価", []))),
        section(f"{name}の使用デッキ例", deck_examples(c["name"], decks, root), "このキャラを使ったデッキは準備中です。"),
        section(f"{name}の選手能力", ability),
    ]
    # 『【名前】』の見出しの前に『名前』だけ（二つ名を除く）の表記もタイトルに入れる
    return "\n".join(parts)


ICON_COPIES = []   # (元のファイル, 出力先 img/chars/番号.png)。build.py がコピーする


def find_icon(chars_path, c, pid):
    """pawa-data の event-chars/icons から、キャラのPSRアイコン（無ければSR）を探す。無ければ None"""
    here = Path(__file__).resolve().parent
    for d in (Path(chars_path).resolve().parent / "icons", here.parent / "pawa-data" / "event-chars" / "icons"):
        base = f'{c["苗字"]}{c.get("名前") or ""}' + (f'_{c["二つ名"]}' if c.get("二つ名") else "")
        for rare in ("PSR", "SR"):
            f = d / f"{base}_{rare}.png"
            if f.exists():
                ICON_COPIES.append((f, f"img/chars/{pid}.png"))
                return True
    return False


def generate(chars_path, src, decks, noindex=True):
    config = json.loads((src / "chars" / "config.json").read_text(encoding="utf-8"))
    kinds = json.loads((src / "chars" / "skill_kinds.json").read_text(encoding="utf-8"))  # 特殊能力の種類（青・金・赤・緑・虹）。pawa-data の skills.json から作る
    chars = {c["name"]: c for c in json.loads(Path(chars_path).read_text(encoding="utf-8"))}
    pages, items = [], []
    pub = set(config.get("検索に出すページ", []))   # ここに書いた番号のページだけ検索に出す（サイトマップにも入る）
    for pid, name in config["公開するキャラ"].items():
        if not re.fullmatch(r"\d{4}", pid):
            raise SystemExit(f"ページ番号は4桁の数字にしてください: {pid}")
        c = chars.get(name)
        if not c:
            print(f"警告: 公開するキャラ {name} が chars.json にありません")
            continue
        tf = next((f for f in (src / "chars" / "texts").glob("*.json") if json.loads(f.read_text(encoding="utf-8")).get("name") == name), None)
        text = json.loads(tf.read_text(encoding="utf-8")) if tf else {}
        path = f"chars/{pid}/"
        full = f'{c["二つ名"] and "[" + c["二つ名"] + "]" or ""}{c["苗字"]}{c["名前"] or ""}'
        c = dict(c, _icon=find_icon(chars_path, c, pid))
        items.append((pid, c, full))
        meta = (f"title: {full}のデータ・イベントまとめ｜パワプロアプリ攻略ベース\n"
                f"description: パワプロアプリ（サクセス・パワクエ共通）のイベキャラ {full} のボーナス、金特、イベント選択肢、選手能力をまとめています。\n"
                f"path: {path}\nnav: none\n" + ("noindex: yes\n" if noindex and pid not in pub else ""))
        body = (f'<section class="phead"><p class="eyebrow">イベキャラ データ</p><h1>{e(full)}のデータ・イベントまとめ</h1></section>\n'
                + build_page(c, text, config, decks, kinds))
        pages.append(f"<!--\n{meta}-->\n{body}")
    # データ未入力のキャラ（名前と読みだけ決まっている）。ページは「準備中」で、検索には出さない
    for pid, st in config.get("準備中のキャラ", {}).items():
        if not re.fullmatch(r"\d{4}", pid) or pid in config["公開するキャラ"]:
            raise SystemExit(f"準備中のキャラの番号が不正か重複しています: {pid}")
        full = f'{st.get("二つ名") and "[" + st["二つ名"] + "]" or ""}{st["苗字"]}{st.get("名前") or ""}'
        c = {"二つ名": st.get("二つ名") or "", "苗字": st["苗字"], "名前": st.get("名前") or "", "読み": st.get("読み"), "二つ名読み": st.get("二つ名読み") or "", "_準備中": True}
        c["_icon"] = find_icon(chars_path, c, pid)
        items.append((pid, c, full))
        meta = (f"title: {full}のデータ・イベントまとめ｜パワプロアプリ攻略ベース\n"
                f"description: パワプロアプリのイベキャラ {full} のページです。データは準備中です。\n"
                f"path: chars/{pid}/\nnav: none\n" + ("" if pid in pub else "noindex: yes\n"))
        body = (f'<section class="phead"><p class="eyebrow">イベキャラ データ</p><h1>{e(full)}のデータ・イベントまとめ</h1></section>\n'
                + stub_body(full, st))
        pages.append(f"<!--\n{meta}-->\n{body}")
    items.sort(key=lambda t: t[0])
    pages.append(index_page(items, config, noindex and not pub))
    return pages


def stub_body(full, st):
    """データ未入力キャラのページ本文。分かっている項目だけ出し、不明な所は「準備中」"""
    def pats(lst):
        return "<br>".join(f"パターン{i + 1}：{e(x)}" for i, x in enumerate(lst)) if lst else "準備中"
    rows = [("得意練習", e(" / ".join(st["得意練習"])) if st.get("得意練習") else "準備中"),
            ("イベント前後", e(st.get("前後イベ") or "準備中")),
            ("野手金特", pats(st.get("金特野手"))),
            ("投手金特", pats(st.get("金特投手")))]
    basic = '<table class="cp-basic"><tbody>' + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</tbody></table>"
    if st.get("金特野手") or st.get("金特投手"):
        basic += '<p class="cp-note">※ 金特のパターンは判明分のみ。他にもある可能性があります。</p>'
    bl = st.get("ボーナス一部") or []
    bon = ('<table class="cp-basic"><tbody>' + "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in bl) + "</tbody></table>"
           '<p class="cp-note">※ 判明している一部のみ。その他は準備中です。</p>') if bl else ""
    return (section(f"{full}の基本情報", basic)
            + section(f"{full}の重要ボーナス", bon)
            + section(f"{full}の金特イベント選択肢", "")
            + section(f"{full}の共通イベント", "")
            + section(f"{full}の自己紹介", "")
            + section(f"{full}の評価", "")
            + section(f"{full}の選手能力", ""))


def index_page(items, config, noindex):
    """イベキャラ一覧（/chars/）。検索つき。本文は静的HTML（検索は表示を絞るだけ）"""
    lis = []
    for pid, c, full in items:
        kind = "準備中" if c.get("_準備中") else char_type(c, config["種別の判定"])
        yomi = c.get("二つ名読み") or ""
        yomi = " ".join(yomi) if isinstance(yomi, list) else yomi
        key = " ".join(x for x in (full, c.get("読み"), yomi, c.get("苗字"), c.get("名前")) if x)
        lis.append(f'<li class="cl-item" data-k="{e(key)}" data-t="{e(kind)}"><a href="{pid}/">'
                   + (f'<img class="cl-icon" src="../img/chars/{pid}.png" alt="" width="52" height="52" loading="lazy">' if c.get("_icon") else '<span class="cl-icon"></span>')
                   + f'<span class="cl-name"><span class="cl-nick">{e(c["二つ名"] or "")}</span><b>{e(c["苗字"])}{e(c["名前"] or "")}</b></span>'
                   f'<span class="cl-tag">{e(kind)}</span></a></li>')
    kinds_ = sorted({char_type(c, config["種別の判定"]) for _, c, _ in items if not c.get("_準備中")}) if items else []
    chips = "".join(f'<button type="button" class="cl-chip" data-t="{e(k)}">{e(k)}</button>' for k in kinds_)
    meta = ("title: イベキャラ一覧｜パワプロアプリ攻略ベース\n"
            "description: パワプロアプリのイベキャラのボーナス・金特・イベントをまとめたページの一覧です。名前や読みで検索できます。\n"
            "path: chars/\nnav: none\n" + ("noindex: yes\n" if noindex else ""))
    body = (f'''<section class="phead"><p class="eyebrow">イベキャラ</p><h1>イベキャラ一覧</h1></section>
<div class="cl">
<input type="search" id="cl-q" class="cl-q" placeholder="名前・読み・二つ名で検索" aria-label="イベキャラを検索">
<div class="cl-chips">{chips}</div>
<p class="muted" id="cl-n">{len(items)}人</p>
<ul class="cl-list">{"".join(lis)}</ul>
</div>
<script>
(function(){{
var q=document.getElementById("cl-q"),items=[].slice.call(document.querySelectorAll(".cl-item")),n=document.getElementById("cl-n"),t="";
function hira(s){{return s.replace(/[ァ-ヶ]/g,function(c){{return String.fromCharCode(c.charCodeAt(0)-96)}}).toLowerCase()}}
function run(){{var w=hira(q.value).split(/\\s+/).filter(Boolean),c=0;
items.forEach(function(li){{var k=hira(li.dataset.k),ok=(!t||li.dataset.t===t)&&w.every(function(x){{return k.indexOf(x)>=0}});li.hidden=!ok;if(ok)c++}});
n.textContent=c+"人"}}
q.addEventListener("input",run);
[].forEach.call(document.querySelectorAll(".cl-chip"),function(b){{b.addEventListener("click",function(){{var on=b.classList.contains("on");[].forEach.call(document.querySelectorAll(".cl-chip"),function(x){{x.classList.remove("on")}});t=on?"":b.dataset.t;if(!on)b.classList.add("on");run()}})}});
}})();
</script>''')
    return f"<!--\n{meta}-->\n{body}"
