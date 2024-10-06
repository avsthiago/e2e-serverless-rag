resource "random_string" "bucket_data_source" {
  length  = 6
  special = false
  upper   = false
}

resource "aws_s3_bucket" "data_source" {
  bucket = "${local.source_bucket_prefix}-${random_string.bucket_data_source.result}"
}

resource "aws_s3_bucket_versioning" "bucket_data_source" {
  bucket = aws_s3_bucket.data_source.id
  versioning_configuration {
    status = "Disabled"
  }
}
