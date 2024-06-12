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
        agent_action_group_id = on_create(event,agent_id,function_arn,bucket_name,object_name)
        actionGroupId = "ActionGroupId"
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': agent_action_group_id+"/"+agent_id,
            'Data': {
                actionGroupId: agent_action_group_id
                }
            }
    elif request_type == 'Update': 
        return on_update(event)
    elif request_type == 'Delete':
        return on_delete(event,bucket_name,object_name,function_arn)
    else:
        logger.error(f"Unsupported request type: {request_type}")
        return {'PhysicalResourceId': 'ERROR'}

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
        agent_action_group_id = action_group['agentActionGroup']['actionGroupId']
        return agent_action_group_id
    except ClientError as e:
        logger.error(f"Couldn't create agent action group. Here's why: {e}")
        raise
        

def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    old_props = event.get("OldResourceProperties", {})

    try:
        # Extract the agent action group ID and agent details from the physical resource ID
        agent_action_group_id, agent_id = physical_id.split("/")

        # Check if any properties have changed
        if props != old_props:
            # Update the agent action group properties
            action_group_name = props.get("ActionGroupName", old_props.get("ActionGroupName"))
            description = props.get("Description", old_props.get("Description"))
            action_group_state = props.get("ActionGroupState", old_props.get("ActionGroupState"))
            action_group_executor = props.get("ActionGroupExecutor", old_props.get("ActionGroupExecutor"))
            api_schema = props.get("ApiSchema", old_props.get("ApiSchema"))

            print(f"Updating agent action group with ID: {agent_action_group_id}")
            bedrock_agent_client.update_agent_action_group(
                actionGroupId=agent_action_group_id,
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=action_group_name,
                description=description,
                actionGroupState=action_group_state,
                actionGroupExecutor=action_group_executor,
                apiSchema=api_schema
            )

            print(f"Agent action group with ID {agent_action_group_id} has been updated.")
        else:
            print(f"No changes detected for agent action group with ID {agent_action_group_id}. Skipping update.")

    except Exception as e:
        logger.error(f"Error updating agent action group: {e}")
        raise

    return {
        'PhysicalResourceId': physical_id
    }

def on_delete(event,bucket_name,object_name,function_arn):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    print(f"cannot delete agent action group resource with PhysicalResourceId: {physical_id} and props: {props}")

    # We have to update the agent action group status to DISBALED before deleting.
    # deleting agent will delete agent action group also
    return {
        "PhysicalResourceId": physical_id
    }