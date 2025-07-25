# ==============================================================================
# Lambda Layers
# ==============================================================================

# Python依存関係Layer用のZIPファイル作成
data "archive_file" "python_layer" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambda/layers/python"
  output_path = "${path.module}/../aws-lambda/layers/python-layer.zip"
}

# FFmpeg Layer用のZIPファイル作成 - コメントアウト（Pythonライブラリに変更）
# data "archive_file" "ffmpeg_layer" {
#   type        = "zip"
#   source_dir  = "${path.module}/../aws-lambda/layers/ffmpeg"
#   output_path = "${path.module}/../aws-lambda/layers/ffmpeg-layer.zip"
# }

# Python依存関係Lambda Layer
resource "aws_lambda_layer_version" "python_deps" {
  filename                 = data.archive_file.python_layer.output_path
  layer_name               = "${var.project_name}-python-deps-${var.environment}"
  description              = "Python dependencies built for Lambda Linux x86_64"
  compatible_runtimes      = ["python3.11"]
  compatible_architectures = ["x86_64"]
  source_code_hash         = data.archive_file.python_layer.output_base64sha256

  depends_on = [data.archive_file.python_layer]
}

# FFmpeg Lambda Layer - コメントアウト（Pythonライブラリに変更）
# resource "aws_s3_object" "ffmpeg_layer" {
#   bucket = aws_s3_bucket.video_processing.id
#   key    = "layers/ffmpeg-layer.zip"
#   source = data.archive_file.ffmpeg_layer.output_path
#   etag   = filemd5(data.archive_file.ffmpeg_layer.output_path)
# }

# resource "aws_lambda_layer_version" "ffmpeg" {
#   s3_bucket               = aws_s3_bucket.video_processing.id
#   s3_key                  = aws_s3_object.ffmpeg_layer.key
#   layer_name              = "${var.project_name}-ffmpeg-${var.environment}"
#   description             = "FFmpeg binaries for audio processing (Linux x86_64)"
#   compatible_runtimes     = ["python3.11"]
#   compatible_architectures = ["x86_64"]
#   source_code_hash        = data.archive_file.ffmpeg_layer.output_base64sha256

#   depends_on = [aws_s3_object.ffmpeg_layer]
# }

# ==============================================================================
# Lambda Functions
# ==============================================================================

# Lambda関数用のZIPファイル作成
data "archive_file" "extract_transcript" {
  type        = "zip"
  source_file = "${path.module}/../aws-lambda/extract_transcript_lambda.py"
  output_path = "${path.module}/lambda_packages/extract_transcript.zip"
}

data "archive_file" "generate_article" {
  type        = "zip"
  source_file = "${path.module}/../aws-lambda/generate_article_lambda.py"
  output_path = "${path.module}/lambda_packages/generate_article.zip"
}

data "archive_file" "wordpress_publish" {
  type        = "zip"
  source_file = "${path.module}/../aws-lambda/wordpress_publish_lambda.py"
  output_path = "${path.module}/lambda_packages/wordpress_publish.zip"
}

# ==============================================================================
# Lambda関数1: extract_transcript
# ==============================================================================

resource "aws_lambda_function" "extract_transcript" {
  # Container Image形式に変更
  package_type = "Image"
  image_uri    = "057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest"
  
  function_name                  = "${var.project_name}-extract-transcript-${var.environment}"
  description                    = "動画から音声抽出・文字起こし（Container + FFmpeg）"
  role                          = aws_iam_role.extract_transcript_role.arn
  timeout                       = 900  # 15分
  memory_size                   = 2048  # Container環境では少し多めに
  # reserved_concurrent_executions = 5  # コメントアウト - アカウント制限回避

  # Container環境ではレイヤー不要
  # layers = [
  #   aws_lambda_layer_version.python_deps.arn
  # ]

  environment {
    variables = {
      OPENAI_API_KEY = var.openai_api_key
      S3_BUCKET      = aws_s3_bucket.video_processing.id
    }
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.extract_transcript_policy,
    aws_cloudwatch_log_group.extract_transcript
  ]
}

# ==============================================================================
# Lambda関数2: generate_article  
# ==============================================================================

resource "aws_lambda_function" "generate_article" {
  # Container Image形式に変更
  package_type = "Image"
  image_uri    = "057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest"
  
  function_name                  = "${var.project_name}-generate-article-${var.environment}"
  description                    = "文字起こしからHTML記事生成（Container）"
  role                          = aws_iam_role.generate_article_role.arn
  timeout                       = 900  # 15分
  memory_size                   = 1024
  # reserved_concurrent_executions = 5  # コメントアウト - アカウント制限回避

  # Container環境ではレイヤー不要
  # layers = [
  #   aws_lambda_layer_version.python_deps.arn
  # ]

  # generate_article用のハンドラを指定
  image_config {
    command = ["generate_article_lambda.lambda_handler"]
  }

  environment {
    variables = {
      OPENAI_API_KEY = var.openai_api_key
      S3_BUCKET      = aws_s3_bucket.video_processing.id
    }
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.generate_article_policy,
    aws_cloudwatch_log_group.generate_article
  ]
}

# ==============================================================================
# Lambda関数3: wordpress_publish
# ==============================================================================

resource "aws_lambda_function" "wordpress_publish" {
  # Container Image形式に変更
  package_type = "Image"
  image_uri    = "057493959080.dkr.ecr.ap-northeast-1.amazonaws.com/video-processing-lambda:latest"
  
  function_name                  = "${var.project_name}-wordpress-publish-${var.environment}"
  description                    = "HTML記事をWordPressに投稿（Container）"
  role                          = aws_iam_role.wordpress_publish_role.arn
  timeout                       = 900  # 15分
  memory_size                   = 1024
  # reserved_concurrent_executions = 5  # コメントアウト - アカウント制限回避

  # Container環境ではレイヤー不要
  # layers = [
  #   aws_lambda_layer_version.python_deps.arn
  # ]

  # wordpress_publish用のハンドラを指定
  image_config {
    command = ["wordpress_publish_lambda.lambda_handler"]
  }

  environment {
    variables = {
      WORDPRESS_SITE_URL      = var.wordpress_site_url
      WORDPRESS_USERNAME      = var.wordpress_username
      WORDPRESS_APP_PASSWORD  = var.wordpress_app_password
      S3_BUCKET              = aws_s3_bucket.video_processing.id
    }
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.wordpress_publish_policy,
    aws_cloudwatch_log_group.wordpress_publish
  ]
}

# ==============================================================================
# Lambda Permissions (S3からのトリガー用)
# ==============================================================================

resource "aws_lambda_permission" "s3_extract_transcript" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.extract_transcript.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.video_processing.arn
}

resource "aws_lambda_permission" "s3_generate_article" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_article.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.video_processing.arn
}

resource "aws_lambda_permission" "s3_wordpress_publish" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.wordpress_publish.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.video_processing.arn
}