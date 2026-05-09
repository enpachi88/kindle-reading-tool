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
echo "▶ 本の種類（見開き分割・読む方向）を選択してください"
echo "  1: 横書き・実用書 (左から右へ読む L2R)"
echo "  2: 縦書き・マンガ (右から左へ読む R2L)"
echo "  3: 分割しない (1画面1ページとしてそのまま保存)"
read -p "番号を入力 (1-3) [デフォルト: 2]: " SPLIT_CHOICE

case "$SPLIT_CHOICE" in
    1) SPREAD_MODE="L2R" ;;
    3) SPREAD_MODE="NONE" ;;
    *) SPREAD_MODE="R2L" ;; # デフォルトはマンガ・縦書き
esac

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
python 01_capture_kindle.py $PAGES $SPREAD_MODE

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
