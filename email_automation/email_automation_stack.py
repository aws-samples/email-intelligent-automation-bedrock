from aws_cdk import (
    Stack,
    aws_iam as iam,
    CustomResource,
    aws_logs as logs,
    aws_lambda as lambda_
)
from constructs import Construct
from aws_cdk.custom_resources import Provider
import aws_cdk as cdk

class WorkmailOrgUserStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        orgname_param = cdk.CfnParameter(self, "OrganizationName",
                #type="String",
                default='my-sample-workmail-org'
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
                            "ds:*",
                            "ses:*",
                            
                        ],
                        resources= [ '*' ],
                    )
                ]
            )
        )


        is_complete_org = lambda_.Function(
                                            self, "id_workmail_org_is_complete",
                                            function_name="resource-is-complete-lambda",
                                            code=lambda_.Code.from_asset(
                                               "lambda/workmail-org-user-domain-lambda"),
                                            handler="workmailcreateorg.is_complete",
                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                            environment= {'work_org_name':orgname_param.value_as_string,
                                                            'user_name': username_param.value_as_string,
                                                                'password': pass_param.value_as_string}
                                                                    )

        is_complete_org.role.attach_inline_policy(
            iam.Policy(
                self, "id_is_complete_custom_resource_lambda_policy",
                policy_name = "is_complete_custom_resource_lambda_policy",
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
                                      is_complete_handler=is_complete_org,  # optional async "waiter"
                                      log_retention=logs.RetentionDays.ONE_DAY#,  # default is INFINITE
                                      #role=my_role
                                      )
        

        CustomResource(self, id="id_Work_Mail_Org_Resource",
                       service_token=create_workmail_org.service_token)
        
        cdk.CfnOutput(
            self, "ResponseMessage",
            description="Your support email address is",
            value="Your support email address is:  "+ username_param.value_as_string+'@'+orgname_param.value_as_string+'.awsapps.com'                                                                                              
        )
        

    # The code that defines your stack goes here

    # example resource
    # queue = sqs.Queue(
    #     self, "EmailAutomationQueue",
    #     visibility_timeout=Duration.seconds(300),
    # )
