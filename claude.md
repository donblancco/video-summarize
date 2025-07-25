# Claude開発メモ - 動画処理システム

## 🎯 プロジェクト概要

YouTube動画から自動的にWordPress記事を生成するAWSサーバーレスシステム

**目的**: 動画コンテンツの文字起こし → 記事化 → WordPress自動投稿

## 🏗️ システム構成

### アーキテクチャ
```
CloudFront(Basic認証) → S3(UI) → S3(処理) → Lambda Container Images → WordPress
```

### AWSリソース
- **リージョン**: ap-northeast-1 (メイン) + us-east-1 (Lambda@Edge)
- **アカウント**: YOUR_ACCOUNT_NAME (XXXXXXXXXXXX)
- **プロファイル**: `--profile YOUR_PROFILE`

## 📁 ディレクトリ構成

```
video-article/
├── aws-lambda/           # Lambda関数（Container Image）
│   ├── Dockerfile       # FFmpeg + Python + OpenAI
│   ├── extract_transcript_lambda.py
│   ├── generate_article_lambda.py
│   ├── wordpress_publish_lambda.py
│   └── upload-ui.html
├── terraform/           # インフラ定義
│   ├── main.tf         # マルチリージョン設定
│   ├── s3.tf           # S3 + CloudFront + Basic認証
│   ├── lambda.tf       # Container Image Lambda
│   ├── lambda_edge.tf  # Basic認証用
│   └── basic_auth_lambda.js
└── claude.md           # このファイル
```

## 🔧 重要な設定

### Lambda関数
| 関数名 | 形式 | メモリ | 一時ストレージ | 用途 |
|--------|------|-------|-------------|------|
| extract-transcript-prod | Container | 2048MB | **10GB** | 音声抽出・文字起こし |
| generate-article-prod | Container | 1024MB | 512MB | 記事生成 |
| wordpress-publish-prod | Container | 1024MB | 512MB | WordPress投稿 |

### Basic認証
- **URL**: https://your-cloudfront-domain.cloudfront.net
- **ユーザー名**: YOUR_USERNAME
- **パスワード**: YOUR_PASSWORD
- **実装**: Lambda@Edge (us-east-1)

### WordPress設定
- **サイト**: your-site.com
- **ユーザー**: YOUR_WP_USERNAME
- **アプリパスワード**: YOUR_APP_PASSWORD

## 🚀 よく使うコマンド

### Container Image 更新
```bash
# ビルド・プッシュ
cd aws-lambda
docker build -t video-processing-lambda .
aws ecr get-login-password --region ap-northeast-1 --profile YOUR_PROFILE | docker login --username AWS --password-stdin XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com
docker tag video-processing-lambda:latest XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest
docker push XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest

# Lambda更新
aws lambda update-function-code --function-name video-article-processing-extract-transcript-prod --image-uri XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest --profile YOUR_PROFILE
aws lambda update-function-code --function-name video-article-processing-generate-article-prod --image-uri XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest --profile YOUR_PROFILE
aws lambda update-function-code --function-name video-article-processing-wordpress-publish-prod --image-uri XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest --profile YOUR_PROFILE
```

### ログ確認
```bash
# 最新ログ確認
aws logs filter-log-events --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod --start-time $(python3 -c "import time; print(int(time.time() - 600) * 1000)") --profile YOUR_PROFILE --filter-pattern "✅" --query 'events[-3:].message' --output text

# エラーログ確認
aws logs filter-log-events --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod --start-time $(python3 -c "import time; print(int(time.time() - 600) * 1000)") --profile YOUR_PROFILE --filter-pattern "ERROR" --query 'events[-3:].message' --output text
```

### S3確認
```bash
# ファイル一覧
aws s3 ls s3://video-article-processing-prod/ --recursive --profile YOUR_PROFILE | tail -10

# 特定動画の処理状況
aws s3 ls s3://video-article-processing-prod/ --recursive --profile YOUR_PROFILE | grep VIDEO_ID
```

### Lambda設定確認
```bash
# 関数設定確認
aws lambda get-function-configuration --function-name video-article-processing-extract-transcript-prod --profile YOUR_PROFILE --query '[MemorySize,Timeout,EphemeralStorage.Size]' --output table

# 一時ストレージ拡張
aws lambda update-function-configuration --function-name video-article-processing-extract-transcript-prod --ephemeral-storage Size=10240 --profile YOUR_PROFILE
```

## 🐛 トラブルシューティング

### よくある問題

#### 1. FFmpegエラー
- **原因**: Container Imageが古い
- **解決**: 上記のContainer Image更新手順

#### 2. OpenAIモジュールエラー
- **原因**: Container Imageが古い
- **解決**: 上記のContainer Image更新手順

#### 3. 大容量動画処理失敗
- **原因**: 一時ストレージ不足
- **解決**: 10GB一時ストレージ設定（済み）

#### 4. Basic認証が効かない
- **原因**: CloudFront更新中
- **確認**: 5-15分待機

### パフォーマンス

#### 動作確認済み
- **55MB動画**: 2分で処理完了
- **558MB動画**: 5分で処理完了（10GB一時ストレージ）

#### 上限
- **理論上**: 10GB一時ストレージまで
- **実用上**: 1GB程度まで推奨

## 💰 コスト

### 月額（100回処理）
- **Lambda実行**: $0.50
- **一時ストレージ**: $0.40 (10GB)
- **S3**: $0.26
- **CloudFront**: $0.01
- **Lambda@Edge**: $0.01
- **CloudWatch**: $0.50
- **合計**: **$1.68/月**
- **OpenAI API**: 別途

### 1回あたり
- **AWS**: 約$0.017
- **OpenAI**: 約$0.05-0.20（動画長による）

## 🔐 セキュリティ

### 認証情報
- **OpenAI API Key**: 環境変数で管理
- **WordPress認証**: アプリパスワード使用
- **Basic認証**: Lambda@Edgeで実装

### IAM権限
- Lambda実行ロールは最小権限
- S3バケット間のアクセス制御
- ECRイメージプル権限

## 📝 開発メモ

### Container Imageの利点
- FFmpegバイナリを含める
- OpenAI最新ライブラリ
- 依存関係管理が簡単
- デプロイが確実

### Lambda@Edgeの制約
- us-east-1でのみ作成可能
- Node.js限定
- サイズ制限あり

### S3イベント連鎖
1. uploads/*.mp4 → extract-transcript
2. transcripts/*.txt → generate-article  
3. articles/*.html → wordpress-publish

### 今後の改善案
- 動画圧縮機能
- 複数言語対応
- バッチ処理機能
- ダッシュボード追加

## 🔄 デプロイフロー

1. **コード変更**
2. **Container Image ビルド・プッシュ**
3. **Lambda関数更新**
4. **テスト実行**
5. **ログ確認**

## 📞 緊急時対応

### システム停止
```bash
# S3イベント通知無効化
aws s3api put-bucket-notification-configuration --bucket video-article-processing-prod --notification-configuration '{}' --profile YOUR_PROFILE
```

### 復旧
```bash
# Terraform再適用
cd terraform
terraform apply
```

## 📊 監視

### 正常性確認
- CloudWatch Logs
- S3ファイル生成状況
- WordPress投稿状況

### アラート設定
- Lambda実行エラー
- 実行時間超過
- S3容量増加

---

**最終更新**: 2025年7月20日  
**動作確認**: VIDEO_ID_1, VIDEO_ID_2 で正常動作確認済み