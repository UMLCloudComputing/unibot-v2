import aws_cdk as core
import aws_cdk.assertions as assertions

from comp4600_final.comp4600_final_stack import Comp4600FinalStack

# example tests. To run these tests, uncomment this file along with the example
# resource in comp4600_final/comp4600_final_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Comp4600FinalStack(app, "comp4600-final")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
