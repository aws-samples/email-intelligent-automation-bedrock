# Import python's built-in regular expression library
import re
import argparse
import boto3
from botocore.exceptions import ClientError
import json
import chromadb
from sentence_transformers import SentenceTransformer

parser = argparse.ArgumentParser(description='Aggument parser to call Bedrock Models')

model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
region = 'us-west-2'

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=region)

parser.add_argument('--prompt', type=str, required=True, help='user prompt')
parser.add_argument('--modelid', type=str, default=model_id, help='bedrock model id')


args = parser.parse_args()

user_message = args.prompt+". List those data if exist and consider the date if given for filter the results."
model_id = args.modelid
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
