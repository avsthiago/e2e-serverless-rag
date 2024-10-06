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

variable "lambda_s3_key_filter" {
  description = "The S3 key prefix filter for triggering the Lambda function."
  type        = string
  default = ""
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
