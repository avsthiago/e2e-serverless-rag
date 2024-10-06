import os
import json
import tempfile
import shutil
import boto3
from pypdf import PdfReader, PdfWriter
import textractcaller as tc
import textractor.entities.document as textractor
import lancedb
from lancedb.pydantic import Vector, LanceModel
from aws_lambda_powertools import Logger
from urllib.parse import unquote_plus


logger = Logger(
    service="rag-ingestion",
    level=os.getenv("LOG_LEVEL", "INFO"),
    use_rfc3339=True,
    log_uncaught_exceptions=True,
)

# Get region from environment variable
region = os.getenv("AWS_REGION", "eu-central-1")

# AWS clients
s3_client = boto3.client("s3", region_name=region)
textract_client = boto3.client("textract", region_name=region)
bedrock_client = boto3.client("bedrock-runtime", region_name=region)
dynamodb = boto3.client("dynamodb", region_name=region)

ddb_table_name = os.getenv("DYNAMODB_TABLE_NAME")
lancedb_table_name = "vector_db"

def connect_to_lancedb():
    lancedb_s3_bucket = os.getenv("LANCEDB_S3_BUCKET")
    lancedb_s3_path = os.getenv("LANCEDB_S3_PATH")
    s3_db_uri = (
        f"s3+ddb://{lancedb_s3_bucket}/{lancedb_s3_path}/?ddbTableName={ddb_table_name}"
    )
    return lancedb.connect(s3_db_uri)


db = connect_to_lancedb()


def create_lancedb_table_if_not_exists(db, table_name):
    class Schema(LanceModel):
        file_name: str
        vector: Vector(1024)
        page_number: int
        text: str

    if table_name in db.table_names():
        logger.info(f"LanceDB table {table_name} already exists.")
        return db.open_table(table_name)
    else:
        logger.info(f"LanceDB table {table_name} does not exist. Creating table.")
        return db.create_table(name=table_name, schema=Schema, exist_ok=True)


lancedb_table = create_lancedb_table_if_not_exists(db, lancedb_table_name)

# Define linearization configuration for Textractor
linearization_config = textractor.TextLinearizationConfig(
    hide_figure_layout=True,
    title_prefix="# ",
    section_header_prefix="## ",
    list_element_prefix="*",
)


def lambda_handler(event, _):
    # Get the bucket and key from the S3 event
    try:
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        # needed for when the key has special characters
        key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])
        logger.info(f"Processing file {key} from bucket {bucket}.")
    except Exception as e:
        logger.error(f"Error getting bucket and key from event: {e}")
        raise e

    if not key.lower().endswith(".pdf"):
        logger.error("The provided file is not a PDF.")
        raise ValueError("The provided file is not a PDF.")

    temp_folder = tempfile.mkdtemp()
    logger.debug(f"Created temporary folder {temp_folder}")

    # Download the PDF file from S3 to temp folder
    try:
        file_name = key.split("/")[-1]
        temp_file = os.path.join(temp_folder, file_name)
        s3_client.download_file(bucket, key, temp_file)
        logger.info(f"Downloaded file {key} from bucket {bucket} to {temp_file}.")
    except Exception as e:
        logger.error(f"Failed to download file from S3: {e}")
        raise e

    # Process the PDF file
    try:
        process_pdf(temp_file, file_name, lancedb_table)
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        raise e
    finally:
        # Clean up the temp folder
        try:
            shutil.rmtree(temp_folder)
            logger.debug(f"Deleted temporary folder {temp_folder}.")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary folder {temp_folder}: {e}")


def process_pdf(pdf_path, file_name, lancedb_table):
    pdf_reader = PdfReader(pdf_path)
    total_pages = len(pdf_reader.pages)
    logger.info(f"PDF file has {total_pages} pages.")

    # For each page, extract text and process
    for page_number in range(total_pages):
        logger.info(f"Processing page {page_number + 1}/{total_pages}.")
        text = extract_text_from_pdf_page(pdf_reader, page_number)
        if not text.strip():
            logger.warning(f"No text found on page {page_number + 1}. Skipping.")
            continue
        chunks = split_text_into_chunks(text, max_length=300, overlap=50)
        embeddings = get_embeddings(chunks)
        data = prepare_data(file_name, page_number + 1, embeddings)
        insert_data_into_lancedb(data, lancedb_table)


def extract_text_from_pdf_page(pdf_reader, page_number):
    # Create a temp file for the page
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf_reader.pages[page_number])
        pdf_writer.write(tmp_pdf)
        page_temp_file = tmp_pdf.name
    logger.debug(
        f"Created temporary PDF file for page {page_number + 1}: {page_temp_file}"
    )

    # Call Textract on the page
    try:
        textract_response = tc.call_textract(
            input_document=page_temp_file,
            features=[],
            call_mode=tc.Textract_Call_Mode.FORCE_SYNC,
            boto3_textract_client=textract_client,
        )
        page = textractor.Document.open(textract_response)
        text = page.get_text(linearization_config)
        logger.debug(f"Extracted text from page {page_number + 1}.")
    except Exception as e:
        logger.error(f"Error extracting text from page {page_number + 1}: {e}")
        text = ""
    finally:
        # Clean up the temp page file
        try:
            os.remove(page_temp_file)
        except Exception as e:
            logger.warning(f"Error deleting temporary page file {page_temp_file}: {e}")

    return text


def recursively_split_text(text, max_length, overlap):
    if len(text) <= max_length:
        return [text]
    else:
        split_index = text.rfind(" ", 0, max_length)
        if split_index == -1:
            split_index = max_length
        next_start = max(0, split_index - overlap)
        return [text[:split_index]] + recursively_split_text(
            text[next_start:].strip(), max_length, overlap
        )


def split_text_into_chunks(text, max_length=300, overlap=50):
    return recursively_split_text(text, max_length, overlap)


def get_embeddings(chunks):
    body = json.dumps(
        {
            "texts": chunks,
            "input_type": "search_document",
        }
    )
    model_id = "cohere.embed-multilingual-v3"
    try:
        response = bedrock_client.invoke_model(
            body=body, modelId=model_id, accept="*/*", contentType="application/json"
        )
        embeddings = json.loads(response["body"].read())
        logger.debug(f"Received embeddings for {len(chunks)} chunks.")
        return embeddings
    except Exception as e:
        logger.error(f"Error getting embeddings: {e}")
        return {"embeddings": [], "texts": []}


def prepare_data(file_name, page_number, embeddings):
    data = [
        {
            "file_name": file_name,
            "page_number": page_number,
            "text": text,
            "vector": embed,
        }
        for embed, text in zip(
            embeddings.get("embeddings", []), embeddings.get("texts", [])
        )
    ]
    logger.debug(f"Prepared data for page {page_number} with {len(data)} entries.")
    return data


def insert_data_into_lancedb(data, table):
    if data:
        table.add(data)
        logger.info(f"Inserted {len(data)} records into LanceDB table.")
    else:
        logger.warning("No data to insert into LanceDB table.")
