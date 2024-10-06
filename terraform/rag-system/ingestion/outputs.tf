output "vector_db_bucket_name" {
    description = "The name of the S3 bucket for storing the VectorDB."
    value       = aws_s3_bucket.vector_db.bucket
}

output "dynamodb_commit_store_arn" {
    description = "The ARN of the DynamoDB table for storing commits."
    value       = aws_dynamodb_table.lance_db_commit_store.arn
}