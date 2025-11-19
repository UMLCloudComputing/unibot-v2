from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr
)
from constructs import Construct

RESOURCE_PREFIX = "gcp-rag-cdk-"

class RagCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)
        
        security_group = ec2.SecurityGroup(
            self, "rag-instance-SG",
            vpc=vpc,
            description="Allow SSH Access",
            allow_all_outbound=True
        )
            
    
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "Allow SSH Access")
        
        role = iam.Role(
            self, "rag-instance-sg",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
    
    
        instance = ec2.Instance(
            self, RESOURCE_PREFIX + "RAG-Instance",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.machineImage.latest_amazon_linux(),
            vpc=vpc,
            security_group=security_group,
            role=role
        )
    
        
        # repo_uri = ecr.Repository.from_repository_name("gcp_ecr_repository").repository_uri
        instance.add_user_data(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "curl -fsSL https://ramalama.ai/install.sh | bash",
            "uv add aiohttp",
            # f"export REPO_URI={repo_uri}", 
            "git clone https://github.com/nbottari9/comp4600_final.git",
            "cd comp4600_final/rag-scripts/",
            "uv run download_parallel.py && ./vectorize.sh"
        )
            
        
    
