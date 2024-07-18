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
        return on_update(event, context)
    elif request_type == 'Delete':
        return on_delete(event, context)
        #physical_id = event["PhysicalResourceId"]
        #return {'PhysicalResourceId': physical_id}
    else:
        logger.error(f"Unsupported request type: {request_type}")
        return {'PhysicalResourceId': 'ERROR'}

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
            You are a classification and entity recognition agent.
            
            Task 1: Classify the given text into one of the following categories: "Transfer Status", "Password Reset", or "Promo Code". Return only the category without any additional text. If the given text is not falling under one of the category, just reply "Thanks for your email and our team is reviewing your request and get back to you in 24 to 48 hours." email signature "Best regards, Intelligent Corp" at the end of the email reply. Task 2: If the classified category is "Transfer Status", find the 10-digit entity "money_transfer_id" (example: "MTN1234567") in the text. Call the "GetTransferStatus" action, passing the money_transfer_id as an argument, to retrieve the transfer status. Task 3: Write an email reply for the customer based on the received text, the classified category, and the transfer status (if applicable). Include the money_transfer_id in the reply if the category is "Transfer Status". Task 4: Use the email signature "Best regards, Intelligent Corp" at the end of the email reply.
            
            Task 2: If the classified category is "Transfer Status", find the 10-digit entity "money_transfer_id" (example: "MTN1234567") in the text. Call the "GetTransferStatus" action, passing the money_transfer_id as an argument, to retrieve the transfer status.
            
            Task 3: Write an email reply for the customer based on the received text, the classified category, and the transfer status (if applicable). Include the money_transfer_id in the reply if the category is "Transfer Status".
            
            Task 4: Use the email signature "Best regards, Intelligent Corp" at the end of the email reply.
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
        agent_status = bedrock_agent_client.get_agent(agentId=agent_response['agent']['agentId'])['agent']['agentStatus']
        print ("agent status" + agent_status)
        #agent_version = create_agent_alias(agent_response['agent']['agentId'])
        #print ("printing agent version1 " + agent_version)
        agent_arn = agent_response['agent']['agentArn']
        agent_id = agent_response['agent']['agentId']
        #agent_version = agent_response['agent']['agentVersion']
        return agent_arn,agent_id
        
    except ClientError as q:
        print("Error while creating the agent: %s" % q)
    
def on_update(event, context):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    old_props = event.get("OldResourceProperties", {})

    try:
        # Extract the agent ID from the physical resource ID
        agent_id = physical_id.split("/")[-1]

        # Check if any properties have changed
        if props != old_props:
            # Update the agent properties
            agent_name = props.get("AgentName", old_props.get("AgentName"))
            model_name = props.get("ModelName", old_props.get("ModelName"))
            instruction = props.get("Instruction", old_props.get("Instruction"))
            agent_role_arn = props.get("AgentRoleArn", old_props.get("AgentRoleArn"))

            print(f"Updating agent with ID: {agent_id}")
            bedrock_agent_client.update_agent(
                agentId=agent_id,
                agentName=agent_name,
                foundationModel=model_name,
                instruction=instruction,
                agentResourceRoleArn=agent_role_arn
            )

            # Wait for the agent to be updated
            _wait_for_agent_status(agent_id, "PREPARED")

            print(f"Agent with ID {agent_id} has been updated.")
        else:
            print(f"No changes detected for agent with ID {agent_id}. Skipping update.")

    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise

    return {
        'PhysicalResourceId': physical_id
    }

def on_delete(event, context):
    physical_id = event["PhysicalResourceId"]
    try:
        # Extract the agent ID from the physical resource ID
        agent_id = physical_id.split("/")[-1]
        
        # Delete the agent
        print(f"Deleting agent with ID: {agent_id}")
        bedrock_agent_client.delete_agent(agentId=agent_id)
        
        # Wait for the agent to be deleted
        while True:
            try:
                agent_details = bedrock_agent_client.get_agent(agentId=agent_id)
                if agent_details["agent"]["agentStatus"] == "DELETED":
                    break
            except bedrock_agent_client.exceptions.ResourceNotFoundException:
                break
            time.sleep(5)
        
        print(f"Agent with ID {agent_id} has been deleted.")
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise
    
    return {
        'PhysicalResourceId': physical_id
    }
        

def _wait_for_agent_status(agent_id, status):
    while bedrock_agent_client.get_agent(agentId=agent_id)['agent']['agentStatus'] != status:
        time.sleep(2)