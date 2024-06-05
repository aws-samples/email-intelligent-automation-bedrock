from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_lambda as lambda_,
    CustomResource,
    aws_iam as iam,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    Duration,
    aws_lambda_event_sources as event_sources,
)
    

from constructs import Construct
from aws_cdk.custom_resources import Provider
import aws_cdk as cdk
import os.path as path
import json
import random
import string
import yaml
import time
random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
random_role_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

class BedrockAgentCreation(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        agent_name_param = cdk.CfnParameter(self, "AgentName",
                #type="String",
                default='my-email-bedrock-agent'
                )
        agent_model_param = cdk.CfnParameter(self, "ModelName",
                #type="String",
                default='anthropic.claude-3-sonnet-20240229-v1:0' # enter the default model
                )
        
        create_bedrock_agent_lambda = lambda_.Function(self, "id_bedrock_agent",
                                                      runtime=lambda_.Runtime.PYTHON_3_11,
                                                      function_name='bedrock_agent_creation',
                                                      code=lambda_.Code.from_asset(
                                                          "lambda/create-bedrock-agent-lambda"),
                                                      handler="bedrock_agent_creation_lambda.handler",
                                                      #layers=[yaml_layer],
                                                      timeout = Duration.minutes(2),
                                                      environment= {'agent_name': agent_name_param.value_as_string,
                                                                    'model_name': agent_model_param.value_as_string
                                                      }
                                                      )
                                                     
        
                
        create_bedrock_agent_lambda.role.attach_inline_policy(
            iam.Policy(
                self, "id_bedrock_agent_creation_lambda_policy",
                policy_name = "bedrock_agent_custom_resource_policy",
                statements = [
                    iam.PolicyStatement(
                        actions = [
                            "bedrock:*",
                            "iam:*",
                            "s3:*",
                            "lambda:*",
                            "dynamodb:*"
                        ],
                        resources= [ '*' ],
                    )
                ]
            )
        )
        
        create_bedrock_agent = Provider(self, "id_create_agent",
                                      on_event_handler=create_bedrock_agent_lambda,
                                      #is_complete_handler=is_complete_agent,  # optional async "waiter"
                                      log_retention=logs.RetentionDays.ONE_DAY#,  # default is INFINITE
                                      #role=my_role
                                      )
        custom_resource_agent= CustomResource(self, id="id_Bedrock_Agent_Resource",
                       service_token=create_bedrock_agent.service_token)
        
        custom_resource_agent_arn = custom_resource_agent.get_att("AgentARN").to_string()
        custom_resource_agent_id = custom_resource_agent.get_att("AgentId").to_string()
        print("agent arn  :" + str(custom_resource_agent_arn))
        print("agent id   :" + str(custom_resource_agent_id))
        
        # Create the S3 bucket
        print("Creating S3 bucket and uploading the data")
        bucket_name = f'bedrock-agent-demo-bucket-{random_string}'
        bucket = s3.Bucket(self,
            "MyBucket",
            bucket_name=bucket_name,  # Replace with your desired bucket name
            removal_policy=RemovalPolicy.DESTROY,  # Delete the bucket when the stack is deleted
            auto_delete_objects=True, #delete the objects when delete the bucket
        )
        
        # Upload data to the S3 bucket
        s3deploy.BucketDeployment(self,
            "DeployData",
            sources=[s3deploy.Source.asset("./email_automation/scenario_resources/openapi")],  # Replace with the path to your local folder
            destination_bucket=bucket,
            destination_key_prefix="openapi/",  # Optional prefix for the uploaded files
        )
        
        # Create Bedrock Execution Role for Lambda
        role_name = f"AmazonBedrockExecutionRoleForLambda_{random_role_string}"
        # Define the Lambda function role
        lambda_role = iam.Role(self,
            "SampleLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=role_name,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                #iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonDynamoDBReadOnlyAccess")
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBReadOnlyAccess")
            ],
        )
        
        
        print(f"Created role {role_name}")
        print("Waiting for the execution role to be fully propagated...")
        time.sleep(10)
        
        # Lambda function for agent action
        print("Creating the Lambda function...")
        function_name = f"AmazonBedrockAgentAction_{random_role_string}"
        action_lambda = lambda_.Function(self,
                function_name,
                code=lambda_.Code.from_asset("./email_automation/scenario_resources"),
                handler="lambda_function.lambda_handler",  # Name of the Lambda function handler
                runtime=lambda_.Runtime.PYTHON_3_9,
                role=lambda_role,
                timeout=Duration.seconds(30),
            )
        
        
        
        create_agent_action_lambda = lambda_.Function(self, "id_bedrock_agent_action",
                                                      runtime=lambda_.Runtime.PYTHON_3_9,
                                                      function_name='bedrock_agent_action_creation',
                                                      code=lambda_.Code.from_asset(
                                                          "lambda/create-bedrock-agent-action-lambda"),
                                                      handler="bedrock_agent_action_lambda.handler",
                                                      #layers=[yaml_layer],
                                                      timeout = Duration.minutes(2),
                                                      environment= {'agent_id': custom_resource_agent_id,
                                                                    #'agent_version': custom_resource_agent_version,
                                                                    'function_arn': action_lambda.function_arn,
                                                                    'bucket_name': bucket_name,
                                                                    'object_name': 'openapi/api_schema.yaml'
                                                      }
                                                      )
                                                     
        
        create_agent_action_lambda.role.attach_inline_policy(
            iam.Policy(
                self, "id_bedrock_agent_action_lambda_policy",
                policy_name = "bedrock_agent_action_custom_resource_policy",
                statements = [
                    iam.PolicyStatement(
                        actions = [
                            "bedrock:*",
                            "iam:*",
                            "s3:*",
                            "lambda:*",
                            "dynamodb:*"
                        ],
                        resources= [ '*' ],
                    )
                ]
            )
        )
        
        # Create the dependency between the custom resource and the dependent resource
        create_agent_action_lambda.node.add_dependency(custom_resource_agent)
        
        create_bedrock_agent_action_group = Provider(self, "id_create_agent_action",
                                      on_event_handler=create_agent_action_lambda,
                                      #is_complete_handler=is_complete_action_agent,  # optional async "waiter"
                                      log_retention=logs.RetentionDays.ONE_DAY#,  # default is INFINITE
                                      #role=my_role
                                      )
        
                       
        custom_resource_agent_action= CustomResource(self, id="id_Bedrock_Agent_Action_Resource",
                       service_token=create_bedrock_agent_action_group.service_token)
        
        custom_resource_agent_action_id = custom_resource_agent_action.get_att("AgentActionId").to_string()
        
        print ("agent_action_id is: " + str(custom_resource_agent_action_id))
        
        
        # Define table properties
        table_name = "moneyTransferStatus"
        partition_key = dynamodb.Attribute(name="transferID", type=dynamodb.AttributeType.STRING)
        sort_key = dynamodb.Attribute(name="transferStatus", type=dynamodb.AttributeType.STRING)

        # Create the DynamoDB table
        table = dynamodb.Table(
            self,
            "MoneyTransferStatusTable",
            table_name=table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Define the Lambda function role for DynamoDB
        role_name_ddb = f"DDBLambdaRole_{random_role_string}"
        lambda_ddb_role = iam.Role(
            self,
            "LambdaDDBRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=role_name_ddb,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"),
            ],
        )
        
        # Define the Lambda function to upload data to DynamoDB
        upload_data_lambda = lambda_.Function(self,
            "UploadDataLambdatoBynamoDB",
            code=lambda_.Code.from_asset("./email_automation/scenario_resources/ddb_data_upload"),
            handler="add_data_ddb_table.lambda_handler",  # Replace with the name of your Lambda function handler
            runtime=lambda_.Runtime.PYTHON_3_9,
            role=lambda_ddb_role,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name,
            },
        )
        
        #dynamodb_access_policy.add_account_resource_principal(account=self.account)
        
        # Grant the Lambda function permissions to upload data to the DynamoDB table
        table.grant_read_write_data(upload_data_lambda)

        # Accepting invocation from bedrock agent to Lambda
        bedrock_principal = iam.ServicePrincipal("bedrock.amazonaws.com")
        action_lambda.add_permission(
            "AllowBedrockInvoke",
            principal=bedrock_principal,
            action="lambda:InvokeFunction",
            source_arn=custom_resource_agent_arn,  # Replace with your actual Bedrock Agent ARN
        )
        
        # Create Agent Alias. It should be created after Agent action is created
        create_agent_alias_lambda = lambda_.Function(self, "id_bedrock_agent_alias",
                                                      runtime=lambda_.Runtime.PYTHON_3_9,
                                                      function_name='bedrock_agent_alias_creation',
                                                      code=lambda_.Code.from_asset(
                                                          "lambda/create-bedrock-agent-alias-lambda"),
                                                      handler="bedrock_agent_alias_lambda.handler",
                                                      #layers=[yaml_layer],
                                                      timeout = Duration.minutes(2),
                                                      environment= {'agent_id': custom_resource_agent_id}
                                                      )
                                                     
        
        create_agent_alias_lambda.role.attach_inline_policy(
            iam.Policy(
                self, "id_bedrock_agent_alias_lambda_policy",
                policy_name = "bedrock_agent_alias_custom_resource_policy",
                statements = [
                    iam.PolicyStatement(
                        actions = [
                            "bedrock:*"
                        ],
                        resources= [ '*' ],
                    )
                ]
            )
        )
        
        # Create the dependency between the custom resource and the dependent resource
        create_agent_alias_lambda.node.add_dependency(custom_resource_agent_action)
        
        create_bedrock_agent_alias = Provider(self, "id_create_agent_alias",
                                      on_event_handler=create_agent_alias_lambda,
                                      #is_complete_handler=is_complete_action_agent,  # optional async "waiter"
                                      log_retention=logs.RetentionDays.ONE_DAY#,  # default is INFINITE
                                      #role=my_role
                                      )
        
                       
        custom_resource_alias= CustomResource(self, id="id_Bedrock_Agent_Alias_Resource",
                       service_token=create_bedrock_agent_alias.service_token)
        
        custom_resource_agent_alias_id = custom_resource_alias.get_att("AgentAlias").to_string()
        custom_resource_agent_version_id = custom_resource_alias.get_att("AgentVersion").to_string()

        
        print ("agent_action_id is: " + str(custom_resource_agent_action_id))
        
        
        #######
        
        cdk.CfnOutput(
            self, "ResponseMessageBucket",
            description="Your Bucket is",
            value="Your bucket info is:  "+ bucket.bucket_arn,
            export_name="MyBucketArnExport"
        )
        cdk.CfnOutput(
            self, "ResponseMessageActionLambda",
            description="Your Function ARN is",
            value="Your Lambda ARN is:  "+ action_lambda.function_arn
            #export_name="MyLambdaArnExport"
        )
        
        cdk.CfnOutput(
            self, "ResponseMessageAgent",
            description="Your Agent Name is",
            value="Your agent name is:  "+ agent_name_param.value_as_string                                                                                              
        )
        
        cdk.CfnOutput(
            self, "CustomResourceAgentArn",
            value=custom_resource_agent_arn,#custom_output,#custom_resource_agent['Data']['ARN'],
            description="ARN of the Agent resource"
        )
        
        cdk.CfnOutput(
            self, "CustomResourceAgentActionId",
            value=custom_resource_agent_action_id,#custom_output,#custom_resource_agent['Data']['ARN'],
            description="Id of the Agent Action Groupresource"
        )
         # Output the table name
        cdk.CfnOutput(self, "TableName", value=table.table_name)
        
        cdk.CfnOutput(
            self, "CustomResourceAgentAliasId",
            value=custom_resource_agent_alias_id,#custom_output,#custom_resource_agent['Data']['ARN'],
            description="Id of the Agent Alias Groupresource"
        )
        
        cdk.CfnOutput(
            self, "CustomResourceAgentVersionoftheAlias",
            value=custom_resource_agent_version_id,#custom_output,#custom_resource_agent['Data']['ARN'],
            description="Id of the Version of Agent Alias Groupresource"
        )
        