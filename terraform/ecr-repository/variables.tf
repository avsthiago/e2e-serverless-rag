variable "aws_region" {
  description = "The AWS region where resources will be created."
  type        = string
}

variable "ecr_repository_name" {
  description = "The name of the ECR repository."
  type        = string
}
