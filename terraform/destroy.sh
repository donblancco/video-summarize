#!/bin/bash

# Terraform リソース削除スクリプト

set -e

echo "🗑️  Terraform リソース削除開始"

# 確認
echo "⚠️  警告: すべてのAWSリソースが削除されます"
echo "   - S3バケットとすべてのファイル"
echo "   - Lambda関数とLayer"
echo "   - IAMロールとポリシー"
echo "   - CloudWatchロググループ"
echo ""
echo "❓ 本当にすべてのリソースを削除しますか? (yes/NO)"
read -r response

if [[ "$response" != "yes" ]]; then
    echo "❌ 削除をキャンセルしました"
    exit 0
fi

# 設定ファイル確認
if [ ! -f "terraform.tfvars" ]; then
    echo "❌ terraform.tfvars が見つかりません"
    exit 1
fi

# S3バケットのファイルを事前削除（Terraformでは空でないバケットは削除できない）
echo "🧹 S3バケット内のファイルを削除中..."
BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")

if [ -n "$BUCKET_NAME" ]; then
    # S3バケットのすべてのバージョンを削除
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output text | while read -r key version_id; do
        if [ -n "$key" ] && [ -n "$version_id" ]; then
            aws s3api delete-object --bucket "$BUCKET_NAME" --key "$key" --version-id "$version_id"
        fi
    done
    
    # Delete Markersも削除
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output text | while read -r key version_id; do
        if [ -n "$key" ] && [ -n "$version_id" ]; then
            aws s3api delete-object --bucket "$BUCKET_NAME" --key "$key" --version-id "$version_id"
        fi
    done
    
    echo "✅ S3バケット内のファイル削除完了"
else
    echo "⚠️  S3バケット名を取得できませんでした（すでに削除済みの可能性）"
fi

# Terraform destroy実行
echo "🚀 Terraform destroy を実行中..."
terraform destroy -var-file="terraform.tfvars" -auto-approve

# 一時ファイルを削除
echo "🧹 一時ファイルを削除中..."
rm -f tfplan
rm -rf lambda_packages/
rm -f ../aws-lambda/layers/*.zip

echo ""
echo "✅ すべてのリソースの削除が完了しました！"
echo ""
echo "削除されたリソース:"
echo "  - S3バケットとすべてのファイル"
echo "  - Lambda関数とLayer"
echo "  - IAMロールとポリシー"
echo "  - CloudWatchロググループとアラーム"