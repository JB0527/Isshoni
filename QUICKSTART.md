# Quick Start Guide

Get Isshoni running in 5 minutes!

## Prerequisites

- Docker & Docker Compose installed
- AWS Account (for deployment features)
- Anthropic or OpenAI API key

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Isshoni

# Copy environment template
cp .env.example .env
```

## Step 2: Configure Environment

Edit `.env` file with your credentials:

```bash
# Required for AI code generation (choose one)
ANTHROPIC_API_KEY=sk-ant-xxxxx
# OR
OPENAI_API_KEY=sk-xxxxx

# Required for actual AWS deployment
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-northeast-2

# Required for Terraform state storage
TERRAFORM_STATE_BUCKET=isshoni-tfstate-your-name
```

**Get API Keys**:
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys

## Step 3: Start the Application

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Expected output:
```
NAME                STATUS    PORTS
isshoni-backend     Up        0.0.0.0:8000->8000/tcp
isshoni-frontend    Up        0.0.0.0:8501->8501/tcp
isshoni-redis       Up        0.0.0.0:6379->6379/tcp
```

## Step 4: Access the Application

Open your browser and navigate to:

- **Frontend UI**: http://localhost:8501
- **Backend API Docs**: http://localhost:8000/docs

## Step 5: Design Your First Infrastructure

1. **Describe your needs** in the text area:
   ```
   "I need a web application with auto-scaling, database, and caching"
   ```

2. **Add resources** by clicking the buttons:
   - Click "➕ VPC"
   - Click "➕ ALB"
   - Click "➕ EC2"
   - Click "➕ RDS"
   - Click "➕ Redis"

3. **Create connections**:
   - From: ALB → To: EC2 (Type: network)
   - From: EC2 → To: RDS (Type: data)
   - From: EC2 → To: Redis (Type: message)

4. **Generate code**:
   - Go to "🤖 Generate Code" tab
   - Click "✨ Generate Infrastructure Code"
   - Wait 10-20 seconds for AI to generate Terraform code

5. **Review and Download**:
   - Review the generated code
   - Download with "📥 Download Code" button

6. **Deploy** (optional):
   - Go to "🚀 Deploy" tab
   - Click "🚀 Deploy Now"
   - Monitor deployment progress

## Troubleshooting

### Backend not starting?

```bash
# Check logs
docker-compose logs backend

# Common issue: Redis not ready
docker-compose restart backend
```

### Frontend can't connect to backend?

```bash
# Check if backend is healthy
curl http://localhost:8000/

# Should return: {"service": "Isshoni Backend", "status": "healthy"}
```

### AI generation fails?

- Verify your API key is correct in `.env`
- Check if you have credits/quota remaining
- Look at backend logs: `docker-compose logs backend`

### Deployment fails?

- Verify AWS credentials are correct
- Ensure your IAM user has necessary permissions:
  - EC2 full access
  - VPC full access
  - RDS full access
  - ElastiCache full access
  - S3 read/write
- Create the S3 bucket for Terraform state first:
  ```bash
  aws s3 mb s3://isshoni-tfstate-your-name
  aws s3api put-bucket-versioning \
    --bucket isshoni-tfstate-your-name \
    --versioning-configuration Status=Enabled
  ```

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design
- Check [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for production deployment
- Explore [templates/](./templates/) for example Terraform code

## Development Mode

To run in development mode with hot reloading:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Getting Help

- Issues: https://github.com/your-org/isshoni/issues
- Documentation: [README.md](./README.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

**Happy Infrastructure Building! 🎉**
