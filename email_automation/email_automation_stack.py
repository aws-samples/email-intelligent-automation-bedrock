from aws_cdk import (
    Stack,
    aws_iam as iam,
    CustomResource,
    custom_resources as cr,
    aws_cloudformation as cloudformation,
    aws_logs as logs,
    aws_lambda as lambda_,
    Duration
)
from constructs import Construct
from aws_cdk.custom_resources import Provider
import aws_cdk as cdk
import random
import string

class WorkmailOrgUserStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        prefix = 'my-sample-workmail-org'
        length = 8
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        org_name = f"{prefix}-{random_suffix}"
        #org_name_hash = hashlib.sha256(org_name.encode()).hexdigest():8

        orgname_param = cdk.CfnParameter(
        self,
        f"OrganizationName-{org_name}",
        default=org_name
        )

        username_param = cdk.CfnParameter(self, "UserName",
                #type="String",
                default='support'
                )
        pass_param = cdk.CfnParameter(self, "PassWord",
                #type="String",
                default='Welcome@123'
                )
        create_workmail_org_lambda = lambda_.Function(self, "id_WorkMailOrg",
                                                      runtime=lambda_.Runtime.PYTHON_3_9,
                                                      function_name='workmail_org_creation',
                                                      code=lambda_.Code.from_asset(
                                                          "lambda/workmail-org-user-domain-lambda"),
                                                      handler="workmailcreateorg.handler",
                                                      timeout=Duration.minutes(3),
                                                      environment= {'work_org_name': orgname_param.value_as_string,
                                                                    'user_name': username_param.value_as_string,
                                                                    'password': pass_param.value_as_string}
                                                      )
                                                     
        
                
        create_workmail_org_lambda.role.attach_inline_policy(
            iam.Policy(
                self, "id_workmail_custom_resource_lambda_policy",
                policy_name = "workmail_custom_resource_lambda_policy",
                statements = [
                    iam.PolicyStatement(
                        actions = [
                            "workmail:CreateOrganization",
                            "workmail:CreateDomain",
                            "workmail:CreateUser",
                            "workmail:DescribeOrganization",
                            "workmail:DescribeResource",
                            "workmail:ListDomains",
                            "workmail:ListUsers",
                            "workmail:DeleteUser",
                            "workmail:DeleteDomain",
                            "workmail:DeleteOrganization",
                            "workmail:RegisterToWorkMail",
                            "workmail:DeregisterFromWorkMail",
                            "workmail:DeregisterMailDomain",
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "ds:*",
                            "ses:*",
                            
                        ],
                        resources= [ '*' ],
                    )
                ]
            )
        )

        #create_workmail_org = Construct.Provider(self, "id_workmail_org",
        create_workmail_org = Provider(self, "id_workmail_org",
                                      on_event_handler=create_workmail_org_lambda,
                                      #is_complete_handler=is_complete_org,  # optional async "waiter"
                                      log_retention=logs.RetentionDays.ONE_DAY#,  # default is INFINITE
                                      #role=my_role
                                      )
      

        CustomResource(self, id="id_Work_Mail_Org_Resource",
                        service_token=create_workmail_org.service_token)
                        
        
        cdk.CfnOutput(
            self, "ResponseMessage",
            description="Your support email address is",
            value=username_param.value_as_string+'@'+orgname_param.value_as_string+'.awsapps.com'                                                                                              
        )
