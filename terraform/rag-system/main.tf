module "ingestion" {
  source           = "./ingestion"
  aws_region       = local.region
  project_name     = local.project_name
  log_level        = "INFO"
  lambda_image_uri = local.ingestion_lambda_image_uri
  account_id       = local.account_id
}

module "rag" {
  source                    = "./rag"
  aws_region                = local.region
  project_name              = local.project_name
  log_level                 = "INFO"
  lambda_image_uri          = local.rag_lambda_image_uri
  account_id                = local.account_id
  vector_db_bucket_name     = module.ingestion.vector_db_bucket_name
  dynamodb_commit_store_arn = module.ingestion.dynamodb_commit_store_arn
}