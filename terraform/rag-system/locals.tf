locals {
  region = "eu-central-1"
  project_name = "house-rag"
  ingestion_lambda_image_tag = "0.0.6"
  account_id = data.aws_caller_identity.current.account_id
  ingestion_lambda_image_uri = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/house-rag-ingestion:${local.ingestion_lambda_image_tag}"
}

data "aws_caller_identity" "current" {}
