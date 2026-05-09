import os, re, json
from pathlib import Path
from tqdm import tqdm
from google.cloud import vision

# 認証のための環境変数をADCファイルのデフォルトパスに向け、Quotaプロジェクトも指定する
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = "ocr-project-488212"

IMG_DIR = Path("work/images")
JSON_DIR = Path("work/vision_json")
TXT_DIR  = Path("work/vision_txt")
BAD_LIST = Path("work/bad_pages.txt")

JSON_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)

# Visionクライアントの初期化
client = vision.ImageAnnotatorClient()

def ocr_page(img_path: Path):
    content = img_path.read_bytes()
    image = vision.Image(content=content)

    # Document OCR（ページ文書向け）
    resp = client.document_text_detection(image=image)
    if resp.error.message:
        raise RuntimeError(resp.error.message)

    # フルテキスト
    text = resp.full_text_annotation.text if resp.full_text_annotation else ""

    # 品質判定用スコア（ざっくり単語のconfidenceを平均）
    confs = []
    fta = resp.full_text_annotation
    if fta and fta.pages:
        for p in fta.pages:
            for block in p.blocks:
                for para in block.paragraphs:
                    for w in para.words:
                        if w.confidence is not None:
                            confs.append(float(w.confidence))
    avg_conf = sum(confs)/len(confs) if confs else None

    return text, avg_conf, resp

def is_bad(text: str, avg_conf):
    # 失敗ページの典型：文字が少ない / 記号だらけ / confidence低い
    t = text.strip()
    if len(t) < 80:
        return True
    
    # 記号率が高い（日本語でも暴れるとこうなる）
    nonword = re.findall(r"[^\w\u3040-\u30FF\u4E00-\u9FFF]", t)
    ratio = len(nonword) / max(len(t), 1)
    if ratio > 0.55:
        return True
    
    if avg_conf is not None and avg_conf < 0.55:
        return True
        
    return False

def main():
    bad_pages = []
    imgs = sorted(IMG_DIR.glob("page-*.png"))
    
    if not imgs:
        print(f"画像が見つかりません: {IMG_DIR} を確認してください。")
        return

    for img in tqdm(imgs, desc="Cloud Vision OCR"):
        page_id = img.stem  # page-001 など
        out_json = JSON_DIR / f"{page_id}.json"
        out_txt  = TXT_DIR  / f"{page_id}.txt"

        # 既に処理済みの場合はスキップ
        if out_txt.exists() and out_json.exists():
            # 既存のテキストからBad判定だけは行っておく
            text = out_txt.read_text(encoding="utf-8")
            if is_bad(text, None): # avg_confは再計算しない簡易対応
                 bad_pages.append(page_id)
            continue

        try:
            text, avg_conf, resp = ocr_page(img)

            out_txt.write_text(text, encoding="utf-8")
            out_json.write_text(json.dumps(vision.AnnotateImageResponse.to_json(resp)), encoding="utf-8")

            if is_bad(text, avg_conf):
                bad_pages.append(page_id)
        except Exception as e:
            print(f"\n⚠️ Vision API エラー ({page_id}): {e}")
            print("→ このページはTesseract(ローカル)での処理に回します。")
            
            # エラー時は空文字として保存し、強制的にBad判定にする
            out_txt.write_text("", encoding="utf-8")
            out_json.write_text(json.dumps({"error": str(e)}), encoding="utf-8")
            bad_pages.append(page_id)

    # 不出来ページのリストを出力
    BAD_LIST.write_text("\n".join(bad_pages) + ("\n" if bad_pages else ""), encoding="utf-8")
    
    print(f"総ページ数: {len(imgs)}")
    print(f"再処理対象(Bad)ページ数: {len(bad_pages)} -> {BAD_LIST}")

if __name__ == "__main__":
    main()
