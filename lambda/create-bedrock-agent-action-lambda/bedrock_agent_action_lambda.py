import boto3
import os
import json 
import asyncio
import io
import logging
import random
import time
import string
import uuid
import zipfile
from botocore.exceptions import ClientError
bedrock_agent_client = boto3.client('bedrock-agent')
logger = logging.getLogger(__name__)

def handler(event, context):
    print(event)
    agent_id = os.environ['agent_id']
    #agent_version = os.environ['agent_version']
    function_arn = os.environ['function_arn']
    bucket_name = os.environ['bucket_name']
    object_name = os.environ['object_name']
    request_type = event['RequestType']
    print("agent_fun_arn" + function_arn)
    print("bucket_name" + bucket_name)
    print("object_name" + object_name)
    if request_type == 'Create': 
        agent_action_id = on_create(event,agent_id,function_arn,bucket_name,object_name)
        agentActionId = "AgentActionId"
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': agent_action_id,
            'Data': {
                agentActionId: agent_action_id
                }
            }
    elif request_type == 'Update': 
        return on_update(event)
    elif request_type == 'Delete':
        return {'PhysicalResourceId': agent_action_id}
    # Return the resource ARN as part of the response
    else:
        logger.error(f"Unsupported request type: {request_type}")
        return {'PhysicalResourceId': 'Hello_ERROR'}

def on_create(event,agent_id,function_arn,bucket_name,object_name):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)
    print("Creating an action group for the agent...")
    
    try:
        action_group = bedrock_agent_client.create_agent_action_group(
            actionGroupName="GetTransferStatus",
            description="Get the status of the money transfer",
            actionGroupState='ENABLED',
            agentId=agent_id,#agent_response['agent']['agentId'],
            agentVersion='DRAFT',#agent_response['agent']['agentVersion'],
            actionGroupExecutor={"lambda": function_arn},#lambda_function["FunctionArn"]},
            apiSchema= {
                        's3': {
                            's3BucketName': bucket_name,
                            's3ObjectKey': object_name
                              }
                        }
#json.dumps(yaml.safe_load(file))
        )
        agent_action_id = action_group['agentActionGroup']['actionGroupId']
        return agent_action_id
    except ClientError as e:
        logger.error(f"Couldn't create agent action group. Here's why: {e}")
        raise
        
def on_update(event):
    props = event["ResourceProperties"]