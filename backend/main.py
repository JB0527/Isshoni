"""
Isshoni Backend - FastAPI server with WebSocket support
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import os
import json
from dotenv import load_dotenv

from models import (
    CanvasState,
    ChatMessage,
    CodeGenerationRequest,
    CodeGenerationResponse,
    DeploymentRequest,
    DeploymentResponse,
    AWSResource,
    Connection
)
from websocket_manager import ConnectionManager
from redis_client import RedisClient
from ai_generator import AICodeGenerator
from terraform_executor import TerraformExecutor

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Isshoni Backend API",
    description="AI-powered visual infrastructure generator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
ws_manager = ConnectionManager()
redis_client = RedisClient()
ai_generator = AICodeGenerator()
terraform_executor = TerraformExecutor()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Isshoni Backend",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api/sessions/{session_id}/canvas")
async def get_canvas_state(session_id: str):
    """Get current canvas state for a session"""
    state = redis_client.get_canvas_state(session_id)
    if state:
        return state
    return CanvasState(session_id=session_id)


@app.post("/api/sessions/{session_id}/canvas")
async def update_canvas_state(session_id: str, state: CanvasState):
    """Update canvas state"""
    # Save to Redis
    redis_client.save_canvas_state(session_id, state)

    # Broadcast to all connected clients
    await ws_manager.broadcast_to_session(
        session_id,
        {
            "type": "canvas_update",
            "data": state.model_dump()
        }
    )

    return {"success": True}


@app.get("/api/sessions/{session_id}/chat")
async def get_chat_history(session_id: str, count: int = 50):
    """Get chat history for a session"""
    messages = redis_client.get_chat_history(session_id, count)
    return {"messages": [msg.model_dump() for msg in messages]}


@app.post("/api/sessions/{session_id}/chat")
async def send_chat_message(session_id: str, message: ChatMessage):
    """Send a chat message"""
    # Save to Redis
    redis_client.save_chat_message(message)

    # Broadcast to all connected clients
    await ws_manager.broadcast_to_session(
        session_id,
        {
            "type": "chat_message",
            "data": message.model_dump()
        }
    )

    return {"success": True}


@app.post("/api/generate-code", response_model=CodeGenerationResponse)
async def generate_code(request: CodeGenerationRequest):
    """Generate Terraform/CloudFormation code from canvas state"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        if request.target_format == "terraform":
            result = ai_generator.generate_terraform_code(
                request.canvas_state,
                provider=request.ai_provider
            )
            logger.info(f"📤 응답 전송 - success: {result.success}, code length: {len(result.code) if result.code else 0}")
            return result
        else:
            result = ai_generator.generate_cloudformation_code(request.canvas_state)
            logger.info(f"📤 응답 전송 - success: {result.success}, code length: {len(result.code) if result.code else 0}")
            return result

    except Exception as e:
        logger.error(f"❌ Exception in generate_code: {str(e)}")
        return CodeGenerationResponse(
            success=False,
            error=f"Code generation failed: {str(e)}"
        )


@app.post("/api/deploy", response_model=DeploymentResponse)
async def deploy_infrastructure(request: DeploymentRequest):
    """Deploy infrastructure using Terraform"""
    try:
        if request.format == "terraform":
            success, outputs, error = terraform_executor.deploy(
                request.code,
                request.session_id,
                auto_approve=request.auto_approve
            )

            return DeploymentResponse(
                success=success,
                deployment_id=request.session_id,
                status="deployed" if success else "failed",
                outputs=outputs,
                error=error if not success else None
            )
        else:
            return DeploymentResponse(
                success=False,
                deployment_id=request.session_id,
                status="failed",
                error="CloudFormation deployment not supported in MVP"
            )

    except Exception as e:
        return DeploymentResponse(
            success=False,
            deployment_id=request.session_id,
            status="failed",
            error=str(e)
        )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time collaboration"""
    await ws_manager.connect(websocket, session_id)

    try:
        # Send connection confirmation
        await ws_manager.send_personal_message(
            {
                "type": "connected",
                "session_id": session_id,
                "active_users": ws_manager.get_session_count(session_id)
            },
            websocket
        )

        # Send current canvas state
        canvas_state = redis_client.get_canvas_state(session_id)
        if canvas_state:
            await ws_manager.send_personal_message(
                {
                    "type": "canvas_state",
                    "data": canvas_state.model_dump()
                },
                websocket
            )

        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_type = message_data.get("type")

            if message_type == "canvas_update":
                # Update canvas state
                canvas_state = CanvasState(**message_data["data"])
                redis_client.save_canvas_state(session_id, canvas_state)

                # Broadcast to others
                await ws_manager.broadcast_to_session(
                    session_id,
                    {
                        "type": "canvas_update",
                        "data": canvas_state.model_dump()
                    }
                )

            elif message_type == "chat_message":
                # Save and broadcast chat message
                chat_msg = ChatMessage(**message_data["data"])
                redis_client.save_chat_message(chat_msg)

                await ws_manager.broadcast_to_session(
                    session_id,
                    {
                        "type": "chat_message",
                        "data": chat_msg.model_dump()
                    }
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
        # Notify others
        await ws_manager.broadcast_to_session(
            session_id,
            {
                "type": "user_disconnected",
                "active_users": ws_manager.get_session_count(session_id)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
