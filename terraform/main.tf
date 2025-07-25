# ==============================================================================
# 動画処理・記事生成・WordPress投稿システム - Terraform設定
# ==============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

# ==============================================================================
# Provider設定
# ==============================================================================

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "video-article-processing"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Lambda@Edge requires us-east-1 region
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  
  default_tags {
    tags = {
      Project     = "video-article-processing"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ==============================================================================
# 変数定義
# ==============================================================================

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "video-article-processing"
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "wordpress_site_url" {
  description = "WordPress site URL"
  type        = string
}

variable "wordpress_username" {
  description = "WordPress username"
  type        = string
}

variable "wordpress_app_password" {
  description = "WordPress application password"
  type        = string
  sensitive   = true
}

# ==============================================================================
# Local Values
# ==============================================================================

locals {
  bucket_name = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ==============================================================================
# Data Sources
# ==============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}