variable "aws_region" {
  description = "The AWS region where resources will be created."
  type        = string
  default     = "eu-central-1"
}

variable "account_id" {
  description = "The AWS account ID."
  type        = string
}

variable "project_name" {
  description = "The name of the project."
  type        = string
}

variable "lambda_image_uri" {
  description = "The URI of the container image in ECR for the Lambda function."
  type        = string
}

variable "log_level" {
  description = "The log level for the Lambda function."
  type        = string
  default     = "INFO"
}

variable "vector_db_bucket_name" {
  description = "The Name of the S3 bucket for storing the vector database."
  type        = string
}

variable "dynamodb_commit_store_arn" {
  description = "The ARN of the DynamoDB table for storing commits."
  type        = string
}