import time
import os
import subprocess
import pyautogui
import pytesseract
from PIL import Image

# ==========================================
# 設定
# ==========================================
# 処理するページ数
PAGES_TO_SCAN = 3

# アプリケーション名
APP_NAME = "Kindle"

# ページめくりに使うキー ('right' または 'space')
PAGE_TURN_KEY = 'right'

# めくった後の待機時間（秒）※Kindleのページめくりアニメーションを待つため
WAIT_TIME = 2.0

# 出力ファイル名
OUTPUT_FILE = "output.txt"

# スクリーンショットの範囲 (left, top, width, height)
# 画面全体から抽出すると不要な文字（メニューバーなど）が入る可能性があります。
# None にすると全画面になります。後から座標を指定することも可能です。
# 例: REGION = (100, 100, 800, 1000)
REGION = None
# ==========================================

def main():
    print(f"[{APP_NAME}] をアクティブにします...")
    # Macの「open」コマンドでアプリケーションを最前面に持ってくる
    subprocess.run(["open", "-a", APP_NAME])
    time.sleep(WAIT_TIME)

    # テキストファイルを追記モードで開く
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for i in range(1, PAGES_TO_SCAN + 1):
            print(f"\n[{i}/{PAGES_TO_SCAN}] ページ目を処理中...")
            
            # 1. スクリーンショットの取得
            img_path = "temp_screenshot.png"
            if REGION:
                screenshot = pyautogui.screenshot(region=REGION)
            else:
                screenshot = pyautogui.screenshot()
            
            screenshot.save(img_path)
            
            # 2. OCRで文字起こし
            print("  OCRで文字起こし中...")
            try:
                text = pytesseract.image_to_string(Image.open(img_path), lang="jpn")
                f.write(f"--- Page {i} ---\n")
                # 前後の無駄な空白を削除して書き込む
                f.write(text.strip() + "\n\n")
            except Exception as e:
                print(f"  OCRエラー: {e}")
                print("  ※Tesseract OCRが正しくインストールされていない可能性があります。")
            
            # 3. ページめくり
            if i < PAGES_TO_SCAN:
                print("  次のページへ...")
                pyautogui.press(PAGE_TURN_KEY)
                
                # 4. アニメーション完了待ち
                time.sleep(WAIT_TIME)
            
    # 一時ファイルの削除
    if os.path.exists("temp_screenshot.png"):
        os.remove("temp_screenshot.png")
        
    print(f"\nすべての処理が完了しました。抽出したテキストは {OUTPUT_FILE} に保存されています。")

if __name__ == "__main__":
    main()
