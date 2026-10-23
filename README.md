# パワプロアプリ攻略ベース（公開用サイト）

公開先は GitHub Pages（main ブランチの /docs フォルダ）。

## しくみ
- `src/` … 元の部品（`layout.html`＝ヘッダー・フッター共通、`pages/*.html`＝各ページの本文、`decks.js`＝デッキのデータ、`assets/`、`img/decks/`）
- `build.py` … `src/` から公開用の `docs/` を作る。`python3 build.py <chars.json>`
- `docs/` … 公開されるファイル（自動で作るので手で直さない）

## よく変える設定（build.py の上のほう）
- `SITE_URL` / `CUSTOM_DOMAIN` … 独自ドメインにしたら変える
- `ADSENSE_CLIENT` … AdSense の `ca-pub-…`。入れると全ページに審査用コードと `ads.txt` が入る
- `AD_SLOT` … 広告ユニットの番号。入れるとトップ（ツールの下）とデッキページ（一覧の下）に広告枠が出る
- `CONTACT_FORM` … Googleフォームの URL

## デッキを追加するとき
`src/decks.js` に1件足し、画像（jpg）を `src/img/decks/` に置いて `build.py` を実行。
キャラを追加したら pawa-data の `chars.json` を使って `build.py` を実行し直す（`docs/data/chars.json` が更新される）。
