# ==============================================================================
# S3 バケット設定
# ==============================================================================

# メインの動画処理バケット
resource "aws_s3_bucket" "video_processing" {
  bucket = local.bucket_name

  tags = local.common_tags
}

# S3バケットのバージョニング設定
resource "aws_s3_bucket_versioning" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3バケットの暗号化設定
resource "aws_s3_bucket_server_side_encryption_configuration" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3バケットのCORS設定（Web UIアップロード用）
resource "aws_s3_bucket_cors_configuration" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*", "https://dwqp0tli97nsm.cloudfront.net"]
    max_age_seconds = 3000
  }
}

# S3バケットの公開アクセス設定（UIアップロード用に部分的に許可）
resource "aws_s3_bucket_public_access_block" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3バケットポリシー（UIからのアップロード許可）
resource "aws_s3_bucket_policy" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowUIUpload"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:PutObject"]
        Resource  = "${aws_s3_bucket.video_processing.arn}/uploads/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.video_processing]
}

# ==============================================================================
# S3 Event Notifications (Lambda Triggers)
# ==============================================================================

# S3バケット通知設定
resource "aws_s3_bucket_notification" "video_processing" {
  bucket = aws_s3_bucket.video_processing.id

  # 動画ファイルアップロード時のトリガー (Lambda 1)
  lambda_function {
    lambda_function_arn = aws_lambda_function.extract_transcript.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".mp4"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.extract_transcript.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".mov"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.extract_transcript.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".avi"
  }

  # 文字起こしファイル作成時のトリガー (Lambda 2)
  lambda_function {
    lambda_function_arn = aws_lambda_function.generate_article.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "transcripts/"
    filter_suffix       = ".txt"
  }

  # HTML記事作成時のトリガー (Lambda 3)
  lambda_function {
    lambda_function_arn = aws_lambda_function.wordpress_publish.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "articles/"
    filter_suffix       = ".html"
  }

  depends_on = [
    aws_lambda_permission.s3_extract_transcript,
    aws_lambda_permission.s3_generate_article,
    aws_lambda_permission.s3_wordpress_publish
  ]
}

# ==============================================================================
# UI専用S3バケット (Static Website Hosting + CloudFront)
# ==============================================================================

# UI専用バケット
resource "aws_s3_bucket" "ui_hosting" {
  bucket = "${var.project_name}-ui-almoprs-${var.environment}"

  tags = local.common_tags
}

# UI専用バケットの静的ウェブサイト設定
resource "aws_s3_bucket_website_configuration" "ui_hosting" {
  bucket = aws_s3_bucket.ui_hosting.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# UI専用バケットの公開アクセス設定
resource "aws_s3_bucket_public_access_block" "ui_hosting" {
  bucket = aws_s3_bucket.ui_hosting.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# UI専用バケットポリシー（CloudFrontからのアクセス）
resource "aws_s3_bucket_policy" "ui_hosting" {
  bucket = aws_s3_bucket.ui_hosting.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.ui_oai.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.ui_hosting.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.ui_hosting]
}

# ==============================================================================
# CloudFront Distribution for UI
# ==============================================================================

# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "ui_oai" {
  comment = "UI hosting OAI for ${var.project_name}-${var.environment}"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "ui_distribution" {
  origin {
    domain_name = aws_s3_bucket.ui_hosting.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.ui_hosting.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.ui_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "UI distribution for ${var.project_name}-${var.environment}"

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.ui_hosting.id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400

    # Lambda@Edge for Basic Authentication
    lambda_function_association {
      event_type   = "viewer-request"
      lambda_arn   = aws_lambda_function.basic_auth.qualified_arn
      include_body = false
    }
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

# ==============================================================================
# S3 Objects (Static Files)
# ==============================================================================

# アップロード用UI HTMLファイル
resource "aws_s3_object" "upload_ui" {
  bucket       = aws_s3_bucket.ui_hosting.id
  key          = "index.html"
  source       = "${path.module}/../aws-lambda/upload-ui.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../aws-lambda/upload-ui.html")

  tags = local.common_tags
}