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
        agent_alias_id,agent_version,agent_id = on_create(event,agent_id)
        print("agent alias id = "+str(agent_alias_id)+"agent_version = "+str(agent_version))
        alias_id = "AgentAlias"
        agentVer = "AgentVersion"
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': agent_id+"/"+agent_alias_id,
            'Data': {
                alias_id: agent_alias_id,
                agentVer: agent_version
                }
            }
    elif request_type == 'Update': 
        return on_update(event)
    elif request_type == 'Delete':
        return on_delete(event)
        #physical_id = event["PhysicalResourceId"]
        #return {'PhysicalResourceId': physical_id}
    else:
        logger.error(f"Unsupported request type: {request_type}")
        return {'PhysicalResourceId': 'ERROR'}

def on_create(event,agent_id):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)
    agent_alias_id, agent_version, agent_id = create_agent_alias(agent_id)
    print("agent alias id= "+str(agent_alias_id)+"agent_version= "+str(agent_version))
    return agent_alias_id,agent_version,agent_id
    
def create_agent_alias(agent_id):
    # Create Agent Alias
    print("Creating the agent alias...")
    
    agent_alias_name = "email_auto_agent_alias"
    agent_version='1'

    agent_alias = bedrock_agent_client.create_agent_alias(
        agentAliasName=agent_alias_name, agentId=agent_id#agent_response['agent']['agentId']
    )
    
    agent_alias_id=agent_alias['agentAlias']['agentAliasId']
    agent_id=agent_alias['agentAlias']['agentId']
    
    print (agent_alias)
    
    _wait_for_agent_alias_status(agent_alias['agentAlias']['agentId'],agent_alias['agentAlias']['agentAliasId'],"PREPARED")
    
    for i in agent_alias['agentAlias']['routingConfiguration']:
        if 'agentVersion' in i:
            agent_version = i['agentVersion']
            print ("printing agent version1 ..." + agent_version)
        else:
            agent_version = '1'
            print ("printing agent version1 in for loop ..." + agent_version)
    return agent_alias_id, agent_version, agent_id
    
        
def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    old_props = event.get("OldResourceProperties", {})

    try:
        # Extract the agent alias ID and agent ID from the physical resource ID
        agent_id,agent_alias_id = physical_id.split("/")

        # Check if any properties have changed
        if props != old_props:
            # Update the agent alias properties
            agent_alias_name = props.get("AgentAliasName", old_props.get("AgentAliasName"))
            description = props.get("Description", old_props.get("Description"))
            routing_configuration = props.get("RoutingConfiguration", old_props.get("RoutingConfiguration"))

            print(f"Updating agent alias with ID: {agent_alias_id}")
            bedrock_agent_client.update_agent_alias(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                agentAliasName=agent_alias_name,
                description=description,
                routingConfiguration=routing_configuration
            )

            print(f"Agent alias with ID {agent_alias_id} has been updated.")
        else:
            print(f"No changes detected for agent alias with ID {agent_alias_id}. Skipping update.")

    except Exception as e:
        logger.error(f"Error updating agent alias: {e}")
        raise

    return {
        'PhysicalResourceId': physical_id
    }

def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    try:
        # Extract the agent alias ID and agent ID from the physical resource ID
        agent_id,agent_alias_id = physical_id.split("/")

        # Delete the agent alias
        print(f"Deleting agent alias with ID: {agent_alias_id}")
        bedrock_agent_client.delete_agent_alias(agentId=agent_id, agentAliasId=agent_alias_id)

        # Wait for the agent alias to be deleted
        while True:
            try:
                alias_details = bedrock_agent_client.get_agent_alias(agentId=agent_id, agentAliasId=agent_alias_id)
                if alias_details["agentAlias"]["agentAliasStatus"] == "DELETED":
                    break
            except bedrock_agent_client.exceptions.ResourceNotFoundException:
                break
            time.sleep(5)

        print(f"Agent alias with ID {agent_alias_id} has been deleted.")
    except Exception as e:
        logger.error(f"Error deleting agent alias: {e}")
        raise

    return {
        'PhysicalResourceId': physical_id
    }

        

def _wait_for_agent_alias_status(agent_id,agent_alias_id,status):
    while bedrock_agent_client.get_agent_alias(agentId=agent_id,agentAliasId=agent_alias_id)['agentAlias']['agentAliasStatus'] != status:
        time.sleep(2)