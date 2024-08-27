import boto3
from utility import interactive_sleep
import argparse

region_name = 'us-west-2'
parser = argparse.ArgumentParser(description='Aggument parser for KB ID and DataSaource ID')

parser.add_argument('--kbid', type=str, required=True, help='knowledgeBaseId')
parser.add_argument('--dsid', type=str, default=model_id, help='dataSourceId')
args = parser.parse_args()
knowledgeBaseId = args.kbid
dataSourceId = args.dsid


boto3_session = boto3.session.Session()
bedrock_agent_client = boto3_session.client('bedrock-agent', region_name=region_name)

# Start an ingestion job
start_job_response = bedrock_agent_client.start_ingestion_job(knowledgeBaseId = knowledgeBaseId, dataSourceId = dataSourceId)

job = start_job_response["ingestionJob"]

# Get job 
while(job['status']!='COMPLETE' ):
    get_job_response = bedrock_agent_client.get_ingestion_job(
      knowledgeBaseId = kb['knowledgeBaseId'],
        dataSourceId = ds["dataSourceId"],
        ingestionJobId = job["ingestionJobId"]
  )
    job = get_job_response["ingestionJob"]
    
    interactive_sleep(30)

kb_id = kb["knowledgeBaseId"]

print("Data Ingestion Job completed....")
print("KB ID  :"+ kb_id)


