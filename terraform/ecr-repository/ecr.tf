resource "aws_ecr_repository" "lambda_repository" {
  name = var.ecr_repository_name
}
