# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import logging
import os
import json 
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_agent = boto3.client('bedrock-agent')
bedrock_agent_client = boto3.client('bedrock-agent-runtime')
sns_client = boto3.resource('sns')
ses_client = boto3.client('ses')


human_workflow_topic_arn = os.getenv("HUMAN_WORKFLOW_SNS_TOPIC_ARN")
source_email = os.getenv("SOURCE_EMAIL")
agent_id = os.getenv("AGENT_ID")
agent_alias_id = os.getenv("AGENT_ALIAS_ID")

   
if not human_workflow_topic_arn:
   raise ValueError("env variable HUMAN_WORKFLOW_SNS_TOPIC is required.")  
   
if not source_email:
   raise ValueError("env variable SOURCE_EMAIL is required.") 

if not agent_id:
   raise ValueError("env variable agent_id is required.")
   
if not agent_alias_id:
   raise ValueError("env variable SOURCE_EMAIL is required.")
   
human_workflow_topic = sns_client.Topic(human_workflow_topic_arn)

def invoke_agent(agent_id, agent_alias_id, prompt):
    
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
            sessionId="XYZ12345YZW",
            inputText=prompt,
        )

        completion = ""

        for event in response.get("completion"):
            chunk = event["chunk"]
            completion = completion + chunk["bytes"].decode()

    except ClientError as e:
        logger.error(f"Couldn't invoke agent. {e}")
        raise

    return completion
   
 
   
def send_user_email(completion_email,user_email,email_subject,email_body,source_email):
   logger.info("Sending email to the user : [{}]".format(user_email))
   logger.info("This is the response content : [{}]".format(completion_email))
   try:
      response = ses_client.send_email(
      Destination={
        'ToAddresses': [user_email
        ]
      },
      Message={
        'Body': {
            'Text': {
                'Charset': 'UTF-8',
                'Data': completion_email,
            },
        },
        'Subject': {
            'Charset': 'UTF-8',
            'Data': email_subject,
        },
      },
      Source=source_email)
      
      logger.info("Sent the email. Response is [{}]".format(response))
   except ClientError as e:
        logger.error(f"Couldn't invoke agent. {e}")
        send_to_human_workflow_topic(email_body)
        raise
      

def send_to_human_workflow_topic(email):
   
   human_workflow_topic.publish(
      Message = json.dumps(email)  ,
      Subject = "Human workflow entry found"
   )
   
def validate_params(event,agent_id,agent_alias_id,source_email):
   
   email = event['email']
   meta = event['meta']
   
   if not email :
      raise ValueError("No email found to classify.")
   if not meta :
      raise ValueError("No metadata found.")
   
   email_body = email['body']
   email_subject = email['subject']
   user_email = email['to']
   message_source = meta['source']
   message_id = meta['id']
   
   
   if not email_body:
      raise ValueError("No email body found to classify.")
   if not email_subject:
      raise ValueError("No email subject found.")
   if not user_email:
      raise ValueError("No user email found.")
   if not message_source:
      raise ValueError("No email source found.")
   if not message_id:
      raise ValueError("No email source id found.")
   
   completion_email = invoke_agent(agent_id,agent_alias_id,email_body)
   
   print(completion_email)
   
   send_user_email(completion_email,user_email,email_subject,email_body,source_email)
      
   return email, meta

def lambda_handler(event, context):
 
   email, meta = validate_params(event,agent_id,agent_alias_id,source_email)
   
   logger.info("Executing the email classification lambda function with email content {}".format(email['body']))