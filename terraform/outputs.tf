# ==============================================================================
# Outputs
# ==============================================================================

output "s3_bucket_name" {
  description = "S3バケット名"
  value       = aws_s3_bucket.video_processing.id
}

output "s3_bucket_arn" {
  description = "S3バケットARN"
  value       = aws_s3_bucket.video_processing.arn
}


output "ui_bucket_name" {
  description = "UI専用S3バケット名"
  value       = aws_s3_bucket.ui_hosting.id
}

output "cloudfront_domain_name" {
  description = "CloudFront ディストリビューション URL"
  value       = aws_cloudfront_distribution.ui_distribution.domain_name
}

output "upload_ui_url" {
  description = "アップロードUI URL (CloudFront)"
  value       = "https://${aws_cloudfront_distribution.ui_distribution.domain_name}"
}

output "s3_ui_website_endpoint" {
  description = "S3 UI ウェブサイトエンドポイント"
  value       = aws_s3_bucket_website_configuration.ui_hosting.website_endpoint
}

output "lambda_functions" {
  description = "Lambda関数の情報"
  value = {
    extract_transcript = {
      function_name = aws_lambda_function.extract_transcript.function_name
      arn           = aws_lambda_function.extract_transcript.arn
    }
    generate_article = {
      function_name = aws_lambda_function.generate_article.function_name
      arn           = aws_lambda_function.generate_article.arn
    }
    wordpress_publish = {
      function_name = aws_lambda_function.wordpress_publish.function_name
      arn           = aws_lambda_function.wordpress_publish.arn
    }
  }
}

output "lambda_layers" {
  description = "Lambda Layerの情報"
  value = {
    python_deps = {
      arn     = aws_lambda_layer_version.python_deps.arn
      version = aws_lambda_layer_version.python_deps.version
    }
    # ffmpeg = {
    #   arn     = aws_lambda_layer_version.ffmpeg.arn
    #   version = aws_lambda_layer_version.ffmpeg.version
    # }  # ffmpeg-pythonライブラリ使用のためコメントアウト
  }
}

output "cloudwatch_log_groups" {
  description = "CloudWatch ロググループ"
  value = {
    extract_transcript  = aws_cloudwatch_log_group.extract_transcript.name
    generate_article    = aws_cloudwatch_log_group.generate_article.name
    wordpress_publish   = aws_cloudwatch_log_group.wordpress_publish.name
  }
}

output "deployment_info" {
  description = "デプロイメント情報"
  value = {
    aws_region    = var.aws_region
    environment   = var.environment
    project_name  = var.project_name
    bucket_name   = local.bucket_name
  }
}