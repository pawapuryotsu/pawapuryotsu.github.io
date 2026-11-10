# YouTube動画用ランキングスライド

イベキャラランキングから、YouTube動画用のスライド画像（1920×1080 PNG）を作る道具。
**普段のサイト作業では使わない。** build.py からは呼ばれないので、動画を作るときだけ使う。

## できるもの
- `00_tier.png` … 全キャラのTier表（1ランク1行、折り返しなし。人数が多い行に合わせてアイコンを自動で小さくする）
- `01_SS.png`〜 … キャラ別。左にTier表（紹介キャラを赤四角）、右に「〇〇の重要ボーナス」（追加枠／キャラ持参アイテムも）。画面下は動画編集で文字を乗せるために空けてある
- `order.txt` … 番号とキャラ名の対応（番号はTier表の左上から右下への順）
- `<キー>_slides.zip` … 上の画像をまとめたもの

ファイル名は文字化けしないよう英数字だけ。

## 使い方
1. 先にサイトを最新にする（`python3 build.py`。ランキングページと docs/img/chars のアイコンを使う）
2. `python3 youtube-slides/make_slides.py <ランキングのキー> [出力先フォルダ]`
   - キーは src/ranking/ranking.json の `ranking` の中の名前（例：`roman`、`andromeda`）
   - 出力先を省くと `youtube-slides/out/`（git には入らない）

必要なもの：Python3、Node.js と Playwright（Chromium）、ネット接続（Google Fonts を読む）、
となりのフォルダに pawa-data（`../pawa-data/event-chars/chars.json`）。

## 決まりごと
- 数値はサイトと同じ計算（charpages.py）で出す。キャラページがあるキャラは、ページの表と一致しないと止まる。
- 重要ボーナスは、その学園で使わない項目を外す（投手ランキング＝コツイベントボーナス・試合経験点ボーナスを外す、野手ランキング＝練習効果アップ・スペシャルタッグボーナスを外す）。make_slides.py の HIDE で変えられる。
- Tier表の並びは ranking.json と一致しないと止まる。
- 画面下の解説文（長所・短所の帯）は Claude が作らない（管理人が動画編集で入れる。2026-11-10）。
