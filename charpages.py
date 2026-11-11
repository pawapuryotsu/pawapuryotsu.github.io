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


def ability_tiles(d, chart=""):
    """能力のマス。chart（変化球の図）があれば、同じ列の一番右に「変化球」のマスとして入れる"""
    out = [f'<div class="cp-tiles{" cp-tiles-p" if chart else ""}" style="--n:{len(d)}">']
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
    if chart:
        out.append(f'<div class="at at-chart"><span class="lb">変化球</span>{chart}</div>')
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


def cap_max_text(entry):
    """基礎上限の表示：そのキャラの最大値（PSRの最大Lvの値。PSRが無ければSR）。Lv35で0・Lv40で2のように途中から付くものも最大値を出す"""
    shown, unit = entry.get("表示") or {}, entry.get("単位") or ""
    mx = {r: t[max(t, key=int)] for r, t in shown.items() if t}
    if not mx:
        return bonus_lines(entry)[0]
    if len(mx) == 2 and mx["SR"] != mx["PSR"]:
        return f'{fmt(mx["SR"])}{unit}(SR) {fmt(mx["PSR"])}{unit}(PSR)'
    return f'{fmt(mx.get("PSR", mx.get("SR")))}{unit}'


def unique_mark(entry):
    """固有ボーナスの表記。固有だけの項目は「(固有)」、SR/PSRの値に固有が足されている項目は「(固有6含む)」（表示の値は固有を含んだ値）"""
    g = entry.get("固有")
    if g is None:
        return ""
    if not entry.get("SR") and not entry.get("PSR"):
        return "(固有)"
    if isinstance(g, (int, float)):
        return f"(固有{fmt(g)}{entry.get('単位') or ''}含む)"
    return ""


def item_text(c):
    """アイテム追加枠：追加枠「○○」・キャラ持参アイテム「○○」の○○（chars.json の「アイテム」）。無ければ なし"""
    names = [it["名前"] for it in c.get("アイテム") or []]
    return "<br>".join(e(n) for n in names) or "なし"


def reform_text(c):
    """練習改革：ボーナスに「○○練習改革(△△)」があれば、その名前を出す。無ければ なし"""
    names = [n for n, b in c["bonus"].items() if "練習改革" in n and (bonus_lines(b) or b.get("固有文字") or b.get("固有") is not None)]
    return "<br>".join(e(n) for n in names) or "なし"


def awake_head(entry, head):
    """覚醒で伸びた値の表記（管理人指示 2026-11-07）。表示の値は覚醒込みなので、そのことを基準値のあとに書く。
    SR覚醒（覚醒）→『150%(SR覚醒含む)』、PSR覚醒（覚醒PSR）→『10(PSR覚醒含む)』。値がSRとPSRで違う形（○○(SR) △△(PSR)）のPSR覚醒は『△△(PSR覚醒含む)』。
    （表示, 折り返さない注記）を返す。注記は途中で折り返さない（320pxで「む」だけ次の行にならないように）"""
    sr, psr = entry.get("覚醒"), entry.get("覚醒PSR")
    if psr and not sr:
        return (head[:-len("(PSR)")], "(PSR覚醒含む)") if head.endswith("(PSR)") else (head, "(PSR覚醒含む)")
    if sr and psr:
        return head, "(SR・PSR覚醒含む)"
    return (head, "(SR覚醒含む)") if sr else (head, "")


def bonus_table(rows, extra=""):
    out = ['<table class="cp-bonus"><tbody>']
    for name, entry in rows:
        r = bonus_lines(entry)
        alpha = entry.get("固有文字") == "α"   # 得意練習率アップの固有はゲーム内で値を測れないので「+α(固有)」と書く（管理人指示 2026-11-07）
        if not r and entry.get("固有文字"):  # 固有の値がゲーム内で分からない項目は文字のまま出す（αは「+α(固有)」、ほかは「あり(固有)」など）
            txt = "+α" if alpha else entry["固有文字"]
            out.append(f'<tr><th>{e(name)}</th><td><b>{e(txt)}</b>(固有)</td></tr>')
            continue
        if not r:
            continue
        head, steps = r
        h, am = awake_head(entry, head)
        if alpha:   # 0%+α は「+α」。Lvで伸びた値にも固有のαは付いたままなので「+α」を付ける
            h = "+α" if h in ("0", "0%") else h + "+α"
            steps = [(v + "+α", l) for v, l in steps]
        cell = f'<b>{e(h)}</b>' + (f'<span class="awk">{e(am)}</span>' if am else "") + (lambda m: f'<span class="awk">{e(m)}</span>' if m else "")("(固有)" if alpha else unique_mark(entry)) + "".join(
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
    def brk(p):
        # 長いパターン（スマホ幅375pxで1行に収まらないもの）だけ、「＋」の後ろで改行する
        return e(p).replace("＋", "＋<br>") if len(p) > 18 else e(p)
    return "<br>".join(brk(p) for p in pats) if pats else "なし"


def friend_text(c):
    f = c["金特"].get("友情", {})
    parts = [f"{k}で獲得：{'、'.join(f[k])}" for k in ("野手", "投手") if f.get(k)]
    return "<br>".join(e(p) for p in parts) if parts else "なし"


_RICH = {"青": "tx-b", "赤": "tx-r", "太": "tx-bold", "青太": "tx-b tx-bold", "赤太": "tx-r tx-bold"}


def rich(t):
    """文字の色・太さの指示。{青:…} {赤:…} {太:…} {青太:…} {赤太:…} を色・太字にする（それ以外は普通の文字）"""
    return re.sub(r"[{｛](青太|赤太|青|赤|太)[:：]([^{}｛｝]*)[}｝]",
                  lambda m: f'<span class="{_RICH[m.group(1)]}">{m.group(2)}</span>', e(t))


def paras(lst):
    return "".join(f"<p>{rich(t)}</p>" for t in lst)


def event_kinds(c, config, text, has_friend):
    """そのキャラのページに並べるイベントの種類（分類ごと。config.json「イベント構成」）"""
    kinds = list(config["イベント構成"].get(c.get("分類") or "選手", config["イベント構成"]["選手"]))
    if has_friend and "友情イベント" not in kinds and (c.get("分類") or "選手") == "選手":
        kinds.insert(kinds.index("共通イベント") + 1 if "共通イベント" in kinds else len(kinds), "友情イベント")
    # エピローグ：彼女・選手彼女・相棒は構成に含まれる。選手は、共通イベントの小イベントの1つとして texts に書く
    # 構成に無い種類（例：選手のバレンタイン）が texts にあれば、texts で1つ前に書いた種類のすぐ後ろに足す
    prev = None
    for x in text.get("イベント", []):
        k = x.get("種類")
        if k and k not in kinds:
            kinds.insert(kinds.index(prev) + 1 if prev in kinds else len(kinds), k)
        prev = k or prev
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


_FRIEND = [set()]  # このキャラの友情特殊能力の名前（イベントの表で青太字にする）


def _kind_of(name):
    """特殊能力名の種類（赤特・緑特など）。skill_kinds.json に無ければ None"""
    _is_gold_kotsu("威圧感コツ")  # _KINDS を読み込む
    name = name.replace("〇", "○")  # skill_kinds.json は「○」（記号）。入力の「〇」（漢数字のゼロ）でも同じに扱う
    for g in _KINDS.values():
        if name in g:
            return g[name]
    return None


def _item(i):
    """「○○コツLv3」は、狭い幅では能力名とコツLvの間でだけ折り返す（<wbr>）。長い名前は伸ばし棒「ー」のあとでも折り返せる（「ポーカーフェイスコツ」が表の外に切れないように）"""
    t = e(i).replace("コツLv", "<wbr>コツLv").replace("取得", "<wbr>取得").replace("ー", "ー<wbr>")
    if re.match(r"^オリジナル(ストレート|変化球)", i) and i.endswith("取得"):  # オリジナルストレート取得・オリジナル変化球(○○方向)取得は青字（管理人指示 2026-11-07）
        return f'<div class="tx-b tx-bold">{t.replace("(", "<wbr>(")}</div>'
    m = re.match(r"^(.+?)取得$", i)
    if m and _kind_of(m.group(1)) in ("赤特", "緑特"):  # 「○○取得」は、赤特は赤文字、緑特は緑文字
        return f'<div class="{"tx-r" if _kind_of(m.group(1)) == "赤特" else "tx-g"}">{t}</div>'
    is_friend = any(i.startswith(n + "コツ") for n in _FRIEND[0])
    cls = "cp-kotsu cp-kotsu-gold" if (_is_gold_kotsu(i) or is_friend) else ("cp-kotsu" if "コツLv" in i else "")
    return f'<div class="{cls}">{t}</div>' if cls else f"<div>{t}</div>"


def _choice_name(t):
    """選択肢の名前。（イベント継続）（成功）は青、（イベント終了）（失敗）は赤で、改行して出す。
    成功・失敗の表記は「（成功）」「（失敗）」に統一（「成功時」「失敗時」と書いても同じ表示）"""
    m = re.match(r"^(.*?)\s*[（(](イベント継続|イベント終了|成功時|失敗時|成功|失敗)[）)]$", t, re.S)
    if not m and t.strip() in ("成功時", "失敗時", "成功", "失敗"):
        m = re.match(r"^()(.+)$", t.strip())
    if not m:
        return e(t).replace("\n", "<br>")
    lab = m.group(2).rstrip("時")
    cls = "cp-cont" if lab in ("イベント継続", "成功") else "cp-end"
    return (f'{e(m.group(1))}<br>' if m.group(1) else "") + f'<span class="{cls}">（{lab}）</span>'


_CELL_ORDER = ("三塁手", "その他野手", "投手", "野手")
# 【野手】【投手】の並び順はキャラの種別で固定（野手用＝野手が上、投手用＝投手が上。兼用は管理人に確認）
_CELL_ORDER_BY_TYPE = {
    "野手用": ("三塁手", "その他野手", "捕手", "捕手以外の野手", "野手", "投手"),
    "投手用": ("投手", "三塁手", "その他野手", "捕手", "捕手以外の野手", "野手"),
}
_CTYPE = [None]
_CELL_SKIP = ("選択肢", "効果", "正解", "その他")


def _cell(x):
    """1行ぶんの「その他」欄。【投手】【野手】【三塁手】など見出しごとの項目と、見出し無しのその他を縦に並べる"""
    out = "".join(_item(i) for i in x.get("その他", []))  # 見出し無し（ランダムコツ等）は一番上。下だと最後の【野手】等だけの物に見えるため（管理人指示）
    order = _CELL_ORDER_BY_TYPE.get(_CTYPE[0], _CELL_ORDER)
    labs = [k for k in order if k in x] + [k for k in x if k not in order and k not in _CELL_SKIP]
    for lab in labs:
        if x.get(lab):
            out += f'<div class="cp-t-lab">【{lab}】</div>' + "".join(_item(i) for i in x[lab])
    return out


def _eff(i):
    """効果の1項目。体力・体力最大値・やる気は、＋が付けば青、－（-）が付けば赤で出す"""
    if re.search(r"[{｛](青太|赤太|青|赤|太)[:：]", i):  # {青:…} などの色指示（例：{青:精神練習Lv1アップ}）
        return rich(i)
    if re.match(r"^(いいヤツ|世渡り上手|モテモテ|センス〇|ムード〇)", i):  # サクセス中のプラス効果＝青
        return f'<span class="tx-b">{e(i)}</span>'
    m = re.match(r"^(.+?)(?:になる|取得)$", i) or re.match(r"^(.+?)になる", i)  # 「○○になる」「○○取得」：○○が緑特なら緑文字、赤特なら赤文字
    if m and _kind_of(m.group(1)) in ("赤特", "緑特"):
        return f'<span class="{"tx-r" if _kind_of(m.group(1)) == "赤特" else "tx-g"}">{e(i)}</span>'
    if i.startswith("センス×"):  # サクセス中のマイナス効果＝赤
        return f'<span class="tx-r">{e(i)}</span>'
    m = re.match(r"^(体力最大値|体力|やる気)([+＋\-－−ー]+)", i)
    if not m:
        return e(i)
    return f'<span class="{"tx-b" if m.group(2)[0] in "+＋" else "tx-r"}">{e(i)}</span>'


def sub_table(rows):
    """イベントの表。選択肢ごとに1行。左＝選択肢名、中＝効果（＋）、右＝投手／野手などその他。選択肢が無いイベントは左の列を出さない"""
    has_name = any(r.get("選択肢") for r in rows)
    has_other = any(_cell(r) for r in rows)  # コツなどが無いイベントは「その他」列を出さない
    head = ("<th></th>" if has_name else "") + "<th>＋</th>" + ("<th>その他</th>" if has_other else "")
    body = ""
    for r in rows:
        name = f'<th class="{"ok" if r.get("正解") else ""}">{"◎ " if r.get("正解") else ""}{_choice_name(r.get("選択肢", ""))}</th>' if has_name else ""
        eff = "".join(f'<div{" class=cp-note" if i.startswith("※") else ""}>{_eff(i)}</div>' for i in r.get("効果", []))
        body += f"<tr>{name}<td>{eff}</td>" + (f"<td>{_cell(r)}</td>" if has_other else "") + "</tr>"
    return f'<div class="cp-tbl-wrap"><table class="cp-tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def side_html(t):
    """見出し横の文。「、」で区切った1まとまりごとに折り返さない（「御／幸塾」のように名前の途中で折り返さないため）"""
    return "、<wbr>".join(f'<span class="cp-nw">{e(p)}</span>' for p in t.split("、"))


def move_epilogue(ev):
    """共通イベントの中の「エピローグ」は、イベント欄の一番下に【エピローグ】（赤系の帯）として出す（管理人指示 2026-11-11）"""
    com = ev.get("共通イベント") or {}
    subs = com.get("小イベント") or []
    epi = [x for x in subs if x.get("名前") == "エピローグ"]
    if not epi or ev.get("エピローグ"):
        return
    com["小イベント"] = [x for x in subs if x.get("名前") != "エピローグ"]
    ev.pop("エピローグ", None)
    ev["エピローグ"] = {"種類": "エピローグ", "小イベント": [{k: v for k, v in x.items() if k != "名前"} for x in epi]}


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
        cls = {"金特イベント": " cp-ev-gold", "共通イベント": " cp-ev-common", "友情イベント": " cp-ev-friend", "エピローグ": " cp-ev-red"}.get(k, "")
        if k in ("告白", "クリスマス", "初詣", "バレンタイン") or k.startswith("デート"):  # 告白・デート・クリスマス・初詣・バレンタインはピンク、エピローグは赤の帯（管理人指示）
            cls = " cp-ev-pink"
        parts.append(f'<h3 class="cp-ev{cls}">{e(k)}' + (f'{"" if k == "友情イベント" else " "}<span class="cp-h3-side">{side_html(x["見出し横"])}</span>' if x.get("見出し横") else "") + "</h3>" + (inner or '<p class="muted">準備中です。</p>'))
    return "".join(parts)


_COMBOS = []    # generate() が src/chars/combos.json から読む（コンボイベント）
_BASE_PID = {}  # 二つ名なしの名前（苗字＋名前）→ 最初のページ番号（コンボの相手へのリンク用）


def base_name(c):
    return f'{c["苗字"]}{c.get("名前") or ""}'


def alias_names(c):
    """二つ名なしの名前と、chars.json の「別表記」の名前（例：暗黒スバル→星井スバル。読みの（）は外す）。同じキャラとして扱う"""
    names = [base_name(c)]
    alt = re.sub(r"[(（].*?[)）]", "", c.get("別表記") or "").strip()
    if alt and alt not in names:
        names.append(alt)
    return names


def combos_of(c):
    """そのキャラが入っているコンボ。別バージョン（二つ名違い）や別表記（暗黒スバル＝星井スバル）でも出る。コンボの「対象外」に書いたバージョンは出さない"""
    names = alias_names(c)
    return [x for x in _COMBOS if any(n in x["キャラ"] for n in names) and c["name"] not in x.get("対象外", [])]


def combo_html(x, root, me=None):
    """コンボイベント1つ分。見出し・コンボキャラ・イベント前後・表。me はそのキャラページの持ち主（太字にする）"""
    def who(n):
        t = e(n)
        if n == me or (isinstance(me, (list, tuple)) and n in me):
            t = f"<b>{t}</b>"
        elif n in _BASE_PID:
            t = f'<a href="{root}chars/{_BASE_PID[n]}/">{t}</a>'
        return f'<span class="cp-nw">{t}</span>'
    basic = ('<table class="cp-basic"><tbody>'
             f'<tr><th>コンボキャラ</th><td>{"、<wbr>".join(who(n) for n in x["キャラ"])}</td></tr>'
             f'<tr><th>イベント前後</th><td>{e(x.get("前後") or "不明")}</td></tr></tbody></table>')
    subs = ""
    for sub in x.get("小イベント", []):
        if sub.get("名前"):
            subs += f'<h4 class="cp-sub">・{e(sub["名前"])}</h4>'
        subs += paras(sub.get("詳細", [])) + (sub_table(sub["行"]) if sub.get("行") else "")
    if not subs:
        subs = '<p class="muted">準備中です。</p>'
    return f'<div class="cp-combo"><h3 class="cp-ev cp-ev-combo">{e(x["名前"])}</h3>{basic}{subs}</div>'


def section(title, inner, empty="準備中です。"):
    # 見出しの最後の「の○○」（の評価・の基本情報…）は折り返さない（「価」だけ次の行になる等を防ぐ）
    head, sep, tail = title.rpartition("の")
    h = f'{e(head)}<span class="cp-tail">{e(sep + tail)}</span>' if head else e(title)
    return f'<section class="cp-sec"><h2>{h}</h2>{inner or f"<p class=muted>{e(empty)}</p>"}</section>'


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
        n = min(int(x["変化量"]), 7) if x and x.get("変化量") else 0  # 7目盛り＝□6個＋先端の△1個（変化量7で△まで塗る。管理人指示 2026-11-07）
        a = (180 - ang) if lefty else ang
        segs = []
        for i in range(6):
            col = seg_color(i, n) if i < n else "#46a8ff"
            segs.append(f'<rect x="{22 + i * 15}" y="-9" width="14" height="18" fill="{col}" stroke="#0b3f9e" stroke-width="1.5"/>')
        tipcol = seg_color(6, n) if n >= 7 else "#46a8ff"
        tip = f'<path d="M112 -9L119 -9L127 0L119 9L112 9Z" fill="{tipcol}" stroke="#0b3f9e" stroke-width="1.5"/>'
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


def char_type_by_practice(c, rules):
    """得意練習（メイン・サブ）で分類（管理人指示 2026-11-05）。投手の練習だけ→投手用、野手の練習だけ→野手用、両方→兼用。
    得意練習のデータが無い時は None"""
    pr = c.get("得意練習") or []
    if not pr:
        return None
    unknown = [x for x in pr if x not in rules["投手の得意練習"] and x not in rules["野手の得意練習"]]
    if unknown:
        raise SystemExit(f'{c["name"]} の得意練習 {unknown} が config.json の「投手の得意練習」「野手の得意練習」にありません')
    p = any(x in rules["投手の得意練習"] for x in pr)
    f = any(x in rules["野手の得意練習"] for x in pr)
    return "投手用" if p and not f else ("野手用" if f and not p else "兼用")


def char_type(c, rules):
    """野手用／投手用／兼用。まず得意練習で決める。得意練習のデータが無いキャラだけ、従来のルール（ボーナス条件→金特）で決める"""
    t = char_type_by_practice(c, rules)
    if t:
        return t
    def ok(conds):
        return all((max_value(c["bonus"].get(k, {})) or 0) >= v for k, v in conds.items())
    p, f = ok(rules["投手条件"]), ok(rules["野手条件"])
    if p != f:
        return "投手用" if p else "野手用"
    # ボーナスで決まらない時は金特で分類（投手系だけ→投手用、野手系だけ→野手用、両方→兼用）
    g = c.get("金特", {})
    gp = any(x in (g.get("投手") or []) for x in rules.get("投手系の金特", []))
    gf = any(x in (g.get("野手") or []) for x in rules.get("野手系の金特", []))
    return "投手用" if gp and not gf else ("野手用" if gf and not gp else "兼用")


TIERS = ("SS", "S", "A", "B", "C")
_RANKING = {}   # generate() が src/ranking/ranking.json から読む


def rankings_of(name):
    """このキャラが載っているランキング［(ランキング, ランク, 理由)］。評価欄に出す"""
    out = []
    for r in _RANKING.get("ranking", {}).values():
        if r.get("キャラページに出さない"):   # 記事用のランキング（次期環境の予想など）はキャラページの評価欄に出さない
            continue
        for t in TIERS:
            for x in r.get("ランク", {}).get(t, []):
                if x["name"] == name:
                    out.append((r, t, x.get("理由", [])))
    return out


def date_label(r):
    return f'<span class="rk-date">【評価日{e(r["評価日"])}】</span>' if r.get("評価日") else ""


def ranking_eval_html(name, root):
    """キャラページの評価欄に出す、ランキングでの位置づけ"""
    out = ""
    for r, t, why in rankings_of(name):
        out += (f'<div class="rk-box"><div class="rk-head"><span class="tier tier-{t}">{t}</span>'
                f'<a href="{root}{r["path"]}">{e(r["短い名前"])}</a>{date_label(r)}</div>' + paras(why) + "</div>")
    return out


def build_page(c, text, config, decks, kinds, root="../../"):
    p = c.get("プロフィール", {})
    bonus = c["bonus"]
    ctype = char_type(c, config["種別の判定"])
    # 並び順用の種別。兼用は、メインポジションが投手なら【投手】が上、投手以外なら【野手】が上（管理人指示 2026-11-05）。
    # 得意練習のデータが無いキャラ（ポジションでは決めない）は config「兼用の並び順」に管理人の指示があればそれ（無ければ聞く）
    order_type = ctype
    if ctype == "兼用":
        name = c["苗字"] + (c["名前"] or "")
        if c.get("得意練習") and c.get("ポジション"):
            order_type = "投手用" if c["ポジション"] == "投" else "野手用"
        else:
            order_type = {"投手": "投手用", "野手": "野手用"}.get(config.get("兼用の並び順", {}).get(name, ""), "兼用")
            if order_type == "兼用":
                print(f"警告: {name} は兼用判定で、メインポジションか得意練習のデータがありません。【野手】【投手】の並びを管理人に確認して config.json の「兼用の並び順」に書いてください")
    _CTYPE[0] = order_type
    _FRIEND[0] = {n for k in ("野手", "投手") for n in c["金特"].get("友情", {}).get(k, [])}
    top_names, tap = config["重要ボーナス"][ctype], config["タップ欄のボーナス"][ctype]
    important = [(n, bonus[n]) for n in top_names if n in bonus and (bonus_lines(bonus[n]) or bonus[n].get("固有文字"))]
    unknown = [n for n in bonus if n not in top_names and n not in tap]
    if unknown:
        print(f"【警告】{c['name']}：config.json にないボーナス {unknown}（タップ欄の一番下に出します）")
    others = sorted(((n, b) for n, b in bonus.items() if n not in top_names and (bonus_lines(b) or b.get("固有文字"))),
                    key=lambda nb: tap.index(nb[0]) if nb[0] in tap else len(tap))
    caps = [(n, bonus[n]) for n in config["基礎上限の項目"] if n in bonus and bonus_lines(bonus[n])]
    cap_txt = "<br>".join(f'{e(n.replace("アップ", ""))}：{e(cap_max_text(b))}' for n, b in caps) or "なし"
    awake_cap = any(b.get("覚醒") or b.get("覚醒PSR") for _, b in caps)  # 基礎上限に覚醒で付く分があるキャラだけ ※ を出す
    ev = {"後": "後", "前": "前"}.get(p.get("前後イベ"), p.get("前後イベ") or "不明")
    basic = (f'<table class="cp-basic"><tbody>'
             f'<tr><th>得意練習</th><td>{e(" / ".join(c["得意練習"]) or "なし")}</td></tr>'
             f'<tr><th>イベント前後</th><td>{e(ev)}</td></tr>'
             f'<tr><th>基礎上限{"<sup>※</sup>" if awake_cap else ""}</th><td>{cap_txt}</td></tr>'
             + "".join(f'<tr><th>{k}金特</th><td>{gold_text(c, k)}</td></tr>' for k in (("投手", "野手") if order_type == "投手用" else ("野手", "投手"))) +
             f'<tr><th>友情特殊能力</th><td>{friend_text(c)}</td></tr>'
             f'<tr><th>練習改革</th><td>{reform_text(c)}</td></tr>'
             f'<tr><th>アイテム追加枠</th><td>{item_text(c)}</td></tr>'
             f'</tbody></table>'
             + ('<p class="cp-note">※ 覚醒で付く分も表記</p>' if awake_cap else ""))
    # 重要ボーナスの一番下に、追加枠「○○」／キャラ持参アイテム「○○」を出す（管理人指示 2026-11-10）。データに無いキャラは出さない
    item_rows = "".join(f'<tr><th>{e(it.get("種類") or "アイテム")}</th><td><b>{e(it["名前"])}</b></td></tr>'
                        for it in c.get("アイテム") or [] if it.get("名前"))
    imp = bonus_table(important, item_rows) + (
        f'<details class="cp-more"><summary>その他ボーナスはこちらをタップ</summary>{bonus_table(others)}</details>' if others else "")
    ability = ability_html(c, kinds)
    name = c["name"]
    friend_ev = text.get("友情イベント") if (c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手")) else None
    has_friend = bool(c["金特"].get("友情", {}).get("野手") or c["金特"].get("友情", {}).get("投手"))
    ev = events_of(text, event_kinds(c, config, text, has_friend))
    move_epilogue(ev)
    parts = [
        section(f"{name}の基本情報", basic),
        section(f"{name}の重要ボーナス", imp),
        section(f"{name}のイベント詳細", event_detail(ev)),
    ]
    cbs = combos_of(c)
    if cbs:
        parts.append(section(f"{name}のコンボイベント", "".join(combo_html(x, root, alias_names(c)) for x in cbs)))
    parts += [
        section(f"{name}の評価", ranking_eval_html(c["name"], root) + paras(text.get("評価", []))),
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


def yomi_of(c):
    """読み（ひらがな）。二つ名があれば [にじゅうめい]よみ の形。無ければ空文字"""
    y = c.get("読み") or ""
    if not y:
        return ""
    nick = c.get("二つ名読み") or ""
    if isinstance(nick, list):
        nick = "".join(nick)
    return (f"[{nick}]" if nick else "") + y


def yomi_paren(c):
    y = yomi_of(c)
    return f"（{y}）" if y else ""


def head_html(full, c, pid=None):
    y = yomi_of(c)
    icon = (f'<img class="cp-icon" src="../../img/chars/{pid}.png" alt="{e(full)}のアイコン" width="72" height="72" decoding="async">'
            if pid and c.get("_icon") else "")
    text = (f'<p class="eyebrow">イベキャラ データ</p><h1><span class="cp-h1">{e(full)}</span> <span class="cp-h1">データ・イベントまとめ</span></h1>'
            + (f'<p class="cp-yomi">読み：{e(y)}</p>' if y else ""))
    if not icon:
        return f'<section class="phead">{text}</section>\n'
    return f'<section class="phead cp-headrow">{icon}<div class="cp-headtxt">{text}</div></section>\n'


def generate(chars_path, src, decks, noindex=True):
    config = json.loads((src / "chars" / "config.json").read_text(encoding="utf-8"))
    kinds = json.loads((src / "chars" / "skill_kinds.json").read_text(encoding="utf-8"))  # 特殊能力の種類（青・金・赤・緑・虹）。pawa-data の skills.json から作る
    chars = {c["name"]: c for c in json.loads(Path(chars_path).read_text(encoding="utf-8"))}
    global _RANKING
    rf = src / "ranking" / "ranking.json"
    _RANKING = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}
    global _COMBOS
    cf = src / "chars" / "combos.json"
    _COMBOS = json.loads(cf.read_text(encoding="utf-8")).get("コンボ", []) if cf.exists() else []
    _BASE_PID.clear()
    for pid, nm in config["公開するキャラ"].items():
        if nm in chars:
            for n in alias_names(chars[nm]):
                _BASE_PID.setdefault(n, pid)
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
                f"description: パワプロアプリ（サクセス・パワクエ共通）のイベキャラ {full}{yomi_paren(c)} のボーナス、金特、イベント選択肢、選手能力をまとめています。\n"
                f"path: {path}\nnav: none\n" + ("noindex: yes\n" if noindex and pid not in pub else ""))
        body = (head_html(full, c, pid)
                + build_page(c, text, config, decks, kinds))
        pages.append(f"<!--\n{meta}-->\n{body}")
    # データ未入力のキャラ（名前と読みだけ決まっている）。ページは「準備中」で、検索には出さない
    for pid, st in config.get("準備中のキャラ", {}).items():
        if not re.fullmatch(r"\d{4}", pid) or pid in config["公開するキャラ"]:
            raise SystemExit(f"準備中のキャラの番号が不正か重複しています: {pid}")
        full = f'{st.get("二つ名") and "[" + st["二つ名"] + "]" or ""}{st["苗字"]}{st.get("名前") or ""}'
        c = {"二つ名": st.get("二つ名") or "", "苗字": st["苗字"], "名前": st.get("名前") or "", "読み": st.get("読み"), "二つ名読み": st.get("二つ名読み") or "", "実装日": st.get("実装日"), "_準備中": True}
        c["_icon"] = find_icon(chars_path, c, pid)
        items.append((pid, c, full))
        meta = (f"title: {full}のデータ・イベントまとめ｜パワプロアプリ攻略ベース\n"
                f"description: パワプロアプリのイベキャラ {full}{yomi_paren(c)} のページです。データは準備中です。\n"
                f"path: chars/{pid}/\nnav: none\n" + ("" if pid in pub else "noindex: yes\n"))
        body = (head_html(full, c, pid)
                + stub_body(full, st, *stub_char(chars, st, kinds)))
        pages.append(f"<!--\n{meta}-->\n{body}")
    items.sort(key=lambda t: t[0])
    pages += ranking_pages(items, config, chars, chars_path)
    if _COMBOS:
        pages.append(combo_page())
    pages.append(index_page(items, config, noindex and not pub))
    return pages


def combo_page():
    """コンボイベントだけをまとめたページ（/chars/combo/）。キャラページの「コンボイベント」欄と同じ内容"""
    global _CTYPE
    _CTYPE[0] = None
    meta = ("title: コンボイベント一覧｜パワプロアプリ攻略ベース\n"
            "description: パワプロアプリのイベキャラの組み合わせで発生するコンボイベントを、組み合わせ・イベント前後・効果ごとにまとめています。\n"
            "path: chars/combo/\nnav: none\nnoindex: yes\n")
    body = ('<section class="phead"><p class="eyebrow">イベキャラ</p><h1>コンボイベント一覧</h1></section>\n'
            '<p class="cp-sec-lead">特定のイベキャラの組み合わせで発生するイベントです。イベント前後は、イベキャラの前後とは関係なく、コンボごとに決まっています。二つ名が異なる別バージョンでも基本的に同じように発生します。</p>'
            + "".join(f'<section class="cp-sec">{combo_html(x, "../../")}</section>' for x in _COMBOS))
    return f"<!--\n{meta}-->\n{body}"


def stub_char(chars, st, kinds):
    """準備中キャラが入力シート（chars.json）に一部入っていれば、そのデータ（選手能力欄に使う）。無ければ (None, None)"""
    name = (f'[{st["二つ名"]}]' if st.get("二つ名") else "") + st["苗字"] + (st.get("名前") or "")
    c = chars.get(name)
    if not c or not (c.get("プロフィール") or {}).get("野手能力") and not (c.get("プロフィール") or {}).get("投手能力"):
        return (None, None)
    _CTYPE[0] = None
    return (c, kinds)


def ability_html(c, kinds):
    """選手能力欄（選手ランク・ポジション・利き腕・能力・特殊能力）。準備中ページでも使う"""
    p = c.get("プロフィール", {})
    sub = "、".join(f"{k}{v}" for k, v in (p.get("サブポジ") or {}).items()) or "なし"
    ab = p.get("野手能力") or {}
    pab = p.get("投手能力") or {}
    ab_t = ability_tiles(ab) if ab else ""
    pab_t = ("<h3>投手能力</h3>" + ability_tiles(pab, pitch_chart(p))) if pab else ""
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
    return ability


def stub_body(full, st, c=None, kinds=None):
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
            + section(f"{full}の選手能力", ability_html(c, kinds) if c else ""))


def index_page(items, config, noindex):
    """イベキャラ一覧（/chars/）。検索つき。本文は静的HTML（検索は表示を絞るだけ）"""
    lis = []
    # 実装日（入力シート「キャラ管理」D列）が新しい順＝左上が最新。実装日が空のキャラは最後（同じ日は番号が新しい方が先）
    items = sorted(items, key=lambda t: (t[1].get("実装日") or "", t[0]), reverse=True)
    items = [t for t in items if t[1].get("実装日")] + [t for t in items if not t[1].get("実装日")]
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
<p class="cl-notice"><span>※過去に登場したキャラクターの大半は</span><span>まだ情報入っていませんので</span><span>ご了承ください。</span><br><span>随時更新していきますので</span><span>よろしくお願いします。</span></p>
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


def guide_html(r):
    """ランキングの解説欄（評価基準・加点要素など）。Tier表の下に、見出しごとのまとまりで出す"""
    out = ""
    for g in r.get("解説欄", []):
        body = ""
        if g.get("箇条書き"):
            body += '<ul class="rk-list">' + "".join(f"<li>{rich(x)}</li>" for x in g["箇条書き"]) + "</ul>"
        body += paras(g.get("文章", []))
        out += f'<section class="cp-sec"><h2>{e(g["見出し"])}</h2>{body}</section>'
    return out


BASE_BONUS = ("筋力ボーナス", "敏捷ボーナス", "技術ボーナス", "変化球ボーナス", "精神ボーナス")


def _shown_at(entry, rare, lv):
    """chars.json の「表示」（Lvの値＋覚醒＋固有）で、指定Lv以下の一番高いLvの値（無ければ0）"""
    best, val = -1, 0
    for k, v in ((entry or {}).get("表示") or {}).get(rare, {}).items():
        if best < int(k) <= lv:
            best, val = int(k), v
    return val


def base_kotsu(c, rare, lv):
    """（基礎合計, コツボナ）。基礎合計＝筋力・敏捷・技術・変化球・精神ボーナスの合計（Tier表メーカーと同じ）"""
    b = c.get("bonus", {})
    return sum(_shown_at(b.get(k), rare, lv) for k in BASE_BONUS), _shown_at(b.get("コツイベントボーナス"), rare, lv)


def recommended_lv(c):
    """基礎合計とコツボナが両方PSR50の値に届く一番低いLv。SRで届けば数字、SRでは届かずPSRで届けば「PSR40」など（管理人OK 2026-11-11）"""
    top = base_kotsu(c, "PSR", 50)
    for lv in (35, 37, 40, 45):
        if base_kotsu(c, "SR", lv) == top:
            return str(lv)
    for lv in (40, 42, 45, 50):
        if base_kotsu(c, "PSR", lv) == top:
            return "50" if lv == 50 else f"PSR{lv}"
    return "－"


def bonus_table_html(r, chars, icons=None):
    """ランキングの「ボーナス表」：前後・基礎合計・コツボナ（PSR50＝覚醒すべて込み、Lv35＝PSR覚醒なし・SR覚醒あり）・推奨Lv（管理人指示 2026-11-11）"""
    rows = ""
    for t in TIERS:
        for x in r["ランク"].get(t, []):
            c = chars[x["name"]]
            top, low = base_kotsu(c, "PSR", 50), base_kotsu(c, "SR", 35)
            nick = f'<small>[{e(c["二つ名"])}]</small>' if c.get("二つ名") else ""
            ev = (c.get("プロフィール") or {}).get("前後イベ") or "－"
            rows += (f'<tr><td class="bt-t"><span class="tier tier-{t}">{t}</span></td><th><div class="bt-nm">{icons.get(x["name"], "") if icons else ""}<div>{nick}<span>{"".join(f"<b>{e(w)}</b>" for w in re.findall(r"[^・=]+[・=]?", c["苗字"] + (c["名前"] or "")))}</span></div></div></th>'
                     f'<td>{e(ev)}</td><td class="bt-mx">{fmt(top[0])}</td><td>{fmt(low[0])}</td>'
                     f'<td class="bt-mx">{fmt(top[1])}</td><td>{fmt(low[1])}</td><td>{e(recommended_lv(c))}</td></tr>')
    return ('<section class="cp-sec"><h2>ボーナス一覧</h2><div class="bt-wrap"><table class="bt">'
            '<thead><tr><th rowspan="2"></th><th rowspan="2">キャラ</th><th rowspan="2">前後</th><th colspan="2">基礎合計</th><th colspan="2">コツボナ</th><th rowspan="2">推奨Lv</th></tr>'
            '<tr><th>PSR50</th><th>Lv35</th><th>PSR50</th><th>Lv35</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            '<ul class="rk-list bt-note"><li>基礎合計：筋力・敏捷・技術・変化球・精神ボーナスの合計</li>'
            '<li>PSR50：覚醒をすべて含む値。Lv35：SR覚醒は含み、PSR覚醒は含まない値</li>'
            '<li>推奨Lv：基礎合計とコツボナが両方とも最大値になるLv</li></ul></section>')


def _autolink(h):
    """文章の中の https://… をリンクにする（ランキングの「上の解説欄」用。公式Xのポストなど）"""
    return re.sub(r"https?://[^\s<>\"]+", lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>', h)


def top_guide_html(r):
    """Tier表の上に出す解説（「上の解説欄」。見出し・文章・箇条書き）。書き方は「解説欄」と同じ"""
    out, need_x = "", False
    for g in r.get("上の解説欄", []):
        body = ""
        for t in g.get("文章", []):
            m = re.fullmatch(r"https://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)\S*", t.strip())
            if m:
                # 公式Xのポストは埋め込み表示（管理人指示 2026-11-11）。読み込めない時はリンクだけ出る
                url = f"https://twitter.com/{m.group(1)}/status/{m.group(2)}"
                body += (f'<div class="rk-xpost"><blockquote class="twitter-tweet" data-lang="ja" data-dnt="true">'
                         f'<a href="{url}">{e(t.strip())}</a></blockquote></div>')
                need_x = True
            else:
                body += f"<p>{_autolink(rich(t))}</p>"
        if g.get("箇条書き"):
            body += '<ul class="rk-list">' + "".join(f"<li>{_autolink(rich(x))}</li>" for x in g["箇条書き"]) + "</ul>"
        out += f'<section class="cp-sec"><h2>{e(g["見出し"])}</h2>{body}</section>'
    if need_x:
        out += '<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
    if r.get("動画"):   # 解説動画（YouTubeの動画ID）。サムネイル画像を押すとYouTubeが開く（埋め込みにしないのでページが重くならない）
        vid = e(r["動画"])
        out += (f'<section class="cp-sec"><h2>【解説動画】</h2><a class="rk-video" href="https://youtu.be/{vid}" target="_blank" rel="noopener">'
                f'<img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="解説動画（YouTube）" width="480" height="360" loading="lazy"></a></section>')
    return out


def ranking_pages(items, config, chars, chars_path):
    """ランキングページ（/ranking/〇〇/）。Tier表（顔アイコン）と、キャラごとの解説。
    キャラページがまだ無いキャラも載せられる（アイコンはリンクなし。ページができたら自動でリンクされる）"""
    import hashlib
    by_name = {}
    for pid, c, full in items:
        if not c.get("_準備中"):
            by_name[c["name"]] = (pid, c, full)
    pages = []
    for key, r in _RANKING.get("ranking", {}).items():
        rows, notes, n = "", "", 0
        bt_icons = {}   # ボーナス一覧の名前の左に出すアイコン（Tier表と同じ画像）
        for t in TIERS:
            if t == "C" and not r["ランク"].get("C"):
                continue   # Cランクは使うランキングだけに出す（ロマン・アンドロメダはSS〜Bの4段のまま）
            icons = ""
            for x in r["ランク"].get(t, []):
                nm = x["name"]
                if nm in by_name:
                    pid, c, full = by_name[nm]
                else:
                    c = chars.get(nm)
                    if not c:
                        raise SystemExit(f"ランキング {key} のキャラ {nm} が chars.json にありません")
                    pid = None
                    rid = "r" + hashlib.md5(nm.encode("utf-8")).hexdigest()[:8]
                    c = dict(c, _icon=find_icon(chars_path, c, rid))
                    full = f'{c["二つ名"] and "[" + c["二つ名"] + "]" or ""}{c["苗字"]}{c["名前"] or ""}'
                n += 1
                img_id = pid or rid
                icon = (f'<img src="../../img/chars/{img_id}.png" alt="" width="60" height="60" loading="lazy">' if c.get("_icon") else '<span class="rk-noicon"></span>')
                # 名前は「・」「=」の後でだけ折り返す（リムル=テンペスト など）
                label = (f'<small>[{e(c["二つ名"])}]</small>' if c.get("二つ名") else "") + f'<span{" class=lg" if len(c["苗字"] + (c["名前"] or "")) > 6 else ""}>{"".join(f"<b>{e(w)}</b>" for w in re.findall(r"[^・=]+[・=]?", c["苗字"] + (c["名前"] or "")))}</span>'
                why = x.get("理由", [])
                href = f' href="../../chars/{pid}/"' if pid else ""   # アイコンを押すとそのキャラのページへ（ページがまだ無いキャラはリンクなし）
                tag = "a" if href else "div"
                # 目印：●高校キャラ（そのランキングの学園に所属・青）、☆至高（至高のスターター／リリーバー／クローザーが取れる・赤）
                marks = ""
                if r.get("学園") and c.get("所属高校") == r["学園"]:
                    marks += '<em class="rk-school">●高校キャラ</em>'
                if r.get("種別") == "野手":
                    # 野手ランキング：野手の至高金特（球界の頭脳・至高の〇〇手）が取れたら☆至高金特。オリスト・オリ変は野手育成で取れないので付けない（管理人指示 2026-11-10）
                    if any(k in config["種別の判定"]["野手系の金特"] for k in c.get("金特", {}).get("野手", [])):
                        marks += '<em class="rk-supreme">☆至高金特</em>'
                else:
                    if any(k in ("至高のスターター", "至高のリリーバー", "至高のクローザー") for k in c.get("金特", {}).get("投手", [])):
                        marks += '<em class="rk-supreme">☆至高金特</em>'
                    pit = c.get("金特", {}).get("投手", [])
                    pats = [p_.get("投手", []) for p_ in c.get("金特", {}).get("パターン", [])]
                    supreme = any(k in ("至高のスターター", "至高のリリーバー", "至高のクローザー") for k in pit)

                    def with_supreme(match):
                        # 至高金特を取れるキャラは、同じ獲得パターンで両立できる時だけ★を出す（両立できなければ☆至高金特を優先）
                        return any(match(k) for k in pit) and (not supreme or any(
                            any(match(k) for k in pt) and any(k in ("至高のスターター", "至高のリリーバー", "至高のクローザー") for k in pt) for pt in pats))
                    if with_supreme(lambda k: k == "オリジナルストレート"):
                        marks += '<em class="rk-supreme">★オリスト</em>'
                    if with_supreme(lambda k: k.startswith("オリジナル変化球")):
                        marks += '<em class="rk-supreme">★オリ変</em>'
                bt_icons[nm] = (f'<img src="../../img/chars/{img_id}.png" alt="" width="40" height="40" loading="lazy">' if c.get("_icon") else "")
                icons += f'<{tag} class="rk-ic"{href}>{icon}{label}{marks}</{tag}>'
                if why:
                    link = f'<a href="../../chars/{pid}/">{e(full)}</a>' if pid else e(full)
                    notes += (f'<div class="rk-note" id="c-{img_id}"><h3><span class="tier tier-{t}">{t}</span>{link}</h3>' + paras(why) + "</div>")
            rows += f'<div class="tier-row"><div class="tier tier-{t}">{t}</div><div class="tier-ic">{icons}</div></div>'
        intro = paras(r.get("導入", []))
        h1_title = " ".join(f'<span class="cp-h1">{e(w)}</span>' for w in r["title"].split())  # 空白の所でだけ折り返す
        body = (f'<section class="phead"><p class="eyebrow">イベキャラランキング</p><h1>{h1_title}</h1>'
                f'<p>{date_label(r)}</p></section>'
                + (f'<div class="rk-intro">{intro}</div>' if intro else "")
                + top_guide_html(r)
                + (f'<div class="tier-table">{rows}</div>' if n else '<p class="muted">準備中です。</p>')
                + (bonus_table_html(r, chars, bt_icons) if r.get("ボーナス表") else "")
                + guide_html(r))   # キャラごとの評価文章は、各キャラのページ（src/chars/texts/<名前>.json の「評価」）にだけ書く
        meta = "\n".join([f'title: {r["title"]}｜パワプロアプリ攻略ベース',
                          f'description: パワプロアプリのイベキャラを、Tier表（{"・".join(t for t in TIERS if r["ランク"].get(t))}）でランク付けしました。{r["title"]}の評価基準と、各キャラのランクをまとめています。',
                          f'path: {r["path"]}', "nav: none"] + ([] if r.get("公開") else ["noindex: yes"])) + "\n"
        pages.append(f"<!--\n{meta}-->\n{body}")
    return pages
