from aws_cdk import (
    # Duration,
    Stack,
    Size,
    # aws_sqs as sqs,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from aws_cdk.lambda_layer_kubectl_v33 import KubectlV33Layer
from constructs import Construct
from collections.abc import Mapping
import json
import os

DEFAULT_VPC_ID = "vpc-01169b0ddb2a2f86b"
RESOURCE_PREFIX = "unibot-"
class Comp4600FinalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc.from_lookup(
            self,
            id=DEFAULT_VPC_ID,
            is_default=True
        )

        # IAM STUFF
        eks_assume_role_policy_json = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "./policies/eks_assume_role.json"), "r"))
        eks_auto_node_role = iam.Role(
            self,
            id=RESOURCE_PREFIX + "eks_auto_node_role",
            assumed_by = iam.ServicePrincipal("eks.amazonaws.com")
        )
        eks_auto_node_role.assume_role_policy.from_json(eks_assume_role_policy_json)
        
        
        # EKS Cluster
        cluster = eks.Cluster(self, RESOURCE_PREFIX + "cluster",
            kubectl_memory=Size.gibibytes(4),
            version=eks.KubernetesVersion.V1_33,
            kubectl_layer=KubectlV33Layer(self, "kubectl"),
            vpc=vpc
        )

        cluster.add_nodegroup_capacity("")
