"""
Isshoni Frontend - Streamlit UI for Visual Infrastructure Design
"""
import streamlit as st
import requests
import json
from datetime import datetime
import uuid

# Page configuration
st.set_page_config(
    page_title="Isshoni - Visual Infrastructure Generator",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API URL
BACKEND_URL = "http://localhost:8000"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "username" not in st.session_state:
    st.session_state.username = f"User_{st.session_state.user_id}"

if "canvas_resources" not in st.session_state:
    st.session_state.canvas_resources = []

if "canvas_connections" not in st.session_state:
    st.session_state.canvas_connections = []

if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


def main():
    """Main application"""

    # Header
    st.title("☁️ Isshoni - AI-Powered Infrastructure Designer")
    st.markdown("**一緒に (Isshoni)** = Build cloud infrastructure together with AI")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.text_input("Session ID", value=st.session_state.session_id, disabled=True)
        st.text_input("Your Username", value=st.session_state.username, key="username_input")

        st.divider()

        st.subheader("AWS Credentials")
        aws_access_key = st.text_input("AWS Access Key", type="password")
        aws_secret_key = st.text_input("AWS Secret Key", type="password")
        aws_region = st.selectbox("Region", ["ap-northeast-2", "us-east-1", "eu-west-1"])

        st.divider()

        st.subheader("AI Provider")
        ai_provider = st.radio("Choose AI Provider", ["SSAFY GMS (GPT-5)", "Anthropic (Claude)"])
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter your SSAFY GMS API key or Anthropic API key"
        )

        st.divider()

        if st.button("🔄 Reset Canvas"):
            st.session_state.canvas_resources = []
            st.session_state.canvas_connections = []
            st.rerun()

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📐 Canvas", "💬 Chat", "🤖 Generate Code", "🚀 Deploy"])

    # Tab 1: Visual Canvas
    with tab1:
        st.header("Visual Infrastructure Canvas")

        # User prompt
        user_prompt = st.text_area(
            "Describe your infrastructure needs:",
            placeholder="e.g., I need a disaster notification system that can handle 1M concurrent users with WebSocket connections...",
            height=100
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Design Canvas")

            # Resource palette
            st.write("**Available AWS Resources:**")
            resource_cols = st.columns(4)

            with resource_cols[0]:
                if st.button("➕ VPC"):
                    add_resource("vpc", "VPC")
                if st.button("➕ EC2"):
                    add_resource("ec2", "EC2 Instance")

            with resource_cols[1]:
                if st.button("➕ RDS"):
                    add_resource("rds", "RDS Database")
                if st.button("➕ ALB"):
                    add_resource("alb", "Application Load Balancer")

            with resource_cols[2]:
                if st.button("➕ Redis"):
                    add_resource("redis", "ElastiCache Redis")
                if st.button("➕ S3"):
                    add_resource("s3", "S3 Bucket")

            with resource_cols[3]:
                if st.button("➕ Lambda"):
                    add_resource("lambda", "Lambda Function")
                if st.button("➕ API Gateway"):
                    add_resource("apigateway", "API Gateway")

            st.divider()

            # Display current resources
            if st.session_state.canvas_resources:
                st.write("**Current Resources:**")
                for i, resource in enumerate(st.session_state.canvas_resources):
                    col_a, col_b, col_c = st.columns([3, 2, 1])
                    with col_a:
                        st.write(f"**{resource['name']}** ({resource['type']})")
                    with col_b:
                        notes = st.text_input(
                            "Notes",
                            value=resource.get("notes", ""),
                            key=f"notes_{i}",
                            placeholder="Add configuration notes..."
                        )
                        st.session_state.canvas_resources[i]["notes"] = notes
                    with col_c:
                        if st.button("🗑️", key=f"delete_{i}"):
                            st.session_state.canvas_resources.pop(i)
                            st.rerun()
            else:
                st.info("👆 Click on resources above to add them to your canvas")

        with col2:
            st.subheader("Connections")

            if len(st.session_state.canvas_resources) >= 2:
                st.write("**Define connections between resources:**")

                resource_names = [r["name"] for r in st.session_state.canvas_resources]

                from_resource = st.selectbox("From", resource_names, key="conn_from")
                to_resource = st.selectbox("To", resource_names, key="conn_to")
                conn_type = st.selectbox(
                    "Type",
                    ["network", "data", "api", "message"],
                    key="conn_type"
                )

                if st.button("➕ Add Connection"):
                    if from_resource != to_resource:
                        st.session_state.canvas_connections.append({
                            "from_resource": from_resource,
                            "to_resource": to_resource,
                            "connection_type": conn_type
                        })
                        st.success("Connection added!")
                    else:
                        st.warning("Cannot connect a resource to itself")

                if st.session_state.canvas_connections:
                    st.write("**Current Connections:**")
                    for i, conn in enumerate(st.session_state.canvas_connections):
                        col_x, col_y = st.columns([4, 1])
                        with col_x:
                            st.write(f"{conn['from_resource']} → {conn['to_resource']} ({conn['connection_type']})")
                        with col_y:
                            if st.button("🗑️", key=f"del_conn_{i}"):
                                st.session_state.canvas_connections.pop(i)
                                st.rerun()
            else:
                st.info("Add at least 2 resources to create connections")

    # Tab 2: Team Chat
    with tab2:
        st.header("💬 Team Chat")

        # Display chat messages
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["username"]):
                    st.write(msg["message"])
                    st.caption(msg["timestamp"])

        # Chat input
        chat_input = st.chat_input("Type your message...")
        if chat_input:
            new_message = {
                "username": st.session_state.username,
                "message": chat_input,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.chat_messages.append(new_message)
            st.rerun()

    # Tab 3: Generate Code
    with tab3:
        st.header("🤖 AI Code Generation")

        if not st.session_state.canvas_resources:
            st.warning("⚠️ Add some resources to the canvas first!")
        else:
            st.write("**Canvas Summary:**")
            st.write(f"- Resources: {len(st.session_state.canvas_resources)}")
            st.write(f"- Connections: {len(st.session_state.canvas_connections)}")

            st.divider()

            col_gen1, col_gen2 = st.columns(2)

            with col_gen1:
                target_format = st.radio("Output Format", ["Terraform", "CloudFormation"])

            with col_gen2:
                provider = "openai" if "GPT-5" in ai_provider else "anthropic"

            if st.button("✨ Generate Infrastructure Code", type="primary"):
                if not api_key:
                    st.error("Please enter your API key in the sidebar!")
                else:
                    with st.spinner("AI is generating your infrastructure code..."):
                        # Prepare request
                        canvas_state = {
                            "session_id": st.session_state.session_id,
                            "resources": [
                                {
                                    "id": str(i),
                                    "type": r["type"],
                                    "name": r["name"],
                                    "x": i * 100,
                                    "y": i * 100,
                                    "properties": {},
                                    "notes": r.get("notes", "")
                                }
                                for i, r in enumerate(st.session_state.canvas_resources)
                            ],
                            "connections": st.session_state.canvas_connections,
                            "user_prompt": user_prompt
                        }

                        try:
                            response = requests.post(
                                f"{BACKEND_URL}/api/generate-code",
                                json={
                                    "session_id": st.session_state.session_id,
                                    "canvas_state": canvas_state,
                                    "target_format": target_format.lower(),
                                    "ai_provider": provider
                                },
                                timeout=120
                            )

                            if response.status_code == 200:
                                result = response.json()
                                if result["success"]:
                                    st.session_state.generated_code = result["code"]
                                    st.success("✅ Code generated successfully!")
                                else:
                                    st.error(f"Generation failed: {result['error']}")
                            else:
                                st.error(f"API error: {response.status_code}")

                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Display generated code
            if st.session_state.generated_code:
                st.divider()
                st.subheader("Generated Code")

                st.code(st.session_state.generated_code, language="hcl")

                col_download1, col_download2 = st.columns(2)
                with col_download1:
                    st.download_button(
                        "📥 Download Code",
                        st.session_state.generated_code,
                        file_name="infrastructure.tf",
                        mime="text/plain"
                    )
                with col_download2:
                    if st.button("📋 Copy to Clipboard"):
                        st.toast("Code copied to clipboard!")

    # Tab 4: Deploy
    with tab4:
        st.header("🚀 Deploy Infrastructure")

        if not st.session_state.generated_code:
            st.warning("⚠️ Generate code first in the 'Generate Code' tab!")
        else:
            st.write("**Deployment Configuration:**")

            auto_approve = st.checkbox(
                "Auto-approve deployment",
                help="Automatically apply changes without manual approval"
            )

            st.warning("⚠️ This will create real AWS resources that may incur costs!")

            if st.button("🚀 Deploy Now", type="primary"):
                if not aws_access_key or not aws_secret_key:
                    st.error("Please enter AWS credentials in the sidebar!")
                else:
                    with st.spinner("Deploying infrastructure..."):
                        try:
                            response = requests.post(
                                f"{BACKEND_URL}/api/deploy",
                                json={
                                    "session_id": st.session_state.session_id,
                                    "code": st.session_state.generated_code,
                                    "format": "terraform",
                                    "auto_approve": auto_approve
                                },
                                timeout=300
                            )

                            if response.status_code == 200:
                                result = response.json()
                                if result["success"]:
                                    st.success("✅ Deployment successful!")
                                    st.json(result["outputs"])
                                else:
                                    st.error(f"Deployment failed: {result['error']}")
                            else:
                                st.error(f"API error: {response.status_code}")

                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            st.divider()

            st.subheader("Deployment Status")
            st.info("No active deployments")


def add_resource(resource_type: str, resource_name: str):
    """Add a resource to the canvas"""
    resource_id = f"{resource_type}_{len(st.session_state.canvas_resources)}"
    st.session_state.canvas_resources.append({
        "id": resource_id,
        "type": resource_type,
        "name": f"{resource_name}_{len(st.session_state.canvas_resources) + 1}",
        "notes": ""
    })
    st.rerun()


if __name__ == "__main__":
    main()
