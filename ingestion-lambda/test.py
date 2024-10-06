import os

os.environ["LANCEDB_S3_BUCKET"] = "house-rag-vector-db-xxxx"
os.environ["LANCEDB_S3_PATH"] = "house-rag/database"
os.environ["DYNAMODB_TABLE_NAME"] = "house-rag-commit-vector-db"
os.environ["AWS_REGION"] = "eu-central-1"
os.environ["LOG_LEVEL"] = "DEBUG"

event = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "house-rag-data-source-ex4hbt"},
                "object": {"key": "house-rag/test file.pdf"},
            }
        }
    ]
}


import handler

handler.lambda_handler(event, None)
