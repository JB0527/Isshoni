"""
Terraform executor for deploying infrastructure
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Tuple
from python_terraform import Terraform
import boto3


class TerraformExecutor:
    def __init__(self):
        self.s3_client = None
        self.state_bucket = os.getenv("TERRAFORM_STATE_BUCKET")

        # Initialize S3 client if credentials are available
        if os.getenv("AWS_ACCESS_KEY_ID"):
            self.s3_client = boto3.client('s3')

    def deploy(
        self,
        code: str,
        session_id: str,
        auto_approve: bool = False
    ) -> Tuple[bool, Dict, str]:
        """
        Deploy infrastructure using Terraform

        Returns: (success, outputs, error_message)
        """

        # Create temporary directory for Terraform files
        temp_dir = tempfile.mkdtemp(prefix=f"terraform_{session_id}_")

        try:
            # Write Terraform code to file
            tf_file = Path(temp_dir) / "main.tf"
            tf_file.write_text(code)

            # Initialize Terraform
            tf = Terraform(working_dir=temp_dir)

            # Run terraform init
            return_code, stdout, stderr = tf.init()
            if return_code != 0:
                return False, {}, f"Terraform init failed: {stderr}"

            # Run terraform plan
            return_code, stdout, stderr = tf.plan(out='tfplan')
            if return_code != 0:
                return False, {}, f"Terraform plan failed: {stderr}"

            # Run terraform apply (if auto-approved)
            if auto_approve:
                return_code, stdout, stderr = tf.apply(
                    'tfplan',
                    skip_plan=True,
                    capture_output=False
                )
                if return_code != 0:
                    return False, {}, f"Terraform apply failed: {stderr}"

                # Get outputs
                return_code, outputs, stderr = tf.output(json=True)
                if return_code == 0 and outputs:
                    import json
                    output_dict = json.loads(outputs) if isinstance(outputs, str) else outputs
                    return True, output_dict, ""

                return True, {}, ""

            else:
                # Return plan output for user review
                return True, {"plan": stdout}, "Plan generated successfully. Review and approve to deploy."

        except Exception as e:
            return False, {}, f"Deployment error: {str(e)}"

        finally:
            # Cleanup temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def destroy(self, session_id: str) -> Tuple[bool, str]:
        """
        Destroy infrastructure

        Returns: (success, message)
        """
        # Implementation for destroying infrastructure
        # This would require storing the terraform state somewhere
        return False, "Destroy not implemented in MVP"

    def get_state(self, session_id: str) -> Dict:
        """Get current Terraform state"""
        # In production, this would fetch from S3
        return {}
