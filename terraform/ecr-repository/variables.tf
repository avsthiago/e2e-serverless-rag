variable "aws_region" {
  description = "The AWS region where resources will be created."
  type        = string
}

variable "ingestion_ecr_repository_name" {
  description = "The name of the ECR repository for the ingestion lambda."
  type        = string
}

variable "rag_ecr_repository_name" {
  description = "The name of the ECR repository for the RAG lambda."
  type        = string
}
