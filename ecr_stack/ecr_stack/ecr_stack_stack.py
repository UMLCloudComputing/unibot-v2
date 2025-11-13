from aws_cdk import (
    # Duration,
    Stack,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_s3_notifications as s3_trigger,
    aws_lambda as _lambda,
    aws_iam as iam,
    RemovalPolicy
    # aws_sqs as sqs,
)
from constructs import Construct

RESOURCE_PREFIX = "gcp-ecr-stack-"

class EcrStackStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo = ecr.Repository(
            self,
            "OCI-Repository",
            repository_name= RESOURCE_PREFIX + "repository",
            removal_policy=RemovalPolicy.DESTROY
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
                    resources=[html_data_bucket._get_resource_arn_attribute()],
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
            inline_policies=[
                data_download_function_policy_doc
            ]
        )
        
        # Data Downloading Lambda
        data_download_lambda = _lambda.Function(
            self,
            "Data-Downloading-Function",
            function_name= RESOURCE_PREFIX + "data-downloading-function",
            runtime= _lambda.Runtime.PYTHON_3_11,
            handler="download_data-s3.",
            code=_lambda.Code.from_asset("rag/download-lambda"),
            role=data_download_function_role
        )
        html_data_bucket.grant_read_write(data_download_lambda)

        # Vectorization IAM stuff
        vectorization_function_policy_doc = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["s3:GetObject", "ecr:PutImage"],
                    resources=[html_data_bucket._get_resource_arn_attribute(), repo._get_resource_arn_attribute()],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        vectorization_function_role = iam.Role(
            self,
            "Vectorization-Function-Exec-Role",
            role_name= RESOURCE_PREFIX + "vectorization-func-exec-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies=[
                vectorization_function_policy_doc
            ]
        )
        # Vectorization function
        vectorization_lambda = _lambda.Function(
            self,
            "Vectorization-Function",
            function_name=RESOURCE_PREFIX + "vectorization-function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="download-data-s3.handler",
            code=_lambda.Code.from_asset("rag/download-lambda"),
            environment = {
                'BUCKET_NAME': html_data_bucket.bucket_name
            },
            role=vectorization_function_role
        )

