# almoprs-video-article

YouTube動画から自動的にWordPress記事を生成するAWSサーバーレスシステム

## システム概要

本システムは以下の流れで動画を記事に変換します：

1. **動画アップロード** → CloudFront（Basic認証付き）経由でS3バケットに動画ファイルをアップロード
2. **音声抽出・文字起こし** → Lambda Container Image（extract_transcript）がFFmpegで音声抽出＋OpenAI Whisperで文字起こし
3. **記事生成** → Lambda Container Image（generate_article）がOpenAI GPT-4で文字起こしからHTML記事を生成
4. **WordPress投稿** → Lambda Container Image（wordpress_publish）が自動でWordPressサイトに投稿

## 🏗️ AWS アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Account: almoprs (057493959080)             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  🔐Basic認証    ┌──────────────────────────────────────┐ │
│  │   CloudFront    │ ←─────────────── │        Lambda@Edge                   │ │
│  │  Distribution   │                  │     (us-east-1リージョン)             │ │
│  │ E769ZUF7QQQ60   │                  │  video-processing-basic-auth-prod    │ │
│  └─────────────────┘                  └──────────────────────────────────────┘ │
│           │                                                                   │
│           ▼ HTTPS                                                             │
│  ┌─────────────────┐                                                         │
│  │   S3 UI Bucket  │ 📋 upload-ui.html                                      │
│  │  ui-almoprs     │                                                         │
│  └─────────────────┘                                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    メイン処理バケット                                     │ │
│  │              video-article-processing-prod                              │ │
│  │                                                                         │ │
│  │  uploads/     audio/      transcripts/    articles/                     │ │
│  │    📹          🎵            📝            📄                           │ │
│  │    │           │             │             │                            │ │
│  │    │           │             │             │                            │ │
│  │    ▼ S3イベント │             │             │                            │ │
│  │ ┌─────────────┐ │             │             │                            │ │
│  │ │Lambda1:     │ │─────────────┼─────────────┼─                           │ │
│  │ │extract-     │ │             │             │                            │ │
│  │ │transcript   │ │             │             │                            │ │
│  │ │(Container)  │ │             │             │                            │ │
│  │ │+ FFmpeg     │ │             │             │                            │ │
│  │ │2048MB/15分  │ │             │             │                            │ │
│  │ └─────────────┘ │             │             │                            │ │
│  │                 │             ▼ S3イベント │                            │ │
│  │                 │          ┌─────────────┐ │                            │ │
│  │                 │          │Lambda2:     │ │                            │ │
│  │                 │          │generate-    │ │                            │ │
│  │                 │          │article      │ │─────────────────────────────│ │
│  │                 │          │(Container)  │ │                            │ │
│  │                 │          │1024MB/15分  │ │                            │ │
│  │                 │          └─────────────┘ │                            │ │
│  │                 │                         │                            │ │
│  │                 │                         ▼ S3イベント                  │ │
│  │                 │                      ┌─────────────┐                  │ │
│  │                 │                      │Lambda3:     │                  │ │
│  │                 │                      │wordpress-   │                  │ │
│  │                 │                      │publish      │                  │ │
│  │                 │                      │(Container)  │                  │ │
│  │                 │                      │1024MB/15分  │                  │ │
│  │                 │                      └─────────────┘                  │ │
│  │                 │                            │                          │ │
│  └─────────────────────────────────────────────│──────────────────────────┘ │
│                                                 │                            │
│  ┌─────────────────┐                           │                            │
│  │   ECR Repository│                           │                            │
│  │ video-processing│                           │                            │
│  │    -lambda      │                           │                            │
│  └─────────────────┘                           │                            │
│                                                 │                            │
│  ┌─────────────────┐                           │                            │
│  │ CloudWatch Logs │                           │                            │
│  │ 各Lambda用ログ   │                           │                            │
│  │ 保持期間: 14日   │                           │                            │
│  └─────────────────┘                           │                            │
│                                                 ▼ WordPress REST API         │
└─────────────────────────────────────────────────────────────────────────────┘
                                                  │
                                        ┌─────────────────┐
                                        │   WordPress     │
                                        │ almoprs-clinic  │
                                        │      .jp        │
                                        │   (自動投稿)     │
                                        └─────────────────┘
```

## 📊 AWSリソース構成

### ap-northeast-1 リージョン

| サービス | リソース名 | 用途 | 
|---------|-----------|------|
| **S3** | video-article-processing-prod | メイン処理バケット |
| **S3** | video-article-processing-ui-almoprs-prod | UI専用バケット |
| **CloudFront** | E769ZUF7QQQ60 | UI配信 + Basic認証 |
| **Lambda** | extract-transcript-prod | 音声抽出・文字起こし |
| **Lambda** | generate-article-prod | HTML記事生成 |
| **Lambda** | wordpress-publish-prod | WordPress投稿 |
| **ECR** | video-processing-lambda | Container Image |
| **IAM** | 各Lambda用実行ロール | 最小権限設定 |
| **CloudWatch** | 各Lambda用ロググループ | 監視・デバッグ |

### us-east-1 リージョン

| サービス | リソース名 | 用途 |
|---------|-----------|------|
| **Lambda@Edge** | basic-auth-prod | CloudFront Basic認証 |
| **CloudWatch** | Lambda@Edge用ログ | 認証ログ監視 |

## 🔐 セキュリティ設定

### Basic認証（CloudFront）
- **URL**: https://dwqp0tli97nsm.cloudfront.net
- **ユーザー名**: `Uchida`
- **パスワード**: `Naorun1082`
- **実装**: Lambda@Edge（us-east-1）

### IAM権限
- 各Lambda関数に最小権限のIAMロール
- S3バケット間の適切なアクセス制御
- OpenAI/WordPress API キーの環境変数管理

## プロジェクト構造

```
almoprs-video-article/
├── aws-lambda/                   # Lambda関数とContainer Image
│   ├── Dockerfile               # 全Lambda関数用のコンテナイメージ定義
│   ├── extract_transcript_lambda.py    # 第1段階: 音声抽出・文字起こし
│   ├── generate_article_lambda.py      # 第2段階: 記事生成
│   ├── wordpress_publish_lambda.py     # 第3段階: WordPress投稿
│   ├── requirements-container.txt      # Container用依存関係
│   ├── requirements.txt               # 開発用依存関係
│   ├── upload-ui.html                 # アップロード用WebUI
│   └── footer.html                    # WordPress投稿用フッター
├── terraform/                    # Terraformインフラ定義
│   ├── main.tf                   # プロバイダー・共通設定
│   ├── s3.tf                     # S3バケット・CloudFront・UI
│   ├── lambda.tf                 # Lambda関数・権限
│   ├── iam.tf                    # IAMロール・ポリシー
│   ├── cloudwatch.tf             # ログ・モニタリング
│   ├── outputs.tf                # 出力値
│   ├── terraform.tfvars.example  # 設定例
│   └── terraform.tfstate         # 現在の状態
├── local-test/                   # ローカルテスト用
│   ├── extract_transcript.py     # ローカル動作確認用
│   ├── generate_article.py       # ローカル動作確認用
│   └── test_script.py            # 統合テストスクリプト
├── wordpress/                    # WordPress関連
│   ├── footer.html               # 投稿用フッターHTML
│   └── wordpress_test.py         # WordPress API テスト
└── venv/                         # Python仮想環境
```

## 技術スタック

- **AWS Lambda**: サーバーレス関数実行（Container Image形式）
- **Amazon S3**: ファイルストレージ・静的ウェブサイトホスティング
- **Amazon CloudFront**: CDN（UI配信用）
- **Amazon ECR**: Dockerイメージレジストリ
- **FFmpeg**: 動画から音声抽出
- **OpenAI API**: Whisper（文字起こし）＋ GPT-4（記事生成）
- **WordPress REST API**: 自動投稿
- **Terraform**: インフラストラクチャ管理

## セットアップ

### 1. 依存関係のインストール

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r aws-lambda/requirements.txt
```

### 2. AWS設定

```bash
# AWS CLI設定
aws configure --profile almoprs

# Terraform設定
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvarsを編集
```

### 3. デプロイ

```bash
# ECRリポジトリ作成・Dockerイメージビルド・プッシュ
cd aws-lambda
docker build -t video-processing-lambda .
aws ecr get-login-password --region ap-northeast-1 --profile almoprs | docker login --username AWS --password-stdin 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com
docker tag video-processing-lambda:latest 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest
docker push 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest

# Terraformでインフラ構築
cd ../terraform
terraform init
terraform plan
terraform apply
```

## 使用方法

### Web UIから動画アップロード

1. CloudFront URLにアクセス
2. 動画ファイル(.mp4)とYouTube URLを指定
3. アップロード → 自動で記事生成・WordPress投稿

### 直接S3アップロード

```bash
aws s3 cp 動画ファイル.mp4 s3://video-article-processing-prod/uploads/ --profile almoprs
```

## システムの特徴

- **完全自動処理**: S3イベント通知による3段階Lambda連鎖実行
- **Container化**: FFmpegバイナリを含むLambda Container Image
- **マルチ形式対応**: .mp4、.mov、.avi対応
- **スケーラブル**: サーバーレスアーキテクチャ
- **監視可能**: CloudWatch Logsで各段階の実行状況確認
- **コスト効率**: 使用時のみ課金

## トラブルシューティング

### Lambda実行状況確認

```bash
aws logs filter-log-events --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod --start-time $(date -d '1 hour ago' +%s)000 --profile almoprs
```

### S3バケット内容確認

```bash
aws s3 ls s3://video-article-processing-prod/ --recursive --profile almoprs
```

## ライセンス

MIT License