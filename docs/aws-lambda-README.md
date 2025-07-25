# AWS Lambda Container Image

YouTube動画処理用のLambda Container Imageとソースコード

## ファイル構成

```
aws-lambda/
├── Dockerfile                      # Container Image定義
├── requirements-container.txt      # Container用Python依存関係
├── requirements.txt               # 開発用Python依存関係
├── extract_transcript_lambda.py    # 第1段階: 音声抽出・文字起こし
├── generate_article_lambda.py      # 第2段階: 記事生成
├── wordpress_publish_lambda.py     # 第3段階: WordPress投稿
├── upload-ui.html                 # Web UI（S3静的サイト用）
└── footer.html                    # WordPress投稿用フッター
```

## Container Image について

本システムは **Lambda Container Image** 形式を採用しています：

### 利点
- FFmpegバイナリを含む複雑な依存関係の管理が容易
- クロスプラットフォーム対応（macOS ARM64 → Linux x86_64）
- より大きなパッケージサイズ（最大10GB）
- ローカルでのDockerテストが可能

### Lambda Layer vs Container Image

| 項目 | Lambda Layer | Container Image |
|------|--------------|-----------------|
| パッケージサイズ | 250MB制限 | 10GB制限 |
| FFmpegサポート | ❌（バイナリサイズ問題） | ✅（完全サポート） |
| デプロイ時間 | 高速 | 中程度 |
| ローカルテスト | 困難 | 容易 |
| 依存関係管理 | 複雑 | シンプル |

## Dockerイメージのビルド・デプロイ

### 1. ECRリポジトリ作成

```bash
aws ecr create-repository --repository-name video-processing-lambda --region ap-northeast-1 --profile almoprs
```

### 2. イメージビルド

```bash
# ARM64 Mac用（Lambda Linux x86_64向け）
docker build --platform linux/amd64 -t video-processing-lambda .

# または通常のビルド
docker build -t video-processing-lambda .
```

### 3. ECRプッシュ

```bash
# ECRログイン
aws ecr get-login-password --region ap-northeast-1 --profile almoprs | docker login --username AWS --password-stdin 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com

# タグ付け
docker tag video-processing-lambda:latest 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest

# プッシュ
docker push 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest
```

## Lambda関数の実装

### 1. extract_transcript_lambda.py

**機能**: 動画から音声抽出 → OpenAI Whisperで文字起こし

**主要技術**:
- FFmpeg: 動画から音声抽出
- OpenAI Whisper API: 音声ファイルの文字起こし
- S3: ファイルのアップロード・ダウンロード

**処理フロー**:
1. S3から動画ファイルダウンロード
2. FFmpegで音声抽出（MP3変換）
3. OpenAI Whisper APIで文字起こし
4. 文字起こし結果をS3にアップロード

### 2. generate_article_lambda.py

**機能**: 文字起こしテキスト → OpenAI GPT-4でHTML記事生成

**主要技術**:
- OpenAI GPT-4 API: 記事生成
- S3: ファイルの読み書き

**処理フロー**:
1. S3から文字起こしファイル読み込み
2. GPT-4で構造化されたHTML記事生成
3. 生成記事をS3にアップロード

### 3. wordpress_publish_lambda.py

**機能**: HTML記事 → WordPress REST APIで自動投稿

**主要技術**:
- WordPress REST API: 投稿作成
- S3: HTMLファイル読み込み・フッター結合

**処理フロー**:
1. S3からHTML記事読み込み
2. S3からフッターHTML読み込み・結合
3. YouTubeサムネイル取得・アップロード
4. WordPress投稿作成（下書き状態）

## 環境変数

| 変数名 | 説明 | 設定場所 |
|--------|------|----------|
| `OPENAI_API_KEY` | OpenAI APIキー | Terraform |
| `S3_BUCKET` | S3バケット名 | Terraform |
| `WORDPRESS_SITE_URL` | WordPress URL | Terraform |
| `WORDPRESS_USERNAME` | WordPress ユーザー名 | Terraform |
| `WORDPRESS_APP_PASSWORD` | WordPress アプリパスワード | Terraform |

## ローカルテスト

### Dockerコンテナでテスト

```bash
# イメージビルド
docker build -t video-processing-lambda .

# 環境変数ファイル作成
echo "OPENAI_API_KEY=your-key" > .env
echo "S3_BUCKET=your-bucket" >> .env

# コンテナ実行
docker run --env-file .env video-processing-lambda
```

### Lambda Runtime Interface Emulator

```bash
# RIE付きで実行
docker run -p 9000:8080 --env-file .env video-processing-lambda

# 別ターミナルでテスト
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"Records":[{"s3":{"bucket":{"name":"test-bucket"},"object":{"key":"uploads/test.mp4"}}}]}'
```

## デバッグ

### CloudWatch Logs

```bash
# リアルタイムログ監視
aws logs tail /aws/lambda/video-article-processing-extract-transcript-prod --follow --profile almoprs

# エラーログフィルタ
aws logs filter-log-events \
  --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod \
  --filter-pattern "ERROR" \
  --profile almoprs
```

### Lambda関数の手動実行

```bash
# extract_transcript 手動実行
aws lambda invoke \
  --function-name video-article-processing-extract-transcript-prod \
  --payload '{"Records":[{"s3":{"bucket":{"name":"video-article-processing-prod"},"object":{"key":"uploads/test.mp4"}}}]}' \
  /tmp/response.json \
  --profile almoprs
```

## トラブルシューティング

### よくある問題

1. **FFmpeg not found**
   - Container Image内でFFmpegバイナリが正しくインストールされているか確認
   - Dockerfile内のFFmpegインストール手順を確認

2. **OpenAI API エラー**
   - APIキーの有効性確認
   - レート制限の確認
   - バージョン0.28.0の使用確認

3. **S3アクセスエラー**
   - IAMロールの権限確認
   - バケット名の正確性確認

4. **WordPress投稿エラー**
   - WordPress REST API有効性確認
   - アプリパスワードの有効性確認
   - CORS設定確認

### パフォーマンス最適化

1. **メモリ設定**
   - extract_transcript: 2048MB（FFmpeg処理）
   - generate_article: 1024MB（テキスト処理）
   - wordpress_publish: 1024MB（API処理）

2. **タイムアウト設定**
   - 全関数: 15分（長い動画対応）

3. **同時実行制限**
   - コスト管理のため適切な制限設定

## セキュリティ

### 機密情報管理

- OpenAI APIキー: Terraform変数で管理
- WordPress認証情報: Terraform変数で管理
- IAM権限: 最小権限の原則

### ネットワークセキュリティ

- Lambda関数はパブリックサブネット実行
- S3バケット: 適切なアクセス制御
- WordPress: HTTPS必須