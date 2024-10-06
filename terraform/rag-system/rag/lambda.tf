locals {
  # Access to the source bucket
  s3_access = {
    vector_db_access = {
      effect = "Allow",
      actions = [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      resources = [
        "arn:aws:s3:::${var.vector_db_bucket_name}",
        "arn:aws:s3:::${var.vector_db_bucket_name}/*"
      ]
    }
  }

  # Access to the DynamoDB table
  dynamodb_access = {
    table_interaction = {
      effect = "Allow",
      actions = [
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      resources = [
        var.dynamodb_commit_store_arn
      ]
    }
  }

  # Access to Bedrock
  bedrock_access = {
    bedrock_access = {
      effect = "Allow",
      actions = [
        "bedrock:*"
      ],
      resources = [
        "*"
      ]
    }
  }

  cloudwatch_logs_access = {
    logs_access = {
      effect = "Allow",
      actions = [
       "logs:PutLogEvents",
        "logs:CreateLogStream",
        "logs:CreateLogGroup"
      ],
      resources = [
        "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/${local.rag_lambda_function_name}:*:*",
        "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/${local.rag_lambda_function_name}:*"
      ]
    }
  }

  lambda_policy_statements = merge(
    local.s3_access,
    local.dynamodb_access,
    local.bedrock_access,
    local.cloudwatch_logs_access
  )
}

module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 5.0"

  function_name = local.rag_lambda_function_name
  description   = "A function that offers a RAG backend and frontend"
  image_uri     = var.lambda_image_uri

  create_package = false
  package_type   = "Image"
  publish        = true
  attach_policy_statements = true
  cloudwatch_logs_retention_in_days = 3

  memory_size = 1024
  timeout     = 600

  policy_statements = local.lambda_policy_statements

  environment_variables = {
    "LANCEDB_S3_BUCKET"   = var.vector_db_bucket_name,
    "LANCEDB_S3_PATH"     = local.vector_db_s3_path,
    "DYNAMODB_TABLE_NAME" = local.dynamodb_table_name,
    "LOG_LEVEL"           = var.log_level,
    "AWS_LWA_INVOKE_MODE" = "RESPONSE_STREAM"
  }
}

resource "aws_lambda_function_url" "function_url" {
  function_name      = local.rag_lambda_function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  depends_on = [module.lambda_function]
}

resource "aws_lambda_permission" "function_url_permission" {
  statement_id  = "AllowFunctionUrlInvoke"
  action        = "lambda:InvokeFunctionUrl"
  function_name = local.rag_lambda_function_name
  principal     = "*"

  function_url_auth_type = "NONE"
}