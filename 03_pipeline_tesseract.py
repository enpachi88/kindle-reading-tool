import os, re, subprocess
from pathlib import Path
import cv2
import numpy as np
from tqdm import tqdm

IMG_DIR = Path("work/images")
VISION_TXT = Path("work/vision_txt")
TESS_TXT = Path("work/tesseract_txt")
BAD_LIST = Path("work/bad_pages.txt")

TESS_TXT.mkdir(parents=True, exist_ok=True)

def deskew(gray):
    # 文字領域の角度推定（簡易）
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if len(coords) < 1000:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def preprocess(img_path: Path):
    img = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"画像の読み込みに失敗しました: {img_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = deskew(gray)

    # コントラスト強化（CLAHE）
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)

    # ノイズ軽減
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=75, sigmaSpace=75)

    # 2値化
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # 文字が細い場合に少し太らせる
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)

    return thr

def run_tesseract(prep_img_path: Path, out_txt_path: Path):
    # 縦書き・横書き両対応で jpn+jpn_vert を指定
    # PSM 6: 単一の均一なテキストブロックとみなす
    cmd = [
        "tesseract",
        str(prep_img_path),
        str(out_txt_path.with_suffix("")),
        "-l", "jpn+jpn_vert",
        "--oem", "1",
        "--psm", "6"
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def is_tesseract_better(tess_text: str, vision_text: str):
    # 文字数が増えた、記号率が減った、などで勝敗判定
    def score(t: str):
        t = t.strip()
        if not t:
            return -1e9
        nonword = re.findall(r"[^\w\u3040-\u30FF\u4E00-\u9FFF]", t)
        ratio = len(nonword)/max(len(t),1)
        return len(t) - 200*ratio
    
    # わずかな改善ではなく、明確に良い場合のみ採用する
    return score(tess_text) > score(vision_text) + 30

def main():
    if not BAD_LIST.exists():
        print("bad_pages.txt が存在しません。終了します。")
        return

    bad = [line.strip() for line in BAD_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not bad:
        print("再処理対象(Bad)のページはありませんでした。終了します。")
        return

    tmp_dir = Path("work/_tmp_preprocessed")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for page_id in tqdm(bad, desc="Tesseract retry"):
        img_path = IMG_DIR / f"{page_id}.png"
        
        if not img_path.exists():
            print(f"スキップ: {img_path} が見つかりません。")
            continue

        prep = preprocess(img_path)

        prep_path = tmp_dir / f"{page_id}_prep.png"
        cv2.imencode(".png", prep)[1].tofile(str(prep_path))

        out_txt = TESS_TXT / f"{page_id}.txt"
        
        try:
            run_tesseract(prep_path, out_txt)
        except subprocess.CalledProcessError:
            print(f"Tesseractの実行に失敗しました (ページ: {page_id})")
            continue

        tess_text = out_txt.read_text(encoding="utf-8", errors="ignore")
        vision_text_path = VISION_TXT / f"{page_id}.txt"
        vision_text = vision_text_path.read_text(encoding="utf-8", errors="ignore") if vision_text_path.exists() else ""

        # もしTesseractが微妙なら、Visionを優先するために弱い結果とマーク
        if not is_tesseract_better(tess_text, vision_text):
            out_txt.rename(TESS_TXT / f"{page_id}.weaker_than_vision.txt")

    print("Tesseractによる再処理が完了しました。")

if __name__ == "__main__":
    main()
