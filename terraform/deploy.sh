#!/bin/bash

# Terraform デプロイメントスクリプト
# macOS ARM64 → Lambda Linux x86_64 対応

set -e

echo "🚀 Terraform デプロイメント開始"
echo "🖥️  ローカル環境: $(uname -m)"
echo "🐧 ターゲット環境: Lambda Linux x86_64"

# 必要なツールの確認
echo "🔧 必要なツールをチェック中..."

# Terraform確認
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform が見つかりません"
    echo "💡 Terraform をインストールしてください: https://www.terraform.io/downloads"
    exit 1
fi

echo "✅ Terraform $(terraform version -json | jq -r '.terraform_version') 確認完了"

# AWS CLI確認
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI が見つかりません"
    echo "💡 AWS CLI をインストールしてください: https://aws.amazon.com/cli/"
    exit 1
fi

# AWS認証確認
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS認証が設定されていません"
    echo "💡 aws configure を実行してください"
    exit 1
fi

echo "✅ AWS CLI 認証確認完了"

# Docker確認（Lambda Layer ビルド用）
if ! command -v docker &> /dev/null; then
    echo "❌ Docker が見つかりません"
    echo "💡 Docker Desktop をインストールしてください"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker が起動していません"
    echo "💡 Docker Desktop を起動してください"
    exit 1
fi

echo "✅ Docker 確認完了"

# 設定ファイル確認
if [ ! -f "terraform.tfvars" ]; then
    echo "❌ terraform.tfvars が見つかりません"
    echo "💡 terraform.tfvars.example をコピーして terraform.tfvars を作成してください"
    echo "   cp terraform.tfvars.example terraform.tfvars"
    echo "   その後、実際の値を設定してください"
    exit 1
fi

echo "✅ 設定ファイル確認完了"

# Lambda Layerのビルド
echo "🔧 Lambda Layerをビルド中..."
cd ../aws-lambda

if [ ! -d "layers/python" ] || [ ! -d "layers/ffmpeg/bin" ]; then
    echo "⚙️  Lambda Layerが見つからないため、ビルドを実行します..."
    ./build-layers.sh
else
    echo "✅ Lambda Layerは既に存在します"
fi

cd ../terraform

# Lambda関数パッケージディレクトリ作成
mkdir -p lambda_packages

# Terraform初期化
echo "🔧 Terraform を初期化中..."
terraform init

# Terraform計画
echo "📋 Terraform 実行計画を作成中..."
terraform plan -var-file="terraform.tfvars" -out=tfplan

# ユーザー確認
echo ""
echo "📋 上記の実行計画を確認してください"
echo "❓ デプロイを続行しますか? (y/N)"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "❌ デプロイをキャンセルしました"
    exit 0
fi

# Terraform適用
echo "🚀 Terraform を適用中..."
terraform apply tfplan

# 結果表示
echo ""
echo "✅ デプロイ完了！"
echo ""
echo "=== デプロイ情報 ==="
terraform output

echo ""
echo "=== 使用方法 ==="
echo "1. S3バケットの uploads/ フォルダに動画ファイルをアップロード"
echo "2. メタデータに youtube-url を設定"
echo "3. 自動的に処理が開始されます"
echo ""
echo "🌐 アップロードUI:"
terraform output -raw upload_ui_url
echo ""
echo ""
echo "📁 ファイル構造："
echo "uploads/        # 動画ファイル"
echo "audio/          # 抽出された音声"
echo "transcripts/    # 文字起こし"
echo "articles/       # HTML記事"
echo "metadata/       # 処理メタデータ"