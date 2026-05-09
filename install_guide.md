# 読書ツール (Kindle OCR) インストールガイド

別のMacでこのツールを動かすためのセットアップ手順です。

## 1. 必要なツールのインストール (Mac本体へ)
ターミナルを開き、Tesseract (画像から文字を読み取るエンジン) をインストールします。
```bash
brew install tesseract tesseract-lang
```

## 2. Python仮想環境 (venv) の作成と準備
本ツールを置いたフォルダにターミナルで移動します。
```bash
# パスは環境に合わせて変更してください
cd "/Users/enpachi_mini/Library/CloudStorage/GoogleDrive-enpachi88@gmail.com/マイドライブ/Obsidian/Antigravity Vault/Antigravity_System/Tools/ナレッジ系/読書ツール"
```

新しいMac用の「小部屋（仮想環境）」を作成し、中に入ります。
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. 必要なライブラリの一括インストール
用意されている設計図 (`requirements.txt`) を使って、必要なパーツを自動インストールします。
```bash
pip install -r requirements.txt
```

## 4. Google Cloud Vision API の設定 (gcloud CLI)
現在の環境では、組織ポリシーによりJSONキーの発行が制限されているため、Google Cloud CLI (`gcloud`) を用いたユーザー認証（ADC）を使用しています。
新しいMacでも以下の手順でログインを行ってください。

1. `gcloud` コマンドラインツールをインストールします。
   ```bash
   brew install --cask google-cloud-sdk
   ```
2. ターミナルで以下のログインコマンドを実行し、ブラウザが開いたら許可します。
   ```bash
   gcloud auth application-default login
   ```
3. クォータ用プロジェクトを設定します（スクリプト内でも自動指定されます）。
   ```bash
   gcloud auth application-default set-quota-project ocr-project-488212
   ```
※ 上記を一度行えば、次回以降は不要です。

---

## 🎉 使い方 (実行コマンド)
準備が終わったら、以下のコマンドで全自動キャプチャ＆文字起こしを開始できます。

```bash
# 仮想環境に入る（ターミナルを開き直すたびに必要）
source venv/bin/activate

# めくるページ数を指定して実行！
# 例: 10ページ（見開きなら右・左で20ページ分）を処理する場合
./run.sh 10
```

---

## 📦 他のMacへの移行（持っていく方法）
フォルダごと別のMacにコピーする際は、以下の手順でzip圧縮するのが安全で確実です。

❌ **注意**: `venv`フォルダ（仮想環境）は絶対にzipに入れないでください。Macごとの専用設定が含まれており、新しいMacでは動かず、ファイルサイズも数GBになるためです。
✅ **持っていくもの**: 
- `01_`〜`04_`のPythonファイル
- `run.sh`、`requirements.txt`、`install_guide.md`
- `dict`フォルダ、（あれば設定ファイルなど）
※`vision-key.json` や `.env` は機密情報のため、USBメモリ等で直接移すのが最も安全です。

これらの【必要なファイルだけ】を選択してzip圧縮し、新しいMacへ移動して解凍してください。

---

## 🛡️ フォールバック機能（自動復旧）について
本ツールは「Cloud Vision API」をメインの最高精度エンジンとして使用しています。
しかし、万が一「オフライン環境」「GCPの利用枠（クォータ）上限到達」「一時的なシステム障害」などでVision APIが利用できない場合でも、ツールが途中で停止することはありません。

APIエラーが発生したページは、自動的に「不出来(Bad)」としてマークされます。
その後、次のステップでローカルの「Tesseract (Mac内蔵のCPUパワーを利用したOCR)」がそのページを拾い上げ、自動的に処理を引き継ぐ**「フォールバック機能」**を搭載しています。
これにより、いかなる通信環境・エラー状況下でも、最後まで「読書ノート（Markdown）」の出力を完走させる堅牢な作りになっています。
