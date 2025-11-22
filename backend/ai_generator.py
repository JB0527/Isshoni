"""
AI-powered Infrastructure as Code generator
SSAFY GMS GPT-5 전용
"""
import os
from typing import Dict, List
from openai import OpenAI
from models import CanvasState, AWSResource, Connection, CodeGenerationResponse


class AICodeGenerator:
    def __init__(self):
        self.openai_client = None

        if os.getenv("OPENAI_API_KEY"):
            # GMS GPT-5 API
            self.openai_client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1"
            )

    def generate_terraform_code(
        self,
        canvas_state: CanvasState,
        provider: str = "openai"  # GMS만 사용
    ) -> CodeGenerationResponse:
        """Generate Terraform code from canvas state using GMS GPT-5"""

        # Build the prompt
        prompt = self._build_terraform_prompt(canvas_state)

        try:
            if self.openai_client:
                code = self._generate_with_gpt(prompt)
            else:
                return CodeGenerationResponse(
                    success=False,
                    error=" GMS API key not configured. Please set OPENAI_API_KEY in .env file."
                )

            return CodeGenerationResponse(
                success=True,
                code=code,
                estimated_cost=" GMS 사용 (무료)"
            )

        except Exception as e:
            return CodeGenerationResponse(
                success=False,
                error=str(e)
            )

    def _build_terraform_prompt(self, canvas_state: CanvasState) -> str:
        """Build a detailed prompt for Terraform code generation"""

        resources_summary = []
        for resource in canvas_state.resources:
            resources_summary.append(
                f"- {resource.type.upper()} (name: {resource.name})"
                + (f"\n  Notes: {resource.notes}" if resource.notes else "")
            )

        connections_summary = []
        for conn in canvas_state.connections:
            connections_summary.append(
                f"- {conn.from_resource} -> {conn.to_resource} ({conn.connection_type})"
            )

        prompt = f"""You are an expert AWS infrastructure architect. Generate production-ready Terraform code based on this infrastructure design:

**User Requirements:**
{canvas_state.user_prompt if canvas_state.user_prompt else "Standard AWS infrastructure"}

**Resources to Create:**
{chr(10).join(resources_summary)}

**Connections:**
{chr(10).join(connections_summary) if connections_summary else "No explicit connections defined"}

**Requirements:**
1. Use best practices for security (VPC, security groups, IAM roles)
2. Enable high availability where applicable (multi-AZ)
3. Add proper tagging for cost management
4. Use variables for configurable parameters
5. Include outputs for important resource IDs and endpoints
6. Add comments explaining critical sections
7. Use ap-northeast-2 (Seoul) as the default region

**Output Format:**
Provide ONLY the Terraform code with proper structure:
- variables.tf content
- main.tf content
- outputs.tf content

DO NOT include explanations outside of code comments. Start directly with the code.
"""
        return prompt

    def _generate_with_gpt(self, prompt: str) -> str:
        """Generate code using GPT-5 ( GMS)"""
        response = self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert AWS infrastructure engineer who writes production-ready Terraform code."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=128000  # GPT-5 supports up to 128k output tokens
        )
        return response.choices[0].message.content

    def generate_cloudformation_code(self, canvas_state: CanvasState) -> CodeGenerationResponse:
        """Generate CloudFormation YAML from canvas state"""
        # Similar implementation but for CloudFormation
        # For MVP, we'll focus on Terraform
        return CodeGenerationResponse(
            success=False,
            error="CloudFormation generation not implemented in MVP"
        )
