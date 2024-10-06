locals {
  rag_lambda_function_name = "${var.project_name}-rag-lambda"
  vector_db_bucket_prefix  = "${var.project_name}-vector-db"
  vector_db_s3_path        = "${var.project_name}/database"
  dynamodb_table_name      = "${var.project_name}-commit-vector-db"
}
