"""
AI-powered Infrastructure as Code generator
GMS GPT-5 전용
"""
import os
import logging
from typing import Dict, List
from openai import OpenAI
from models import CanvasState, AWSResource, Connection, CodeGenerationResponse

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AICodeGenerator:
    def __init__(self):
        self.openai_client = None

        if os.getenv("OPENAI_API_KEY"):
            # GMS GPT-5 API
            self.openai_client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1",
                timeout=600.0,  # 10분 타임아웃 (GMS API 응답 대기)
                max_retries=3   # 최대 3번 재시도
            )

    def generate_terraform_code(
        self,
        canvas_state: CanvasState,
        provider: str = "openai"  # GMS만 사용
    ) -> CodeGenerationResponse:
        """Generate Terraform code from canvas state using GMS GPT-5"""

        logger.info(f"🚀 Terraform 코드 생성 시작")

        try:
            if not self.openai_client:
                return CodeGenerationResponse(
                    success=False,
                    error="SSAFY GMS API key not configured. Please set OPENAI_API_KEY in .env file."
                )

            # Build the prompt
            prompt = self._build_terraform_prompt(canvas_state)
            logger.info(f"📝 프롬프트 생성 완료 - {len(canvas_state.resources)}개 리소스")

            # GPT-5로 코드 생성
            code = self._generate_with_gpt(prompt, output_format="terraform")

            logger.info(f"✅ Terraform 코드 생성 완료")
            return CodeGenerationResponse(
                success=True,
                code=code,
                estimated_cost="SSAFY GMS 사용 (무료)"
            )

        except Exception as e:
            logger.error(f"❌ 생성 실패: {str(e)}")
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

    def _generate_with_gpt(self, prompt: str, output_format: str = "terraform") -> str:
        """Generate code using GPT-5-nano (SSAFY GMS)"""

        system_msg = f"You are an expert AWS infrastructure engineer. Generate production-ready {output_format.upper()} code in Korean. Answer in Korean."

        logger.info(f"🤖 GPT-5-nano API 호출 시작... (format: {output_format})")

        response = self.openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "developer",
                    "content": system_msg
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=100000
        )

        logger.info(f"✅ GPT-5-nano 응답 받음")
        return response.choices[0].message.content

    def generate_cloudformation_code(self, canvas_state: CanvasState) -> CodeGenerationResponse:
        """Generate CloudFormation YAML from canvas state using GPT-5"""

        logger.info(f"🚀 CloudFormation 코드 생성 시작")

        try:
            if not self.openai_client:
                return CodeGenerationResponse(
                    success=False,
                    error="SSAFY GMS API key not configured. Please set OPENAI_API_KEY in .env file."
                )

            # Build the prompt for CloudFormation
            prompt = self._build_cloudformation_prompt(canvas_state)
            logger.info(f"📝 프롬프트 생성 완료 - {len(canvas_state.resources)}개 리소스")

            # GPT-5로 코드 생성
            code = self._generate_with_gpt(prompt, output_format="cloudformation")

            logger.info(f"✅ CloudFormation 코드 생성 완료")
            return CodeGenerationResponse(
                success=True,
                code=code,
                estimated_cost="SSAFY GMS 사용 (무료)"
            )

        except Exception as e:
            logger.error(f"❌ 생성 실패: {str(e)}")
            return CodeGenerationResponse(
                success=False,
                error=str(e)
            )

    def _build_cloudformation_prompt(self, canvas_state: CanvasState) -> str:
        """Build a detailed prompt for CloudFormation code generation"""

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

        prompt = f"""AWS 인프라를 CloudFormation YAML로 만들어주세요:

**사용자 요구사항:**
{canvas_state.user_prompt if canvas_state.user_prompt else "표준 AWS 인프라"}

**생성할 리소스:**
{chr(10).join(resources_summary)}

**연결 관계:**
{chr(10).join(connections_summary) if connections_summary else "명시적 연결 없음"}

**요구사항:**
1. 보안 모범 사례 적용 (VPC, Security Groups, IAM Roles)
2. 가용성 높게 설정 (Multi-AZ)
3. 비용 관리를 위한 태깅
4. 파라미터로 설정 가능한 값들 정의
5. 중요한 리소스 ID와 엔드포인트는 Outputs에 포함
6. 중요 섹션에 주석 추가
7. 기본 리전은 ap-northeast-2 (서울) 사용

**출력 형식:**
CloudFormation YAML 코드만 제공하세요. 설명은 코드 주석으로만 포함하세요.
"""
        return prompt
