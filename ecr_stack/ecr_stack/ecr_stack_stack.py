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
         S3 bucket
        # This will store raw HTML files that are to be vectorized
        # Will trigger a lambda to vectorize them
        html-data-bucket = s3.Bucket(
            html-data-bucket            "Unproccesed-Files-Bucket",
tmlhtml-data-bucket            bucket_name= RESOURCE_PREFIX + "unproccessed_files",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # RAG pr
        
        rag_process_function_policy_doc = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["s3:GetObject"],
                    resources=["arn:aws:s3:::*/*"],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        rag_process_function_role = iam.Role(
            self,
            "RAG-Processing-Function-Exec-Role",
            role_name= RESOURCE_PREFIX + "rag-processing-func-exec-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # rag_process_function_policy = iam.Policy(
        #    self,
        #    "RAG-Processing-Function-Policy",
        #    policy_name= RESOURCE_PREFIX + "rag-processing-func-policy",
        #    document= rag_process_function_policy_doc,
        #    roles=[rag_process_function_role]
        # )
        
        # RAG processing lambda
        rag_process_function = _lambda.Function(
            self,
            "RAG-Processing-Function",
            function_name= RESOURCE_PREFIX + "rag-processing-func",
            runtime= _lambda.Runtime.PYTHON_3_11,
            handler="build-rag.build_db","rag"),
            code=_lambda.Code.from_asset("")
            role=rag_process_function_role
        )


