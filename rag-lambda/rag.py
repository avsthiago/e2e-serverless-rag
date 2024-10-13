import boto3
import json
import lancedb
import os
from async_lru import alru_cache

region = os.getenv("AWS_REGION", "eu-central-1")
vector_db_path = os.getenv("VECTOR_DB_S3_PATH")
vector_db_table_name = os.getenv("VECTOR_DB_TABLE_NAME", "vector_db")
embedding_model = os.getenv("EMBEDDING_MODEL", "cohere.embed-multilingual-v3")
gen_model = os.getenv(
    "GEN_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"
)
bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


@alru_cache(maxsize=512)
async def cached_table():
    database = await lancedb.connect_async(vector_db_path)
    return await database.open_table(vector_db_table_name)


def question_to_embeddings(question):
    body = json.dumps(
        {
            "texts": [question],
            "input_type": "search_query",
        }
    )
    model_id = embedding_model
    response = bedrock_client.invoke_model(
        body=body, modelId=model_id, accept="*/*", contentType="application/json"
    )
    embeddings = json.loads(response["body"].read())
    return embeddings["embeddings"][0]


async def retrieve(question, table):
    embeddings = question_to_embeddings(question)
    chunks = (
        await table.vector_search(embeddings)
        .limit(3)
        .select(["file_name", "page_number", "text"])
        .to_list()
    )
    return chunks


def stream_response(response):
    event_stream = response.get("body", {})
    for event in event_stream:
        chunk = event.get("chunk")
        if chunk:
            message = json.loads(chunk.get("bytes").decode())
            if message["type"] == "content_block_delta":
                yield message["delta"]["text"] or ""
            elif message["type"] == "message_stop":
                return ""


def generate_prompt(user_input, chunks, messages):
    chunks_text = "\n\n".join([chunk["text"] for chunk in chunks])

    prompt = f"""
# Retrieved Information
{chunks_text}

# Conversation History
{messages}

# Current Query
User: {user_input}

# Task Instruction
Respond to the current query using only the retrieved information and conversation history provided above. Follow these guidelines strictly:

1. If the retrieved information directly answers the query, use it to formulate your response.
2. If the retrieved information is not relevant or insufficient to answer the query, respond with: "I'm sorry, but I don't have enough information in the provided context to answer this question accurately."
3. Do not use any external knowledge or information not present in this prompt.
    """
    print(prompt)

    return prompt


def filter_and_format_messages(messages, messages_limit):
    messages = [msg.strip() for msg in messages]
    # annotate messages with user or assistant role
    annotated_messages = []
    for i, msg in enumerate(messages):
        role = "user" if i % 2 == 0 else "assistant"
        annotated_messages.append({"role": role, "content": msg})

    # pick the last <messages_limit> messages
    if len(annotated_messages) > messages_limit:
        annotated_messages = annotated_messages[-messages_limit:]

    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in annotated_messages])


def generate_response(user_input, chunks, messages, messages_limit=10):
    filtered_messages = filter_and_format_messages(messages, messages_limit)

    prompt = generate_prompt(user_input, chunks, filtered_messages)
    response = bedrock_client.invoke_model_with_response_stream(
        modelId=gen_model,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.7,
                "system": """You are an AI assistant tasked with answering questions based solely on the provided information and conversation history. 
Do not use any knowledge beyond what is explicitly provided in this prompt. If the information given is insufficient 
to answer the query, clearly state this fact. You are always direct and concise in your responses.
""",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }
        ),
    )

    return stream_response(response)
