locals {
  # Access to the source bucket
  s3_access = {
    data_source_access = {
      effect = "Allow",
      actions = [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      resources = [
        aws_s3_bucket.data_source.arn,
        "${aws_s3_bucket.data_source.arn}/*"
      ]
    },
    vector_db_access = {
      effect = "Allow",
      actions = [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      resources = [
        aws_s3_bucket.vector_db.arn,
        "${aws_s3_bucket.vector_db.arn}/*"
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
        aws_dynamodb_table.lance_db_commit_store.arn
      ]
    }
  }

  # Access to Textract and Bedrock
  textract_bedrock_access = {
    textract_access = {
      effect = "Allow",
      actions = [
        "textract:*"
      ],
      resources = [
        "*"
      ]
    },
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
        "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/${local.ingestion_lambda_function_name}:*:*",
        "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/${local.ingestion_lambda_function_name}:*"
      ]
    }
  }

  lambda_policy_statements = merge(
    local.s3_access,
    local.dynamodb_access,
    local.textract_bedrock_access,
    local.cloudwatch_logs_access
  )
}




# # Custom policies
# resource "aws_iam_policy" "lambda_policy" {
#   name        = "${local.ingestion_lambda_function_name}-policy"
#   path        = "/"
#   description = "Policy for Lambda function to access required AWS services"

#   policy = jsonencode({
#     # Version = "2012-10-17",
#     # Statement = [
#     #   {
#     #     Sid = "DataStoreAndVectorDBPermissions",
#     #     Effect      = "Allow",
#     #     Action = [
#     #       "s3:GetObject",
#     #       "s3:ListBucket",
#     #       "s3:PutObject",
#     #       "s3:DeleteObject"
#     #     ],
#     #     Resource = [
#     #       aws_s3_bucket.data_source.arn,
#     #       "${aws_s3_bucket.data_source.arn}/*",
#     #       aws_s3_bucket.vector_db.arn,
#     #       "${aws_s3_bucket.vector_db.arn}/*"
#     #     ]
#     #   },
#       # {
#       #   Sid = "DynamoDBPermissions",
#       #   Effect      = "Allow",
#       #   Action = [
#       #     "dynamodb:CreateTable",
#       #     "dynamodb:DescribeTable",
#       #     "dynamodb:PutItem",
#       #     "dynamodb:GetItem",
#       #     "dynamodb:UpdateItem",
#       #     "dynamodb:DeleteItem",
#       #     "dynamodb:Scan",
#       #     "dynamodb:Query"
#       #   ],
#       #   Resource = aws_dynamodb_table.lance_db_commit_store.arn
#       # },
#       {
#         Sid = "TextractAndBedrockPermissions",
#         Effect      = "Allow",
#         Action = [
#           "textract:*",
#           "bedrock:*"
#         ],
#         Resource = "*"
#       }
#     ]
#   })
# }

# # Attach Custom Policy to Lambda Role
# resource "aws_iam_role_policy_attachment" "lambda_custom_policy" {
#   role       = aws_iam_role.lambda_role.name
#   policy_arn = aws_iam_policy.lambda_policy.arn
# }

module "lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 5.0"

  function_name = local.ingestion_lambda_function_name
  description   = "Lambda function for reading data from S3 and storing in LanceDB"
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
    "SOURCE_BUCKET_NAME"  = aws_s3_bucket.data_source.bucket,
    "LANCEDB_S3_BUCKET"   = aws_s3_bucket.vector_db.bucket,
    "LANCEDB_S3_PATH"     = local.vector_db_s3_path,
    "DYNAMODB_TABLE_NAME" = local.dynamodb_table_name,
    "LOG_LEVEL"           = var.log_level,
  }
}

# Allow S3 to Invoke the Lambda Function
resource "aws_lambda_permission" "s3_lambda" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_source.arn
}

# Configure S3 Event Notification to Trigger Lambda Function
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.data_source.id

  lambda_function {
    lambda_function_arn = module.lambda_function.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = local.lambda_s3_key_filter
  }

  depends_on = [aws_lambda_permission.s3_lambda]
}
