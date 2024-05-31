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
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    print(event)
    agent_id = os.environ['agent_id']
    request_type = event['RequestType']
    if request_type == 'Create': 
        agent_alias_id,agent_version = on_create(event,agent_id)
        print("agent alias id = "+str(agent_alias_id)+"agent_version = "+str(agent_version))
        alias_id = "AgentAlias"
        agentVer = "AgentVersion"
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': agent_alias_id,
            'Data': {
                alias_id: agent_alias_id,
                agentVer: agent_version
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

def on_create(event,agent_id):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)
    agent_alias_id, agent_version = create_agent_alias(agent_id)
    print("agent alias id= "+str(agent_alias_id)+"agent_version= "+str(agent_version))
    return agent_alias_id,agent_version
    
def create_agent_alias(agent_id):
    # Create Agent Alias
    print("Creating the agent alias...")
    
    agent_alias_name = "email_auto_agent_alias"
    agent_version='1'

    agent_alias = bedrock_agent_client.create_agent_alias(
        agentAliasName=agent_alias_name, agentId=agent_id#agent_response['agent']['agentId']
    )
    
    agent_alias_id=agent_alias['agentAlias']['agentAliasId']
    
    print (agent_alias)
    
    _wait_for_agent_alias_status(agent_alias['agentAlias']['agentId'],agent_alias['agentAlias']['agentAliasId'],"PREPARED")
    
    for i in agent_alias['agentAlias']['routingConfiguration']:
        if 'agentVersion' in i:
            agent_version = i['agentVersion']
            print ("printing agent version1 ..." + agent_version)
        else:
            agent_version = '1'
            print ("printing agent version1 in for loop ..." + agent_version)
    return agent_alias_id, agent_version
    
        
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
        

def _wait_for_agent_alias_status(agent_id,agent_alias_id,status):
    while bedrock_agent_client.get_agent_alias(agentId=agent_id,agentAliasId=agent_alias_id)['agentAlias']['agentAliasStatus'] != status:
        time.sleep(2)