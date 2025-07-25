# 技術ドキュメント - almoprs動画処理システム

## 目次
1. [システムアーキテクチャ](#システムアーキテクチャ)
2. [技術スタック詳細](#技術スタック詳細)
3. [Lambda関数仕様](#lambda関数仕様)
4. [Container Image設計](#container-image設計)
5. [S3イベント連鎖フロー](#s3イベント連鎖フロー)
6. [認証・セキュリティ](#認証セキュリティ)
7. [パフォーマンスチューニング](#パフォーマンスチューニング)
8. [エラーハンドリング](#エラーハンドリング)
9. [デプロイメントプロセス](#デプロイメントプロセス)
10. [トラブルシューティングガイド](#トラブルシューティングガイド)

## システムアーキテクチャ

### 全体構成図
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS Account: almoprs (057493959080)                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Region: ap-northeast-1                          Region: us-east-1          │
│                                                                             │
│  CloudFront → S3 UI → S3 Process → Lambda1 → Lambda2 → Lambda3 → WordPress │
│      ↑                                                                      │
│      └── Lambda@Edge (Basic Auth) ←────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────────────┘
```

### コンポーネント間通信
- **CloudFront → S3**: HTTPS (Basic認証付き)
- **S3 → Lambda**: S3 Event Notifications
- **Lambda → S3**: AWS SDK (IAM Role認証)
- **Lambda → WordPress**: REST API (Application Password)
- **Lambda → OpenAI**: HTTPS API (API Key認証)

## 技術スタック詳細

### インフラストラクチャ層
| 技術 | バージョン | 用途 | 設定ファイル |
|------|-----------|------|------------|
| Terraform | >= 1.0 | IaC | terraform/*.tf |
| AWS Lambda | Python 3.11 | サーバーレス実行 | - |
| Amazon ECR | - | Container Image Registry | - |
| Amazon S3 | - | オブジェクトストレージ | s3.tf |
| CloudFront | - | CDN + 認証 | s3.tf |
| Lambda@Edge | Node.js 18.x | エッジ認証 | lambda_edge.tf |

### アプリケーション層
| 技術 | バージョン | 用途 | インストール方法 |
|------|-----------|------|---------------|
| Python | 3.11 | ランタイム | Container Image |
| FFmpeg | 6.0 | 動画処理 | Container Image |
| **OpenAI SDK** | **0.28.0** | **AI API（Lambda安定版）** | pip |
| Boto3 | 1.34.144 | AWS SDK | pip |
| BeautifulSoup4 | 4.12.3 | HTML解析 | pip |
| Requests | 2.31.0 | HTTP通信 | pip |

### 外部サービス
| サービス | 用途 | 認証方式 | エンドポイント |
|---------|------|---------|--------------|
| OpenAI Whisper | 音声文字起こし | API Key | api.openai.com |
| OpenAI GPT-4 | 記事生成 | API Key | api.openai.com |
| WordPress REST API | 記事投稿 | Application Password | almoprs-clinic.jp/wp-json |

## Lambda関数仕様

### 1. extract-transcript-prod
```python
# 関数シグネチャ
def lambda_handler(event: dict, context: LambdaContext) -> dict

# 入力イベント構造
{
    "Records": [{
        "s3": {
            "bucket": {"name": "video-article-processing-prod"},
            "object": {"key": "uploads/VIDEO_ID_timestamp.mp4"}
        }
    }]
}

# 処理フロー
1. S3から動画ダウンロード (最大10GB)
2. FFmpegで音声抽出 (MP3, 128kbps)
3. OpenAI Whisperで文字起こし
4. S3に結果保存 (audio/, transcripts/)

# 出力
- audio/VIDEO_ID.mp3
- transcripts/transcript_VIDEO_ID_timestamp.txt
- metadata/extract_VIDEO_ID_timestamp.json
```

### 2. generate-article-prod
```python
# 関数シグネチャ
def lambda_handler(event: dict, context: LambdaContext) -> dict

# 入力イベント構造
{
    "Records": [{
        "s3": {
            "bucket": {"name": "video-article-processing-prod"},
            "object": {"key": "transcripts/transcript_VIDEO_ID_timestamp.txt"}
        }
    }]
}

# 処理フロー
1. S3から文字起こしファイル読み込み
2. メタデータ（YouTube URL等）取得
3. GPT-4でHTML記事生成
4. S3に記事保存

# 出力
- articles/article_VIDEO_ID_timestamp.html
- metadata/article_VIDEO_ID_timestamp.json
```

### 3. wordpress-publish-prod
```python
# 関数シグネチャ
def lambda_handler(event: dict, context: LambdaContext) -> dict

# 入力イベント構造
{
    "Records": [{
        "s3": {
            "bucket": {"name": "video-article-processing-prod"},
            "object": {"key": "articles/article_VIDEO_ID_timestamp.html"}
        }
    }]
}

# 処理フロー
1. S3からHTML記事読み込み
2. フッターテンプレート結合
3. YouTubeサムネイル取得
4. WordPress REST APIで投稿

# 出力
- WordPress投稿 (下書き)
- metadata/wordpress_VIDEO_ID_timestamp.json
```

## Container Image設計

### Dockerfile構成
```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# FFmpegインストール層（x86_64 Linuxバイナリ）
RUN yum install -y wget tar xz && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*/ffprobe /usr/local/bin/

# Python依存関係層
COPY requirements-container.txt .
RUN pip install -r requirements-container.txt

# Lambda関数層
COPY *_lambda.py ./
COPY upload-ui.html ./

# 環境変数
ENV PYTHONUNBUFFERED=1
```

### 重要な技術的制約

#### OpenAI SDKバージョン
- **バージョン**: `0.28.0` （旧API形式）
- **理由**: Lambda環境での動作安定性
- **注意**: 最新版（1.x系）とAPI構造が異なる

```python
# 0.28.0の使用例
import openai
openai.api_key = os.environ['OPENAI_API_KEY']

# Whisper API
response = openai.Audio.transcribe(
    model="whisper-1",
    file=audio_file,
    language="ja"
)

# GPT-4 API  
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
```

#### プラットフォームアーキテクチャ
- **Lambda**: x86_64 Linux 固定
- **Container Image**: linux/amd64 でビルド
- **FFmpeg**: amd64-static バイナリ使用
- **理由**: コスト効率と安定性（ARM64 Graviton2は未対応）

### イメージサイズ最適化
- **ベースイメージ**: AWS Lambda Python 3.11 (260MB)
- **FFmpeg**: 静的バイナリ (75MB)
- **Python依存関係**: (180MB)
- **合計**: 約515MB

### ECRリポジトリ
```bash
# リポジトリURI
057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest

# イメージタグ戦略
- latest: 本番最新版
- v1.0.0: バージョンタグ
- dev: 開発版
```

## S3イベント連鎖フロー

### イベント設定
```hcl
# terraform/s3.tf より抜粋
resource "aws_s3_bucket_notification" "video_processing" {
  # Stage 1: 動画アップロード → 音声抽出
  lambda_function {
    lambda_function_arn = aws_lambda_function.extract_transcript.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".mp4"  # .mov, .avi も設定
  }

  # Stage 2: 文字起こし完了 → 記事生成
  lambda_function {
    lambda_function_arn = aws_lambda_function.generate_article.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "transcripts/"
    filter_suffix       = ".txt"
  }

  # Stage 3: 記事生成完了 → WordPress投稿
  lambda_function {
    lambda_function_arn = aws_lambda_function.wordpress_publish.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "articles/"
    filter_suffix       = ".html"
  }
}
```

### S3ディレクトリ構造
```
video-article-processing-prod/
├── uploads/          # 入力動画
├── audio/           # 抽出音声
├── transcripts/     # 文字起こし
├── articles/        # 生成記事
├── metadata/        # 処理メタデータ
└── templates/       # テンプレート（footer.html）
```

## 認証・セキュリティ

### Lambda@Edge Basic認証
```javascript
// basic_auth_lambda.js
const USERNAME = 'Uchida';
const PASSWORD = 'Naorun1082';
const authString = 'Basic ' + Buffer.from(USERNAME + ':' + PASSWORD).toString('base64');

exports.handler = (event, context, callback) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    if (headers.authorization && headers.authorization[0].value === authString) {
        callback(null, request); // 認証成功
    } else {
        callback(null, {
            status: '401',
            headers: {
                'www-authenticate': [{key: 'WWW-Authenticate', value: 'Basic'}]
            }
        });
    }
};
```

### IAMロール最小権限
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::video-article-processing-prod/*"
    },
    {
      "Effect": "Allow",
      "Action": "logs:*",
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### 環境変数暗号化
- **OpenAI API Key**: Lambda環境変数（KMS暗号化）
- **WordPress認証**: Lambda環境変数（KMS暗号化）
- **アクセス制御**: IAMロールベース

## パフォーマンスチューニング

### Lambda設定最適化
| 関数 | メモリ | タイムアウト | 一時ストレージ | アーキテクチャ | 同時実行数 |
|------|-------|------------|-------------|-------------|----------|
| extract-transcript | 2048MB | 15分 | 10GB | **x86_64** | 10 |
| generate-article | 1024MB | 15分 | 512MB | **x86_64** | 20 |
| wordpress-publish | 1024MB | 15分 | 512MB | **x86_64** | 20 |

**重要**: Container ImageはLinux x86_64でビルドされており、Lambda関数のアーキテクチャも**x86_64**固定です。ARM64（Graviton2）は使用していません。

### 処理時間の目安
| 動画サイズ | 音声抽出 | 文字起こし | 記事生成 | 合計 |
|-----------|---------|-----------|---------|------|
| 50MB | 30秒 | 60秒 | 30秒 | 2分 |
| 500MB | 120秒 | 180秒 | 30秒 | 5.5分 |
| 1GB | 240秒 | 360秒 | 30秒 | 10.5分 |

### コスト最適化
```python
# 音声圧縮設定
audio_settings = {
    'codec': 'mp3',
    'bitrate': '128k',  # 音質とサイズのバランス
    'channels': 1       # モノラル変換
}

# Whisper API設定
whisper_settings = {
    'model': 'whisper-1',  # 最も費用対効果が高い
    'language': 'ja'       # 言語指定で精度向上
}
```

## エラーハンドリング

### リトライ戦略
```python
# Lambda自動リトライ設定
- 非同期呼び出し: 2回
- 最大イベント経過時間: 6時間
- デッドレターキュー: 未設定（将来実装）

# アプリケーションレベルリトライ
import time
from botocore.exceptions import ClientError

def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)  # 指数バックオフ
```

### エラー通知
```python
# CloudWatch Logsでのエラー検知
print(f"❌ エラー: {error_message}")  # 絵文字でフィルタリング可能

# 将来実装予定
- SNS通知
- CloudWatch Alarms
- Error メトリクス
```

### 一般的なエラーと対処法
| エラー | 原因 | 対処法 |
|-------|------|-------|
| No such file or directory: 'ffmpeg' | Container Image古い | Lambda関数更新 |
| No module named 'openai' | Container Image古い | Lambda関数更新 |
| Task timed out | 大容量動画 | タイムアウト延長 |
| [Errno 28] No space left | 一時ストレージ不足 | 10GB設定確認 |

## デプロイメントプロセス

### 1. Container Imageビルド・プッシュ
```bash
#!/bin/bash
# デプロイスクリプト

# 1. ECRログイン
aws ecr get-login-password --region ap-northeast-1 --profile almoprs | \
docker login --username AWS --password-stdin 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com

# 2. イメージビルド
cd aws-lambda
docker build -t video-processing-lambda .

# 3. タグ付け・プッシュ
docker tag video-processing-lambda:latest \
  057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest
docker push 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest

# 4. Lambda更新
for func in extract-transcript generate-article wordpress-publish; do
  aws lambda update-function-code \
    --function-name video-article-processing-${func}-prod \
    --image-uri 057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest \
    --profile almoprs
done
```

### 2. Terraform適用
```bash
cd terraform
terraform plan
terraform apply

# 特定リソースのみ更新
terraform apply -target=aws_lambda_function.extract_transcript
```

### 3. デプロイ検証
```bash
# テスト動画アップロード
aws s3 cp test.mp4 s3://video-article-processing-prod/uploads/TEST_$(date +%s).mp4 \
  --metadata youtube-url=https://www.youtube.com/watch?v=TEST,video-id=TEST \
  --profile almoprs

# ログ監視
aws logs tail /aws/lambda/video-article-processing-extract-transcript-prod \
  --follow --profile almoprs
```

## トラブルシューティングガイド

### デバッグ手順

#### 1. 処理状況確認
```bash
# S3ファイル確認
aws s3 ls s3://video-article-processing-prod/ --recursive --profile almoprs | grep VIDEO_ID

# Lambda実行ログ
aws logs filter-log-events \
  --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "VIDEO_ID" \
  --profile almoprs
```

#### 2. Lambda関数の状態確認
```bash
# 関数設定
aws lambda get-function-configuration \
  --function-name video-article-processing-extract-transcript-prod \
  --profile almoprs

# 最新のContainer Image確認
aws lambda get-function \
  --function-name video-article-processing-extract-transcript-prod \
  --query 'Code.ImageUri' \
  --profile almoprs
```

#### 3. エラー調査
```bash
# エラーログ抽出
aws logs filter-log-events \
  --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod \
  --filter-pattern "ERROR" \
  --profile almoprs

# メモリ使用量確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/video-article-processing-extract-transcript-prod \
  --filter-pattern "REPORT" \
  --query 'events[*].message' \
  --output text \
  --profile almoprs | grep "Max Memory Used"
```

### ローカルデバッグ

#### Container Imageのローカル実行
```bash
# ローカルでContainer実行（x86_64環境推奨）
docker run -it \
  --platform linux/amd64 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e S3_BUCKET=video-article-processing-prod \
  -v ~/.aws:/root/.aws:ro \
  057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest \
  /bin/bash

# ARM64 Mac環境での注意
# --platform linux/amd64 を明示的に指定してx86_64エミュレーション

# Python環境でデバッグ
python
>>> import extract_transcript_lambda
>>> # デバッグコード実行
```

#### ローカルLambda実行
```bash
# SAM CLIを使用
sam local invoke ExtractTranscript \
  --event test-event.json \
  --docker-network lambda-local
```

### パフォーマンス分析

#### CloudWatch Insights クエリ
```sql
-- 処理時間分析
fields @timestamp, @duration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)

-- エラー率分析
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

#### X-Ray トレーシング（将来実装）
```python
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture('extract_audio')
def extract_audio_from_file(video_path, output_dir, video_id):
    # 処理時間の詳細追跡
    pass
```

---

**最終更新**: 2025年7月20日  
**作成者**: Claude Code  
**対象読者**: エンジニア・DevOpsチーム