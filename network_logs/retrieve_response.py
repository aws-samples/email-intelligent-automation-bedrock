# Import python's built-in regular expression library
import re
import boto3
from botocore.exceptions import ClientError
import json
import chromadb
from sentence_transformers import SentenceTransformer

# Import the hints module from the utils package
#from utils import hints

model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
region = 'us-east-1'

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=region)

user_message = "Do you see any unusual traffic pattern on 17-Aug-2024? List those data"

persist_directory = './chromadb_network_logs'
client = chromadb.PersistentClient(path=persist_directory)
collection = client.get_collection("network_logs_collection")
model = SentenceTransformer('all-mpnet-base-v2')
query_embedding = model.encode([user_message])[0]

query_embedding = query_embedding.tolist()
# Retrieve relevant logs
results = collection.query(
                        query_embeddings=[query_embedding],
                 n_results=10,
		 where={"issue_description": {"$ne": "Normal network activity"}}
                    )

print(results)

def get_completion(prompt, system_prompt=None, prefill=None):
    inference_config = {
        "temperature": 0.0,
         "maxTokens": 1000
    }
    converse_api_params = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": inference_config
    }
    if system_prompt:
        converse_api_params["system"] = [{"text": system_prompt}]
    if prefill:
        converse_api_params["messages"].append({"role": "assistant", "content": [{"text": prefill}]})
    try:
        response = bedrock_client.converse(**converse_api_params)
        text_content = response['output']['message']['content'][0]['text']
        return text_content

    except ClientError as err:
        message = err.response['Error']['Message']
        print(f"A client error occured: {message}")

prompt = f"""Here is the data you need to use:
<data>
{results}
</data>

Here is the user's question:
<question>
{user_message}
</question>"""

output = get_completion(prompt)

print(output)
