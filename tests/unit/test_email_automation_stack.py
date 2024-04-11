import aws_cdk as core
import aws_cdk.assertions as assertions

from email_automation.email_automation_stack import EmailAutomationStack

# example tests. To run these tests, uncomment this file along with the example
# resource in email_automation/email_automation_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = EmailAutomationStack(app, "email-automation")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
