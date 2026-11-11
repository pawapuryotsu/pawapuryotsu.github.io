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

---

# デッキ紹介スライド（1デッキにつき2枚）

デッキページ（docs/decks/<学園>/）の情報から作る。どのデッキを作るかは管理人が指定する。

- `deck_<デッキ>_1.png` … 左上に育成結果画像（右は文章を書くための空き）、中央にメインデッキ（青の縁）・サポートデッキ（緑の縁）、下にメイン・サポートの表（デッキページと同じ数値。●☆の印は外す）。サポートの表の下に基礎上限の画像（u）
- `deck_<デッキ>_2.png` … 上は1枚目と同じ、下に育成した選手の能力画像と動画のサムネイル。一番下は1行ぶんの空欄（何も入れない）

## 使い方
`node youtube-slides/deck_slides.js <デッキ> [出力先フォルダ] [--thumb サムネイル画像]`
- `<デッキ>` は decks.js の画像名の後ろ（育成結果が `result_roman_8` なら `roman_8`）
- メイン画像の下の端（アイテム枠の下の線）が切れている roman_1〜5 は、切れた分（6px）を下に足してから青の縁を付ける（deck_slides.js の MAIN_PAD）
- サムネイルは decks.js の video から https://i.ytimg.com を自動で読む（クラウド環境は 2026-11-10 に i.ytimg.com を許可済み）。読めない時や動画が「なし」のデッキは灰色の空枠。画像をもらった時は `--thumb` で渡す

---

# イベキャラ一覧スライド（アイコン／キャラ名／実装日／入手手段）

ランキングスライドと同じデザインで、指定した日以降に登場したイベキャラを実装日順に並べる（1枚に最大7人、多い時は自動で2枚目以降）。
データは pawa-data の chars.json（実装日・入手方法）とアイコン。実装日が空欄のキャラは載らないので、実行時に名前を表示する。

`python3 youtube-slides/list_slides.py --since 2026/09/05 --title "タイトル" [--exclude "[キャプテン]御幸一也" ...] [--until 日付] [--name 出力名] [出力先フォルダ]`
- キャラ名は [二つ名]名前 を1行で出す。入りきらない時だけ二つ名を上の行に小さく出す（2026-11-10 管理人）。
- 例（2026-11-10 管理人依頼の投手向け）：`--exclude "[キャプテン]御幸一也" "[わんこだよ！]パーちゃん" 天道あかね シャンプー --name pitcher_since0905 /mnt/project-files/youtube-slides/lists`

---

# 評価基準・加点要素スライド

ランキングの解説欄（src/ranking/ranking.json の「解説欄」）のうち、箇条書きの見出し（評価基準・加点要素）を1見出し1枚にする。文章はそのまま使い、{赤太:…} の色もサイトと同じ。
`python3 youtube-slides/guide_slides.py <ランキングのキー> [出力先フォルダ] [--all]` → `<キー>_guide/guide_1.png …` と order.txt。`--all` で評価理由詳細などの文章の見出しも作る。

---

# 画像でもらったTier表を作り直すスライド

ranking.json に無いTier表（過去の月のランキングの画像など）を、ランキングスライドと同じデザイン（make_slides.py のCSSをそのまま使う）の1枚にする。

1. 画像から読み取ったランク・並び・キャラ名を `youtube-slides/tiers/<英数字の名前>.json` に書く（chars.json の名前と完全一致しないと止まる。推測で並べ替えたり足したりしない）
2. `python3 youtube-slides/tier_slide.py youtube-slides/tiers/<名前>.json /mnt/project-files/youtube-slides/tiers` → `<名前>_tier.png`

- ランクの色は上から 赤・橙・黄・緑・青（高校キャラ＝赤、C＝青を追加）。行が多いときはアイコンを自動で小さくする
- アイコンは pawa-data の event-chars/icons（PSR、無ければSR）
- 例：`tiers/sep2026.json`（9月のランキング※一部省略、2026-11-10 管理人依頼）
