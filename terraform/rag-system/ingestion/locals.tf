locals {
  ingestion_lambda_function_name = "${var.project_name}-ingestion-lambda"
  vector_db_bucket_prefix        = "${var.project_name}-vector-db"
  source_bucket_prefix           = "${var.project_name}-data-source"
  lambda_s3_key_filter           = var.lambda_s3_key_filter == "" ? "${var.project_name}/" : var.lambda_s3_key_filter
  vector_db_s3_path              = "${var.project_name}/database"
  dynamodb_table_name            = "${var.project_name}-commit-vector-db"
}
