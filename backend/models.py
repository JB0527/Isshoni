"""
Data models for Isshoni platform
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


class AWSResource(BaseModel):
    """Represents an AWS resource on the canvas"""
    id: str
    type: Literal["vpc", "ec2", "rds", "alb", "redis", "s3", "lambda", "apigateway"]
    name: str
    x: float
    y: float
    properties: Dict = Field(default_factory=dict)
    notes: str = ""


class Connection(BaseModel):
    """Connection between two resources"""
    from_resource: str
    to_resource: str
    connection_type: str = "default"  # e.g., "network", "data", "api"


class CanvasState(BaseModel):
    """Complete state of the infrastructure canvas"""
    session_id: str
    resources: List[AWSResource] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
    user_prompt: str = ""
    last_updated: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    """Chat message between team members"""
    session_id: str
    user_id: str
    username: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class CodeGenerationRequest(BaseModel):
    """Request to generate IaC code"""
    session_id: str
    canvas_state: CanvasState
    target_format: Literal["terraform", "cloudformation"] = "terraform"
    ai_provider: Literal["anthropic", "openai"] = "anthropic"


class CodeGenerationResponse(BaseModel):
    """Response with generated code"""
    success: bool
    code: str = ""
    error: Optional[str] = None
    estimated_cost: Optional[str] = None


class DeploymentRequest(BaseModel):
    """Request to deploy infrastructure"""
    session_id: str
    code: str
    format: Literal["terraform", "cloudformation"]
    auto_approve: bool = False


class DeploymentResponse(BaseModel):
    """Deployment result"""
    success: bool
    deployment_id: str
    status: str
    outputs: Dict = Field(default_factory=dict)
    error: Optional[str] = None
