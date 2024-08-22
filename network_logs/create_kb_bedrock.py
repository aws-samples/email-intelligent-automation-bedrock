import json
import time
import os
import boto3
from botocore.exceptions import ClientError
import pprint
from utility import create_bedrock_execution_role, create_oss_policy_attach_bedrock_execution_role, create_policies_in_oss, interactive_sleep
import random
from retrying import retry
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError

suffix = random.randrange(200, 900)

sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
region_name = 'us-west-2'
bedrock_agent_client = boto3_session.client('bedrock-agent', region_name=region_name)
service = 'aoss'
s3_client = boto3.client('s3')
account_id = sts_client.get_caller_identity()["Account"]
s3_suffix = f"{region_name}-{account_id}"
bucket_name = f'bedrock-kb-{s3_suffix}' # replace it with your bucket name.
pp = pprint.PrettyPrinter(indent=2)

# Check if bucket exists, and if not create S3 bucket for knowledge base data source
try:
    s3_client.head_bucket(Bucket=bucket_name)
    print(f'Bucket {bucket_name} Exists')
except ClientError as e:
    print(f'Creating bucket {bucket_name}')
    if region_name == "us-west-2":
        s3bucket = s3_client.create_bucket(
            Bucket=bucket_name)
    else:
        s3bucket = s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={ 'LocationConstraint': region_name }
    )

vector_store_name = f'hybrid-bedrock-kb-{suffix}'
index_name = f"hybrid-bedrock-kb-index-{suffix}"
aoss_client = boto3_session.client('opensearchserverless',region_name='us-west-2')
bedrock_kb_execution_role = create_bedrock_execution_role(bucket_name=bucket_name)
bedrock_kb_execution_role_arn = bedrock_kb_execution_role['Role']['Arn']

# create security, network and data access policies within OSS
encryption_policy, network_policy, access_policy = create_policies_in_oss(vector_store_name=vector_store_name,
                       aoss_client=aoss_client,
                       bedrock_kb_execution_role_arn=bedrock_kb_execution_role_arn)
collection = aoss_client.create_collection(name=vector_store_name,type='VECTORSEARCH')

pp.pprint(collection)

# Get the OpenSearch serverless collection URL
collection_id = collection['createCollectionDetail']['id']
host = collection_id + '.' + region_name + '.aoss.amazonaws.com'
print(host)

# This can take couple of minutes to finish
response = aoss_client.batch_get_collection(names=[vector_store_name])
# Periodically check collection status
while (response['collectionDetails'][0]['status']) == 'CREATING':
    print('Creating collection...')
    interactive_sleep(30)
    response = aoss_client.batch_get_collection(names=[vector_store_name])
print('\nCollection successfully created:')
pp.pprint(response["collectionDetails"])

# create opensearch serverless access policy and attach it to Bedrock execution role

try:
    create_oss_policy_attach_bedrock_execution_role(collection_id=collection_id,
                                                    bedrock_kb_execution_role=bedrock_kb_execution_role)
    # It can take up to a minute for data access rules to be enforced
    interactive_sleep(60)
except Exception as e:
    print("Policy already exists")
    pp.pprint(e)

# Create the vector index in Opensearch serverless, with the knn_vector field index mapping, specifying the dimension size, name and engine.

credentials = boto3.Session().get_credentials()
awsauth = auth = AWSV4SignerAuth(credentials, region_name, service)

index_name = f"hybrid-kb-index-{suffix}"
body_json = {
   "settings": {
      "index.knn": "true",
       "number_of_shards": 1,
       "knn.algo_param.ef_search": 512,
       "number_of_replicas": 0,
   },
   "mappings": {
      "properties": {
         "vector": {
            "type": "knn_vector",
            "dimension": 1536,
             "method": {
                 "name": "hnsw",
                 "engine": "faiss",
                 "space_type": "l2"
             },
         },
         "text": {
            "type": "text"
         },
         "text-metadata": {
            "type": "text"         }
      }
   }
}

# Build the OpenSearch client
oss_client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

# Create index
try:
    response = oss_client.indices.create(index=index_name, body=json.dumps(body_json))
    print('\nCreating index:')
    pp.pprint(response)

    # index creation can take up to a minute
    interactive_sleep(60)
except RequestError as e:
    # you can delete the index if its already exists
    # oss_client.indices.delete(index=index_name)
    print(f'Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to delete, and recreate the index')
