locals {
  rag_lambda_function_name = "${var.project_name}-rag-lambda"
  dynamodb_table_name      = "${var.project_name}-commit-vector-db"
  vector_db_s3_path        = "s3://${var.vector_db_bucket_name}/${var.project_name}/database"
}
