resource "random_string" "bucket_vector_db" {
  length  = 6
  special = false
  upper   = false
}

resource "aws_s3_bucket" "vector_db" {
  bucket = "${local.vector_db_bucket_prefix}-${random_string.bucket_vector_db.result}"
}

resource "aws_s3_bucket_versioning" "bucket_vector_db" {
  bucket = aws_s3_bucket.vector_db.id
  versioning_configuration {
    status = "Disabled"
  }
}