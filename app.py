#!/usr/bin/env python3
import os
#import yaml

import aws_cdk as cdk

from email_automation.email_automation_stack import WorkmailOrgUserStack
from email_automation.email_automation_workflow_stack import EmailAutomationWorkflowStack
from email_automation.bedrock_agent_creation_stack import BedrockAgentCreation


app = cdk.App()
WorkmailOrgUserStack(app, "WorkmailOrgUserStack",)
BedrockAgentCreation(app, "BedrockAgentCreation",)
EmailAutomationWorkflowStack(app, "EmailAutomationWorkflowStack",)
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    
app.synth()
