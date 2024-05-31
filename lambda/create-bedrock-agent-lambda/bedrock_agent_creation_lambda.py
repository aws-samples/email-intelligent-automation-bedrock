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
REGION = "us-east-1"
ROLE_POLICY_NAME = "agent_permissions"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.resource('s3', region_name=REGION)
bedrock_agent_client = boto3.client('bedrock-agent')
iam_resource=boto3.resource("iam")
random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
random_role_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
logger = logging.getLogger(__name__)

def handler(event, context):
    print(event)
    agent_name = os.environ['agent_name']
    model_name = os.environ['model_name']
    request_type = event['RequestType']
    if request_type == 'Create': 
        agent_arn,agent_id = on_create(event,agent_name,model_name)
        print("agentarn..= "+str(agent_arn)+"agentid= "+str(agent_id))
        arn_name = "AgentARN"
        agentId = "AgentId"
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': agent_arn,
            'Data': {
                arn_name: agent_arn,
                agentId: agent_id
                }
            }
    elif request_type == 'Update': 
        return on_update(event)
    elif request_type == 'Delete':
        physical_id = event["PhysicalResourceId"]
        return {'PhysicalResourceId': physical_id}
    else:
        logger.error(f"Unsupported request type: {request_type}")
        return {'PhysicalResourceId': 'Hello_ERROR'}

def on_create(event,agent_name,model_name):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)
    role_name = f"AmazonBedrockExecutionRoleForAgents_{random_role_string}"
    model_arn = f"arn:aws:bedrock:{REGION}::foundation-model/{model_name}*"
    agent_role_arn = create_agent_role(role_name,model_name,model_arn)
    agent_arn,agent_id = create_agent(agent_name,model_name,agent_role_arn)
    print("agentarn= "+str(agent_arn)+"agentid= "+str(agent_id))
    return agent_arn,agent_id
    
def create_agent_role(role_name,model_name,model_arn):# call bedrock agent creation api
    # Create agent role
    try:
        print("Creating an an execution role for the agent...")
        #role_name = "AmazonBedrockExecutionRoleForAgents_"
        agent_role = iam_resource.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "bedrock.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )

        agent_role.Policy(ROLE_POLICY_NAME).put(
            PolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "bedrock:InvokeModel",
                            "Resource": model_arn,
                        },
                        {
                            "Sid": "AllowAgentAccessOpenAPISchema",
                            "Effect": "Allow",
                            "Action": [
                                        "s3:*",
                                        "s3-object-lambda:*"
                                        ],
                            "Resource": "*"
                        },
                        {
                            "Sid": "AllowAgenttoInvokeLambda",
                            "Effect": "Allow",
                            "Action": [
                                        "lambda:*"
                                        ],
                            "Resource": "*"
                        }
                    ],
                }
            )
        )
        
        return agent_role.arn
       
    except ClientError as e:
        logger.error(f"Couldn't create role {role_name}. Here's why: {e}")
        raise
    #return agent_role.arn

def create_agent(agent_name,model_name,agent_role_arn):
    try:
        print("Creating the agent...")

        instruction = """
            You are an classification and entity recognition agent. 
            1. First you have to classify the text given to you based on the categories in ["Transfer Status","Password Reset","Promo Code"] and return just category without additional text.
            2. Next, if the classified category is "Transfer Status", find the 10 digits entity money_transfer_id(example: "MTN1234567") and call the "GetTransferStatus" action to get the status by using the money_transfer_id
            3. Then, write a email reply for the customer based on the text you received, classification of the text and transfer status with money_transfer_id
            4. If you are not able to classify with in the categories given, call the "send message to SNS" action to push the message SNS topic
            """
        agent_response = bedrock_agent_client.create_agent(
            agentName=agent_name,
            foundationModel=model_name,
            instruction=instruction,
            agentResourceRoleArn=agent_role_arn#agent_role.arn # to be updated
        )
        time.sleep(10)
        
        prepared_agent_details = bedrock_agent_client.prepare_agent(agentId=agent_response['agent']['agentId'])
       
        _wait_for_agent_status(agent_response['agent']['agentId'], "PREPARED")
        print (agent_response)
        #agent_version = create_agent_alias(agent_response['agent']['agentId'])
        #print ("printing agent version1 " + agent_version)
        agent_arn = agent_response['agent']['agentArn']
        agent_id = agent_response['agent']['agentId']
        #agent_version = agent_response['agent']['agentVersion']
        return agent_arn,agent_id
        
    except ClientError as q:
        print("Error while creating the agent: %s" % q)
    
        
def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    print("Nothing to do as an update event : update resource %s with props %s" %
        (physical_id, props))
    response = {
      'PhysicalResourceId': physical_id
    }
    return response

def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    print("Nothing to do as an update event : Delete resource %s with props %s" %
        (physical_id, props))
    response = {
      'PhysicalResourceId': physical_id
    }
    return response
        

def _wait_for_agent_status(agent_id, status):
    while bedrock_agent_client.get_agent(agentId=agent_id)['agent']['agentStatus'] != status:
        time.sleep(2)