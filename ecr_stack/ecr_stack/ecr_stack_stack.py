from aws_cdk import (
    # Duration,
    Stack,
    aws_ecr as ecr,
    aws_s3 as s3,
    # aws_s3_notifications as s3_trigger,
    aws_lambda as _lambda,
    aws_iam as iam,
    RemovalPolicy,
    # aws_sqs as sqs,
    aws_ec2 as ec2
)
from constructs import Construct
import os

RESOURCE_PREFIX = "gcp-ecr-stack-"

class EcrStackStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        

        repo = ecr.Repository(
            self,
            "OCI-Repository",
            repository_name= RESOURCE_PREFIX + "repository",
            removal_policy=RemovalPolicy.DESTROY,
            
        )

        # S3 bucket
        # This will store raw HTML files that are to be vectorized
        # Will trigger a lambda to vectorize them
        html_data_bucket = s3.Bucket(
            self,
            "html_data_bucket",
            bucket_name= RESOURCE_PREFIX + "html-data-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        
        # Data download IAM stuff
        data_download_function_policy_doc = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["s3:GetObject", "s3:PutObject"],
                    resources=[html_data_bucket.bucket_arn],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        data_download_function_role = iam.Role(
            self,
            "RAG-Processing-Function-Exec-Role",
            role_name= RESOURCE_PREFIX + "rag-processing-func-exec-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "Data-Download-Function-Policy": data_download_function_policy_doc
            }
        )
        
        # Data Downloading Lambda
        data_download_lambda = _lambda.Function(
            self,
            "Data-Downloading-Function",
            function_name= RESOURCE_PREFIX + "data-downloading-function",
            runtime= _lambda.Runtime.PYTHON_3_11,
            handler="download_data-s3.handler",
            code=_lambda.Code.from_asset("rag/download-lambda"),
            role=data_download_function_role
        )
        html_data_bucket.grant_read_write(data_download_lambda)

        # Vectorization IAM stuff
        # vectorization_function_policy_doc = iam.PolicyDocument(
        #     statements=[
        #         iam.PolicyStatement(
        #             actions=["s3:GetObject", "ecr:PutImage"],
        #             resources=[html_data_bucket.bucket_arn, repo.repository_arn ],
        #             effect=iam.Effect.ALLOW
        #         )
        #     ]
        # )

        # vectorization_function_role = iam.Role(
        #     self,
        #     "Vectorization-Function-Exec-Role",
        #     role_name= RESOURCE_PREFIX + "vectorization-func-exec-role",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        #     inline_policies={
        #         "Vectorization-Function-Policy": vectorization_function_policy_doc
        #     }
        # )
        # # Vectorization function
        # vectorization_lambda = _lambda.Function(
        #     self,
        #     "Vectorization-Function",
        #     function_name=RESOURCE_PREFIX + "vectorization-function",
        #     runtime=_lambda.Runtime.PYTHON_3_11,
        #     handler="vectorize-push-ecr.handler",
        #     code=_lambda.Code.from_asset("rag/vectorize-lambda"),
        #     environment = {
        #         'BUCKET_NAME': html_data_bucket.bucket_name,
        #         'ECR_REPO_URI': repo.repository_uri
        #     },
        #     role=vectorization_function_role
        # )


        # Vectorization EC2 IAM Role
        vect_ec2_role = iam.Role(
            self,
            "Vectorization-EC2-Role",
            role_name=RESOURCE_PREFIX+"vect-ec2-role",
            assumed_by=iam.ServicePrincipal("ec2.amazon.com"),
            inline_policies={
                "Vectorization-Policy-Doc": 
            }
        )
        # Vectorization EC2 Instance
        ## Ubuntu AMI source: https://cloud-images.ubuntu.com/locator/ec2/
        with open(os.path.join(os.path.dirname(__file__), "./rag/vectorize_lambda.sh"), "r") as file:
            user_data_script = file.read()

        vectorization_ec2 = ec2.Instance(
            self,
            "vectorization_ec2_instance",
            machine_image=ec2.MachineImage.generic_linux({
                "us-east-1": "ami-083f1fc4f8bcff379"
            }),
            role=vect_ec2_role,
            user_data=ec2.UserData.custom(user_data_script)
        )

