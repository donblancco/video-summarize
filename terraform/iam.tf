# ==============================================================================
# IAM ロールとポリシー
# ==============================================================================

# Lambda実行ロール用のAssumeRoleポリシー
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    
    actions = ["sts:AssumeRole"]
  }
}

# ==============================================================================
# Lambda関数1用IAMロール (extract_transcript)
# ==============================================================================

resource "aws_iam_role" "extract_transcript_role" {
  name               = "${var.project_name}-extract-transcript-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = local.common_tags
}

# S3アクセス用ポリシードキュメント
data "aws_iam_policy_document" "extract_transcript_policy" {
  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
  }

  # S3アクセス
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:HeadObject"
    ]
    resources = ["${aws_s3_bucket.video_processing.arn}/*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [aws_s3_bucket.video_processing.arn]
  }
}

resource "aws_iam_policy" "extract_transcript_policy" {
  name   = "${var.project_name}-extract-transcript-policy-${var.environment}"
  policy = data.aws_iam_policy_document.extract_transcript_policy.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "extract_transcript_policy" {
  role       = aws_iam_role.extract_transcript_role.name
  policy_arn = aws_iam_policy.extract_transcript_policy.arn
}

# ==============================================================================
# Lambda関数2用IAMロール (generate_article)
# ==============================================================================

resource "aws_iam_role" "generate_article_role" {
  name               = "${var.project_name}-generate-article-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = local.common_tags
}

# generate_article用ポリシー（extract_transcriptと同じS3権限）
resource "aws_iam_policy" "generate_article_policy" {
  name   = "${var.project_name}-generate-article-policy-${var.environment}"
  policy = data.aws_iam_policy_document.extract_transcript_policy.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "generate_article_policy" {
  role       = aws_iam_role.generate_article_role.name
  policy_arn = aws_iam_policy.generate_article_policy.arn
}

# ==============================================================================
# Lambda関数3用IAMロール (wordpress_publish)
# ==============================================================================

resource "aws_iam_role" "wordpress_publish_role" {
  name               = "${var.project_name}-wordpress-publish-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = local.common_tags
}

# wordpress_publish用ポリシー（extract_transcriptと同じS3権限）
resource "aws_iam_policy" "wordpress_publish_policy" {
  name   = "${var.project_name}-wordpress-publish-policy-${var.environment}"
  policy = data.aws_iam_policy_document.extract_transcript_policy.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "wordpress_publish_policy" {
  role       = aws_iam_role.wordpress_publish_role.name
  policy_arn = aws_iam_policy.wordpress_publish_policy.arn
}