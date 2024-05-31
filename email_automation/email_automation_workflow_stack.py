from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ses as ses,
    Duration
)
from constructs import Construct
from aws_cdk.custom_resources import Provider
import aws_cdk as cdk
import os.path as path
import json
import string
import random
random_class_func_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
random_integ_func_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

#f'bedrock-agent-demo-bucket-{random_string}'

class EmailAutomationWorkflowStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        agent_id = cdk.CfnParameter(self, "AgentID",
                #type="String"
                ).value_as_string
        
        agent_alias_id = cdk.CfnParameter(self, "AgentAliasID",
                #type="String"
                ).value_as_string

        human_topic = self.human_workflow_topic()

        classification_lambda = self.classify_email_lambda(human_topic,agent_id,agent_alias_id)
        
        workmail_lambda = self.workmail_integration_lambda(classification_lambda)
        
        
        
        #self.register_email_temapltes()
        
    def human_workflow_topic(self):
        
        human_workflow_email = cdk.CfnParameter(self, "humanWorkflowEmail",
                #type="String"
                ).value_as_string
             
        topic =  sns.Topic(
            self, "id_human_workflow_topic",
            display_name="Email-classification-human-workflow-topic",
            topic_name="Email-classification-human-workflow-topic"
        )
        
        topic.add_subscription(subs.EmailSubscription(human_workflow_email))
        
        return topic
    
    def classify_email_lambda(self, human_workflow_topic,agent_id,agent_alias_id):
        support_email = cdk.CfnParameter(self, "supportEmail",
                #type="String"
                ).value_as_string
        
        # Define the inline policy
        inline_policy = iam.PolicyDocument(
            statements=[
            iam.PolicyStatement(
                actions=[
                    "ses:SendTemplatedEmail",
                    "bedrock:InvokeAgent",
                    "ses:SendEmail"
                    ],
                resources=["*"],
                effect=iam.Effect.ALLOW
                        )
                         ]
                        )
        
        # Create the IAM role with the lambda.amazonaws.com service principal
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "InvokeAgentAndSES": inline_policy
                }
            )
                
        email_classify_lambda = lambda_.Function(
            #f'bedrock-agent-demo-bucket-{random_string}'
            self, "id_classify_emails_lambda_fn", 
            function_name=f'classify-emails-lambda-fn-{random_class_func_string}',
            code = lambda_.Code.from_asset(path.join("./lambda", "classify-emails-lambda")),
            handler = "lambda_function.lambda_handler",
            runtime = lambda_.Runtime.PYTHON_3_9,
            role=lambda_role,
            timeout = Duration.minutes(1),
            environment={
                #"EMAIL_ENTITY_RECOGNITION_ENDPOINT_ARN" : email_entity_recognition_endpoint_arn,
                "HUMAN_WORKFLOW_SNS_TOPIC_ARN" : human_workflow_topic.topic_arn,
                "SOURCE_EMAIL" : support_email,
                "AGENT_ID" : agent_id,
                "AGENT_ALIAS_ID" : agent_alias_id
            }
        )
        
        human_workflow_topic.grant_publish(email_classify_lambda)
        
        return email_classify_lambda
    
    def workmail_integration_lambda(self, classification_lambda):
        
        workmail_lambda = lambda_.Function(
            self, "id_workmail_integration_lambda_lambda_fn", 
            function_name=f'workmail-integration-lambda-fn-{random_integ_func_string}',
            #function_name="workmail-integration-lambda-fn",
            code = lambda_.Code.from_asset(path.join("./lambda", "workmail-integration-lambda")),
            handler = "lambda_function.lambda_handler",
            runtime = lambda_.Runtime.PYTHON_3_9,
            timeout = Duration.minutes(1),
            environment={
                "EMAIL_CLASSIFICATION_LAMBDA_FN_NAME" : classification_lambda.function_name
            }
        )
        
        current_region = self.region
        
        principal = iam.ServicePrincipal("workmail.{}.amazonaws.com".format(current_region))
        
        workmail_lambda.grant_invoke(principal)
        
        workmail_lambda.add_to_role_policy(
            iam.PolicyStatement(
                        actions = [
                            "workmailmessageflow:GetRawMessageContent",
                        ],
                        resources= [ '*' ]
                    )
            
        )
        
        classification_lambda.grant_invoke(workmail_lambda)
        
        return workmail_lambda