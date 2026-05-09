import time
import os
import subprocess
import pyautogui
from pathlib import Path
import Quartz
from PIL import Image

# ==========================================
# 設定
# ==========================================
import sys

# 処理するページ数と各種設定
try:
    PAGES_TO_SCAN = int(sys.argv[1]) if len(sys.argv) > 1 else 5
except ValueError:
    PAGES_TO_SCAN = 5

TARGET_APP = sys.argv[2] if len(sys.argv) > 2 else 'APP'
TURN_DIR = sys.argv[3] if len(sys.argv) > 3 else 'LEFT'
SPREAD_MODE = sys.argv[4] if len(sys.argv) > 4 else 'R2L'

START_PAGE = 1
END_PAGE = PAGES_TO_SCAN
WAIT_TIME = 1.0

# 見開き(2ページ分)の自動分割に関する設定
if SPREAD_MODE == 'NONE':
    SPLIT_SPREAD = False
    SPREAD_DIRECTION = 'L2R' # 使われないが定義しておく
else:
    SPLIT_SPREAD = True
    SPREAD_DIRECTION = SPREAD_MODE

IMG_DIR = Path("work/images")
IMG_DIR.mkdir(parents=True, exist_ok=True)

def get_kindle_window_info():
    """KindleアプリまたはKindle Cloud Reader(ブラウザ)のウィンドウ情報を取得する"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, 
        Quartz.kCGNullWindowID
    )
    for window in window_list:
        owner_name = str(window.get(Quartz.kCGWindowOwnerName, ''))
        window_name = str(window.get(Quartz.kCGWindowName, ''))
        
        # アプリ名がKindle、またはウィンドウタイトル(タブ名)にKindleが含まれる場合
        if 'Kindle' in owner_name or 'Kindle' in window_name or 'kindle' in window_name.lower():
            bounds = window.get(Quartz.kCGWindowBounds, {})
            # メインウィンドウらしき大きさのもの（ツールチップなどを避ける）
            if bounds.get('Width', 0) > 300 and bounds.get('Height', 0) > 300:
                ret_id = window.get(Quartz.kCGWindowNumber)
                return ret_id, owner_name, bounds
    return None, None, None

def clear_old_data():
    """前回のOCRデータ(画像やテキスト、JSON)を削除してまっさらな状態にする"""
    print("\n【初期化】 前回の画像・キャッシュデータをクリアしています...")
    # 画像含む作業フォルダをすべてクリア
    for d in ["work/images", "work/vision_txt", "work/vision_json", "work/tesseract_txt", "out"]:
        dir_path = Path(d)
        if dir_path.exists():
            for f in dir_path.glob("*"):
                if f.is_file():
                    f.unlink()
    print("✅ クリア完了")

def split_if_spread(img_path: Path):
    """横幅が広い画像を見開きと判定して左右に分割する"""
    if not SPLIT_SPREAD:
        return
        
    img = Image.open(img_path)
    w, h = img.size
    
    # 横幅が高さの1.1倍以上あれば見開きと判定
    if w > h * 1.1:
        mid = w // 2
        left_img = img.crop((0, 0, mid, h))
        right_img = img.crop((mid, 0, w, h))
        
        # 読む順番に合わせて連番をつける
        # _1 が先に読まれるページ、_2 が後に読まれるページ
        if SPREAD_DIRECTION == 'L2R':
            left_img.save(img_path.with_name(f"{img_path.stem}_1.png"))
            right_img.save(img_path.with_name(f"{img_path.stem}_2.png"))
        else: # 'R2L': 漫画や小説
            right_img.save(img_path.with_name(f"{img_path.stem}_1.png"))
            left_img.save(img_path.with_name(f"{img_path.stem}_2.png"))
            
        # 元の1枚画像を削除
        img_path.unlink()

def main():
    print(f"\n【ウィンドウ自動キャプチャモード】")
    
    # 最初のページから始める場合は古いデータを消す
    if START_PAGE == 1:
        clear_old_data()
        
    print("開いているKindleアプリ または Kindle Cloud Reader を自動検索しています...")
    window_id, owner_name, bounds = get_kindle_window_info()
    
    if not window_id:
        print("❌ エラー: Kindleの画面が見つかりませんでした。")
        print("Kindleアプリまたはブラウザ(Kindle Cloud Reader)で本を開いた状態で再度実行してください。")
        return
        
    print(f"✅ Kindleのウィンドウ(ID: {window_id}, アプリ: {owner_name})を発見しました！")
    print(f"★ Macの特権機能により、上に別のウィンドウや通知が被っていてもKindleの中身だけを綺麗にキャプチャします。")
    print(f"\n確実な操作のため、自動的に最前面に移動します...")
    
    # 確実に操作を届けるため、該当アプリ（KindleやChrome等）をアクティブにする
    subprocess.run(["open", "-a", owner_name])
    
    print(f"3秒後にキャプチャを開始します。マウスを動かさないでお待ちください...")
    time.sleep(3.0)

    for i in range(START_PAGE, END_PAGE + 1):
        print(f"[{i:03d}/{END_PAGE:03d}] ページ目をキャプチャ中...")
        
        img_path = IMG_DIR / f"page-{i:03d}.png"
        
        # Mac標準のscreencaptureで指定ウィンドウIDのみを無音(-x)・影なし(-o)で撮影
        subprocess.run(["screencapture", "-l", str(window_id), "-o", "-x", str(img_path)])
        
        # 見開きの場合は画像を2枚に分割する
        split_if_spread(img_path)
        
        # ページめくり
        if i < END_PAGE:
            if TARGET_APP == 'APP':
                # Kindleアプリの場合: マウスクリック方式
                click_y = bounds['Y'] + (bounds['Height'] / 2)
                if TURN_DIR == 'LEFT':
                    click_x = bounds['X'] + 50
                else:
                    click_x = bounds['X'] + bounds['Width'] - 50
                pyautogui.click(x=click_x, y=click_y)
            else:
                # Kindle Cloud Readerの場合: キーボード(矢印キー)方式
                if TURN_DIR == 'LEFT':
                    pyautogui.keyDown('left')
                    time.sleep(0.1)
                    pyautogui.keyUp('left')
                else:
                    pyautogui.keyDown('right')
                    time.sleep(0.1)
                    pyautogui.keyUp('right')
                    
            time.sleep(WAIT_TIME)
            
    print(f"\n🎉 キャプチャ完了。画像を {IMG_DIR} に保存しました。")

if __name__ == "__main__":
    main()
