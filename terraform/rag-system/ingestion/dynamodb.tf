resource "aws_dynamodb_table" "lance_db_commit_store" {
  name         = local.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "base_uri"
  range_key    = "version"

  attribute {
    name = "base_uri"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }
}