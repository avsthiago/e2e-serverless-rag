module "ingestion" {
    source = "./ingestion"
    aws_region = local.region
    project_name = local.project_name
    log_level = "INFO"
    lambda_image_uri = local.ingestion_lambda_image_uri
    account_id = local.account_id
}
