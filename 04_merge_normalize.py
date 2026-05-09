import re
import sys
import unicodedata
from pathlib import Path
import img2pdf

# オプション: タイトルの取得 (デフォルト名)
book_title = "book_ocr"
if len(sys.argv) > 1:
    book_title = sys.argv[1]

# 出力先の指定 (デフォルトはout)
OBSIDIAN_VAULT_DIR = Path("out")
if len(sys.argv) > 2:
    OBSIDIAN_VAULT_DIR = Path(sys.argv[2])

# 該当ディレクトリを作成
OBSIDIAN_VAULT_DIR.mkdir(parents=True, exist_ok=True)

# 入出力の設定
VISION_TXT = Path("work/vision_txt")
TESS_TXT   = Path("work/tesseract_txt")

# ファイルパスの決定
OUT_MD     = OBSIDIAN_VAULT_DIR / f"{book_title}.md"
OUT_PDF    = OBSIDIAN_VAULT_DIR / f"{book_title}.pdf"
OUT_TXT    = OBSIDIAN_VAULT_DIR / f"{book_title}.txt"

RAW_DIR    = Path("work/merged_raw")
NORM_DIR   = Path("work/merged_norm")
RULES_TSV  = Path("dict/replace_rules.tsv")

RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

def load_rules():
    rules = []
    if RULES_TSV.exists():
        for line in RULES_TSV.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                rules.append((parts[0], parts[1]))
    return rules

RULES = load_rules()

def normalize_text(s: str) -> str:
    # 1) Unicode正規化（全角半角の揺れを統一）
    s = unicodedata.normalize("NFKC", s)

    # 2) よくあるOCRノイズ除去
    s = s.replace("\u00a0", " ") # ノーブレークスペースを通常のスペースに
    s = re.sub(r"[ \t]+", " ", s)  # 連続するスペースやタブを一つに
    s = re.sub(r"\n{3,}", "\n\n", s) # 3つ以上の連続する改行を2つに

    # 3) ハイフン改行対策（英単語の折返し）
    s = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", s)

    # 4) 置換辞書による修正（表記ゆれ・固有名詞・頻出誤字）
    for src, dst in RULES:
        s = s.replace(src, dst)

    return s.strip() + "\n"

def choose_page_text(page_id: str) -> str:
    vpath = VISION_TXT / f"{page_id}.txt"
    tpath = TESS_TXT / f"{page_id}.txt"

    vision = vpath.read_text(encoding="utf-8", errors="ignore") if vpath.exists() else ""

    # Tesseract結果が「weaker」扱いでなければ採用
    if tpath.exists():
        tess = tpath.read_text(encoding="utf-8", errors="ignore")
        return tess if tess.strip() else vision

    # Tesseract結果が弱いとマーキングされている、または存在しない場合はVision採用
    return vision

def main():
    # ページ一覧（Vision基準）
    pages = sorted([p.stem for p in VISION_TXT.glob("page-*.txt")])

    if not pages:
        print("テキストファイルが見つかりません。先に 02_pipeline_vision.py を実行してください。")
        return

    merged_raw_parts = []
    merged_norm_parts = []

    for pid in pages:
        text = choose_page_text(pid)
        raw_path = RAW_DIR / f"{pid}.txt"
        raw_path.write_text(text, encoding="utf-8")

        norm = normalize_text(text)
        norm_path = NORM_DIR / f"{pid}.txt"
        norm_path.write_text(norm, encoding="utf-8")

        # Markdown用のヘッダーを付けて結合
        page_num = pid.split("-")[-1]
        merged_raw_parts.append(f"\n\n---\n## Page {page_num}\n\n{text.strip()}\n")
        merged_norm_parts.append(f"\n\n---\n## Page {page_num}\n\n{norm.strip()}\n")

    # 最終的な結合と保存
    merged_norm = "".join(merged_norm_parts).strip() + "\n"

    OUT_MD.write_text(merged_norm, encoding="utf-8")
    
    # プレーンテキスト用にはMarkdownの見出し等を取り除く
    txt_content = re.sub(r"\n---\n## Page [\w_]+\n\n", "\n\n", merged_norm)
    OUT_TXT.write_text(txt_content, encoding="utf-8")

    print(f"統合・正規化が完了しました。")
    print(f"📄 Markdown出力: {OUT_MD}")
    print(f"📄 Text出力: {OUT_TXT}")
    
    # 5) 画像群を束ねてPDFとしてバックアップ保存する
    print(f"📷 画像をPDFとしてパッケージ化しています...")
    imgs = sorted(Path("work/images").glob("*.png"))
    if imgs:
        try:
            img_paths = [str(f) for f in imgs]
            with open(OUT_PDF, "wb") as f:
                f.write(img2pdf.convert(img_paths))
            print(f"📦 PDFバックアップ出力: {OUT_PDF}")
        except Exception as e:
            print(f"⚠️ PDF化中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
