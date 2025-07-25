# ローカルテスト環境

ローカル動画ファイルから音声を抽出し、文字起こしと記事生成を行うためのツール群です。

## 📁 ディレクトリ構成

```
local-test/
├── README.md                   # このファイル
├── requirements.txt            # Python依存関係
├── extract_transcript.py       # 音声抽出・文字起こしスクリプト
├── generate_article.py         # 記事生成スクリプト（推奨）
├── generate_html.py            # 旧統合スクリプト（非推奨）
├── test_script.py             # YouTubeチャンネル動画処理テスト
├── mock_aws_services.py        # AWSサービスモック
├── test_lambda_functions.py    # Lambda関数テスト
└── final_outputs/             # 生成されたアウトプット
    ├── articles/              # HTML記事
    ├── transcripts/           # 文字起こし
    ├── metadata/              # メタデータ
    └── audio/                 # 抽出した音声ファイル
```

## 🚀 セットアップ

### 1. システム要件

- Python 3.7+
- FFmpeg（音声抽出に必須）
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt-get install ffmpeg`
  - Windows: [公式サイト](https://ffmpeg.org/download.html)からダウンロード

### 2. Python環境セットアップ

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r local-test/requirements.txt
```

### 3. OpenAI API設定

`.env`ファイルを作成し、APIキーを設定：

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

## 💻 使用方法

### 推奨ワークフロー（2段階処理）

#### ステップ1: 音声抽出・文字起こし

```bash
python local-test/extract_transcript.py <動画ファイルパス> <YouTube URL>
```

**例:**
```bash
python local-test/extract_transcript.py video/sample.mp4 https://www.youtube.com/watch?v=z0hNjLcG6tw
```

#### ステップ2: 記事生成

```bash
python local-test/generate_article.py <文字起こしファイルパス>
```

**例:**
```bash
python local-test/generate_article.py final_outputs/transcripts/transcript_z0hNjLcG6tw_20250720_161656.txt
```

**処理フロー:**
1. **extract_transcript.py**: 動画から音声抽出 → OpenAI Whisperで文字起こし
2. **generate_article.py**: 文字起こしから GPT-4-turbo でHTML記事生成

**利点:**
- 長い文字起こしでもコンテキスト制限を回避
- エラー時の部分的な再実行が可能
- 処理ステップの分離により効率的

## 📄 出力ファイル

### ファイル命名規則
- **音声**: `{video_id}.mp3`
- **文字起こし**: `transcript_{video_id}_{timestamp}.txt`
- **HTML記事**: `article_{video_id}_{timestamp}.html`
- **メタデータ**: `metadata_{video_id}_{timestamp}.json`

### 出力例
```
final_outputs/
├── audio/
│   └── z0hNjLcG6tw.mp3              # 抽出した音声
├── transcripts/
│   └── transcript_z0hNjLcG6tw_20250720_161656.txt
├── articles/
│   └── article_z0hNjLcG6tw_20250720_161656.html
└── metadata/
    └── metadata_z0hNjLcG6tw_20250720_161656.json
```

## 🎯 主な機能

### extract_transcript.py
- **音声抽出**: FFmpegを使用してMP4→MP3変換
- **文字起こし**: OpenAI Whisper APIで日本語認識
- **ファイル管理**: YouTube IDベースのファイル命名
- **エラーハンドリング**: 詳細なエラーログとガイダンス

### generate_article.py
- **記事生成**: GPT-4-turboでSEO最適化されたHTML記事作成
- **長文対応**: 大きなコンテキストウィンドウで長い文字起こしに対応
- **Markdownクリーンアップ**: コードブロック記号の自動除去
- **メタデータ**: 処理情報とコスト推定を記録

## ⚙️ 設定

### 音声抽出設定
- ビットレート: 192kbps
- サンプルレート: 44100Hz
- フォーマット: MP3

### API設定
- Whisperモデル: `whisper-1`
- GPTモデル: `gpt-4-turbo`
- 最大トークン数: 3000

## 🔧 トラブルシューティング

### よくあるエラー

1. **ModuleNotFoundError: No module named 'openai'**
   ```bash
   pip install -r local-test/requirements.txt
   ```

2. **FFmpegが見つからない**
   ```bash
   # macOS
   brew install ffmpeg
   ```

3. **OpenAI APIエラー**
   - `.env`ファイルにAPIキーが設定されているか確認
   - APIキーが有効か確認

4. **HTMLに ```html と ``` が含まれる**
   - generate_article.py では自動的に除去されます
   - 手動で除去が必要な場合は、ファイルを編集してください

## 💡 注意事項

- 動画ファイルのサイズや長さによって処理時間が変わります
- OpenAI APIの使用量に応じて料金が発生します
- 生成されたファイルは`final_outputs/`に蓄積されるので、定期的に整理してください
- 推奨ワークフローを使用することで、より安定した処理が可能です

## 📚 参考情報

### 旧方式（非推奨）
```bash
python local-test/generate_html.py <動画ファイルパス> <YouTube URL>
```
⚠️ **注意**: 長い文字起こしの場合、GPT-4のコンテキスト制限によりエラーが発生する可能性があります。

### テスト用スクリプト
```bash
python local-test/test_script.py  # YouTubeチャンネル動画処理テスト
```