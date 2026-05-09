#!/bin/bash

# 使い方: ./run.sh [ページ数]
# 例: ./run.sh 10

# エラーが起きたら途中で停止する
set -e

# 引数が指定されていない場合は対話形式でページ数を聞く
if [ -z "$1" ]; then
    echo "========================================"
    echo " 📚 読書ツール (Kindle OCR) を開始します"
    echo "========================================"
    echo ""
    read -p "▶ キャプチャするページ数を入力してください（Enterでデフォルトの5ページ）: " INPUT_PAGES
    PAGES=${INPUT_PAGES:-5}
else
    PAGES=$1
    echo "========================================"
    echo " 📚 読書ツール (Kindle OCR) を開始します"
    echo " 対象ページ数: $PAGES ページ"
    echo "========================================"
fi

echo ""
echo "▶ 対象アプリを選択してください"
echo "  1: Kindle アプリ (マウスクリックでページをめくる)"
echo "  2: Kindle Cloud Reader ブラウザ版 (矢印キーでページをめくる)"
read -p "番号を入力 (1-2) [デフォルト: 1]: " TARGET_CHOICE

if [ "$TARGET_CHOICE" = "2" ]; then
    TARGET_APP="CLOUD"
else
    TARGET_APP="APP"
fi

echo ""
echo "▶ めくる方向（次のページへ進む操作）を選択してください"
if [ "$TARGET_APP" = "APP" ]; then
    echo "  1: 画面の【左端】をクリックして進む (マンガ等・右から左に読む本)"
    echo "  2: 画面の【右端】をクリックして進む (実用書等・左から右に読む本)"
else
    echo "  1: 【左矢印キー】で進む (マンガ等・右から左に読む本)"
    echo "  2: 【右矢印キー】で進む (実用書等・左から右に読む本)"
fi
read -p "番号を入力 (1-2) [デフォルト: 1]: " TURN_CHOICE

if [ "$TURN_CHOICE" = "2" ]; then
    TURN_DIR="RIGHT"
else
    TURN_DIR="LEFT"
fi

echo ""
echo "▶ 取得した画像の見開き分割設定を選択してください"
echo "  1: 横書き・実用書として分割 (左ページが先、右ページが後: L2R)"
echo "  2: 縦書き・マンガとして分割 (右ページが先、左ページが後: R2L)"
echo "  3: 分割しない (1画面1ページとしてそのまま保存: NONE)"
read -p "番号を入力 (1-3) [デフォルト: 2]: " SPLIT_CHOICE

case "$SPLIT_CHOICE" in
    1) SPREAD_MODE="L2R" ;;
    3) SPREAD_MODE="NONE" ;;
    *) SPREAD_MODE="R2L" ;; # デフォルトはマンガ・縦書き
esac

echo ""
echo "▶ ページをめくった後の「待機時間（秒）」を設定してください"
echo "  ※イラスト集など、読み込みが遅い本の場合は 3 や 5 を指定してください"
read -p "秒数を入力 [デフォルト: 1]: " WAIT_SEC
if [ -z "$WAIT_SEC" ]; then
    WAIT_SEC="1"
fi

# 仮想環境の有効化
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ エラー: 仮想環境(venv)が見つかりません。セットアップを行ってください。"
    exit 1
fi

echo ""
echo "▶ 0. 保存先とタイトルを設定します"
read -p "本のタイトルを入力: " BOOK_TITLE

# 未入力の対策
if [ -z "$BOOK_TITLE" ]; then
    BOOK_TITLE="無題の書籍_$(date +%Y%m%d%H%M%S)"
    echo "※ タイトルが未入力のため「$BOOK_TITLE」として進めます。"
fi

DEFAULT_DIR="/Users/enpachi_mini/Library/CloudStorage/GoogleDrive-enpachi88@gmail.com/マイドライブ/Obsidian/Antigravity Vault/40_Resources/書籍OCR"
echo ""
echo "現在のデフォルト保存先: $DEFAULT_DIR"
read -p "変更する場合は新しいパスを入力 (空欄でデフォルト): " OUT_DIR
if [ -z "$OUT_DIR" ]; then
    OUT_DIR="$DEFAULT_DIR"
fi

echo ""
echo "▶ 1. Kindleのキャプチャと画像分割を開始します..."
python 01_capture_kindle.py $PAGES $TARGET_APP $TURN_DIR $SPREAD_MODE $WAIT_SEC

echo ""
echo "▶ 2. Cloud Vision APIによる超高精度文字起こしを実行中..."
python 02_pipeline_vision.py

echo ""
echo "▶ 3. Tesseractによる文字起こし (補完) を実行中..."
python 03_pipeline_tesseract.py

echo ""
echo "▶ 4. Obsidianへテキストの統合・正規化・出力を行っています..."
# タイトルと出力先を引数として渡す
python 04_merge_normalize.py "$BOOK_TITLE" "$OUT_DIR"

echo ""
echo "========================================"
echo " 🎉 すべての処理が完了しました！"
echo " 📓 保存先: $OUT_DIR"
echo " 📄 作成ファイル: $BOOK_TITLE.md / $BOOK_TITLE.pdf / $BOOK_TITLE.txt"
echo "========================================"
