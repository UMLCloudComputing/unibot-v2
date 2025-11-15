from constructs import Construct
from aws_cdk import aws_iam as iam
from pathlib import Path
import json


class PolicyLoader(Construct):

    def __init__(self, scope: Construct, id: str, *, root: Path = None):
        super().__init__(scope, id)

        # project root defaults to: /project_root
        self.project_root = root or Path(__file__).parents[2]
        self.policy_dir = self.project_root / "policies"

        if not self.policy_dir.exists():
            raise FileNotFoundError(f"Policy directory not found: {self.policy_dir}")

    def load_policy(self, filename: str) -> iam.PolicyDocument:
        """Load a single policy document from /policies and return as PolicyDocument."""

        policy_file = self.policy_dir / filename

        if not policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_file}")

        with open(policy_file) as f:
            policy_json = json.load(f)

        return iam.PolicyDocument.from_json(policy_json)

    def attach_inline(self, role: iam.Role, filename: str, name: str = None):
        """Attach a policy JSON file to a role as an inline policy."""
        doc = self.load_policy(filename)
        role.add_to_policy(iam.PolicyStatement.from_json(doc.to_json()))

    def create_managed_policy(self, filename: str, id: str) -> iam.ManagedPolicy:
        """Create a managed policy from a JSON file."""
        doc = self.load_policy(filename)
        return iam.ManagedPolicy(self, id, document=doc)
