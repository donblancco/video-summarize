# ==============================================================================
# Lambda@Edge for Basic Authentication
# ==============================================================================

# Lambda@Edge function for Basic Authentication
data "archive_file" "basic_auth" {
  type        = "zip"
  source_file = "${path.module}/basic_auth_lambda.js"
  output_path = "${path.module}/lambda_packages/basic_auth.zip"
}

# IAM role for Lambda@Edge
resource "aws_iam_role" "basic_auth_lambda_edge_role" {
  name = "${var.project_name}-basic-auth-lambda-edge-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "edgelambda.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for Lambda@Edge
resource "aws_iam_role_policy_attachment" "basic_auth_lambda_edge_policy" {
  role       = aws_iam_role.basic_auth_lambda_edge_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda@Edge function
resource "aws_lambda_function" "basic_auth" {
  # Lambda@Edge は us-east-1 リージョンでのみ作成可能
  provider = aws.us_east_1

  filename                       = data.archive_file.basic_auth.output_path
  function_name                  = "${var.project_name}-basic-auth-${var.environment}"
  role                          = aws_iam_role.basic_auth_lambda_edge_role.arn
  handler                       = "basic_auth_lambda.handler"
  source_code_hash              = data.archive_file.basic_auth.output_base64sha256
  runtime                       = "nodejs18.x"
  timeout                       = 5
  memory_size                   = 128
  publish                       = true

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.basic_auth_lambda_edge_policy,
    aws_cloudwatch_log_group.basic_auth
  ]
}

# CloudWatch Log Group for Lambda@Edge
resource "aws_cloudwatch_log_group" "basic_auth" {
  # Lambda@Edge のログは us-east-1 に作成される
  provider = aws.us_east_1
  
  name              = "/aws/lambda/${var.project_name}-basic-auth-${var.environment}"
  retention_in_days = 14

  tags = local.common_tags
}