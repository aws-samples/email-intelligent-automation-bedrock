import boto3
import logging
import time
from botocore.exceptions import ClientError
logger = logging.getLogger()
bedrock_agent_client = boto3.client('bedrock-agent-runtime')
bedrock_client = boto3.client('bedrock-agent')



def get_version(agent_id):
    try:
        agent_alias_name = "email_auto_agent_alias-new3"
        agent_version1='1'

        response1 = bedrock_client.list_agent_versions(
        agentId=agent_id
        )
    except ClientError as e:
        logger.error(f"Couldn't invoke agent. {e}")
        raise
    return response1


def invoke_agent(agent_id, agent_alias_id, session_id, prompt):
    
    """
    Sends a prompt for the agent to process and respond to.

    :param agent_id: The unique identifier of the agent to use.
    :param agent_alias_id: The alias of the agent to use.
    :param session_id: The unique identifier of the session. Use the same value across requests
                       to continue the same conversation.
    :param prompt: The prompt that you want Claude to complete.
    :return: Inference response from the model.
"""
    
    try:
        # Note: The execution time depends on the foundation model, complexity of the agent,
        # and the length of the prompt. In some cases, it can take up to a minute or more to
        # generate a response.
        response = bedrock_agent_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=prompt,
        )

        completion = ""

        for event in response.get("completion"):
            chunk = event["chunk"]
            completion = completion + chunk["bytes"].decode()
        
        print(completion)

    except ClientError as e:
        logger.error(f"Couldn't invoke agent. {e}")
        raise

    return completion
    
prompt = "What is the status of this tranfer id MTN7714540"
#prompt = "Would like to reset the password"
output = invoke_agent('VUXJKVN98Y', '41IBNH4BK5', '123xyz123435', prompt)

output1 = get_version('VUXJKVN98Y')

#print(output)
#print(output1)



