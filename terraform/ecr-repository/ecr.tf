resource "aws_ecr_repository" "lambda_repository" {
  name = var.ingestion_ecr_repository_name
}

resource "aws_ecr_repository" "rag_repository" {
  name = var.rag_ecr_repository_name
}
