# ==============================================================================
# CloudWatch Log Groups
# ==============================================================================

# Lambda関数1用ログググループ
resource "aws_cloudwatch_log_group" "extract_transcript" {
  name              = "/aws/lambda/${var.project_name}-extract-transcript-${var.environment}"
  retention_in_days = 14

  tags = local.common_tags
}

# Lambda関数2用ロググループ
resource "aws_cloudwatch_log_group" "generate_article" {
  name              = "/aws/lambda/${var.project_name}-generate-article-${var.environment}"
  retention_in_days = 14

  tags = local.common_tags
}

# Lambda関数3用ロググループ
resource "aws_cloudwatch_log_group" "wordpress_publish" {
  name              = "/aws/lambda/${var.project_name}-wordpress-publish-${var.environment}"
  retention_in_days = 14

  tags = local.common_tags
}

# ==============================================================================
# CloudWatch Alarms (オプション)
# ==============================================================================

# Lambda関数のエラー監視
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    extract_transcript  = aws_lambda_function.extract_transcript.function_name
    generate_article    = aws_lambda_function.generate_article.function_name
    wordpress_publish   = aws_lambda_function.wordpress_publish.function_name
  }

  alarm_name          = "${each.key}-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors lambda errors for ${each.key}"
  alarm_actions       = []  # SNS topic ARN would go here

  dimensions = {
    FunctionName = each.value
  }

  tags = local.common_tags
}

# Lambda関数の実行時間監視
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = {
    extract_transcript  = aws_lambda_function.extract_transcript.function_name
    generate_article    = aws_lambda_function.generate_article.function_name
    wordpress_publish   = aws_lambda_function.wordpress_publish.function_name
  }

  alarm_name          = "${each.key}-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "600000"  # 10分（ミリ秒）
  alarm_description   = "This metric monitors lambda duration for ${each.key}"
  alarm_actions       = []  # SNS topic ARN would go here

  dimensions = {
    FunctionName = each.value
  }

  tags = local.common_tags
}