# SNSで共有したときの画像（og:image、1200x630）を作る。build.py から呼ぶ（2026-11-12 管理人OK）
#   形：緑の背景＋左上にロゴとサイト名、白いカードにページの種類（小さく）とページ名（大きく）、キャラページ・ガチャ記事はキャラのアイコン
#   フォントは tools/fonts/（サイトと同じ M PLUS 1p Black・Dela Gothic One。SIL Open Font License）
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT_TITLE = str(HERE / "tools" / "fonts" / "MPLUS1p-Black.ttf")
FONT_BRAND = str(HERE / "tools" / "fonts" / "DelaGothicOne-Regular.ttf")
W, H = 1200, 630
GREEN, WHITE, INK, MUTED, MARKER = "#1d5e43", "#ffffff", "#14233a", "#5b6676", "#ffd64a"
NO_HEAD = set("、。，．・：；？！）」』】〕｝〉》ー…ぁぃぅぇぉっゃゅょァィゥェォッャュョ")   # 行の頭に来ないようにする文字


def _chunks(text):
    """改行してよい区切りで分ける（「の」「・」「？」「]」「）」・空白の後ろと「（」の前。「と」は「まとめ」等を切るので使わない）。[ ] の中（バージョン名）は切らない"""
    out, cur, depth = [], "", 0
    for ch in text:
        if ch in "（(" and depth == 0 and cur:   # 「（」の前でも改行してよい
            out.append(cur)
            cur = ""
        cur += ch
        depth += (ch in "[［【") - (ch in "]］】")
        if depth == 0 and ch in "の・？]］】）) 　":
            out.append(cur)
            cur = ""
    return out + [cur] if cur else out


def _wrap_chars(draw, text, font, width):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= width or not cur:
            cur += ch
        elif ch in NO_HEAD:            # 行頭禁則：前の行の最後の1文字と一緒に次の行へ
            lines.append(cur[:-1])
            cur = cur[-1] + ch
        else:
            lines.append(cur)
            cur = ch
    return lines + [cur] if cur else lines


def _wrap(draw, text, font, width, by_chunk=True):
    """区切りの良い所で改行する（入らなければ None）。by_chunk=False なら1文字ずつ"""
    if not by_chunk:
        return _wrap_chars(draw, text, font, width)
    lines, cur = [], ""
    for c in _chunks(text):
        if draw.textlength((cur + c).rstrip(), font=font) <= width:
            cur += c
        elif draw.textlength(c.rstrip(), font=font) <= width:
            lines.append(cur.rstrip())
            cur = c
        else:
            return None                # 1かたまりが1行に入らない → もっと小さい文字で試す
    return [l for l in lines if l] + ([cur.rstrip()] if cur.strip() else [])


def _logo(draw, x, y, s):
    """サイトのロゴ（ホームベース形）。s は一辺の大きさ"""
    k = s / 40
    draw.polygon([(x + 6 * k, y + 6 * k), (x + 34 * k, y + 6 * k), (x + 34 * k, y + 22 * k), (x + 20 * k, y + 35 * k), (x + 6 * k, y + 22 * k)], fill=WHITE)


def make(dest, title, label="", icon=None):
    """dest に PNG を書く。title＝ページ名、label＝小さく出すページの種類、icon＝キャラのアイコン画像のパス"""
    im = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(im)
    _logo(d, 56, 30, 64)
    d.text((132, 62), "パワプロアプリ攻略ベース", font=ImageFont.truetype(FONT_BRAND, 40), fill=WHITE, anchor="lm")
    cx0, cy0, cx1, cy1 = 48, 118, W - 48, H - 48
    d.rounded_rectangle((cx0, cy0, cx1, cy1), radius=28, fill=WHITE)
    tx = cx0 + 56
    tw = (cx1 - 56) - tx
    if icon:
        ic = Image.open(icon).convert("RGB")
        size = 260
        ic = ic.resize((size, size), Image.LANCZOS)
        ix, iy = cx1 - 56 - size, (cy0 + cy1) // 2 - size // 2
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=26, fill=255)
        im.paste(ic, (ix, iy), mask)
        tw = ix - 40 - tx
    # 区切りの良い所で改行する。58px以上で2行に入るならその一番大きいサイズ、だめなら3行に入る一番大きいサイズ。
    # それでも入らなければ1文字ずつ改行
    tries = []
    for by_chunk in (True, False):
        for fs in (76, 70, 64, 58, 52, 46, 42):
            font = ImageFont.truetype(FONT_TITLE, fs)
            lines = _wrap(d, title, font, tw, by_chunk)
            if lines:
                tries.append((by_chunk, fs, font, lines))
    pick = (next((t for t in tries if t[0] and t[1] >= 58 and len(t[3]) <= 2), None)
            or next((t for t in tries if t[0] and len(t[3]) <= 3), None)
            or next(t for t in tries if len(t[3]) <= 3 or t[1] == 42))
    _, fs, font, lines = pick
    lh = int(fs * 1.3)
    lab_h = 52 if label else 0
    y = (cy0 + cy1) // 2 - (lab_h + lh * len(lines)) // 2
    if label:
        lf = ImageFont.truetype(FONT_TITLE, 30)
        lw = d.textlength(label, font=lf)
        d.rounded_rectangle((tx, y, tx + lw + 32, y + 42), radius=21, fill=GREEN)
        d.text((tx + 16, y + 21), label, font=lf, fill=WHITE, anchor="lm")
        y += lab_h
    for ln in lines:
        lw = d.textlength(ln, font=font)
        d.rectangle((tx, y + int(lh * 0.62), tx + lw, y + int(lh * 0.92)), fill=MARKER)   # サイトの見出しと同じ黄色のマーカー
        d.text((tx, y), ln, font=font, fill=INK)
        y += lh
    d.text((cx1 - 32, cy1 - 26), "pawapuryotsu.com", font=ImageFont.truetype(FONT_TITLE, 24), fill=MUTED, anchor="rs")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)
