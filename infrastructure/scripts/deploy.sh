#!/bin/bash
# Isshoni Deployment Script - Blue-Green Deployment with Zero Downtime
# Usage: ./deploy.sh [environment] [version]

set -e  # Exit on any error

# Configuration
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Pre-deployment checks
log_info "Starting deployment to $ENVIRONMENT (version: $VERSION)"

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

log_info "✓ AWS credentials verified"

# Check if required environment variables are set
if [ -z "$TERRAFORM_STATE_BUCKET" ]; then
    log_error "TERRAFORM_STATE_BUCKET not set. Check your .env file."
    exit 1
fi

log_info "✓ Environment variables verified"

# Step 2: Determine current and target environments
CURRENT_ENV=$(aws elbv2 describe-listeners \
    --listener-arns $LISTENER_ARN \
    --query 'Listeners[0].DefaultActions[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "blue")

if [[ "$CURRENT_ENV" == *"blue"* ]]; then
    TARGET_ENV="green"
    CURRENT_COLOR="blue"
    TARGET_COLOR="green"
else
    TARGET_ENV="blue"
    CURRENT_COLOR="green"
    TARGET_COLOR="blue"
fi

log_info "Current environment: $CURRENT_COLOR"
log_info "Deploying to: $TARGET_COLOR"

# Step 3: Build Docker images
log_info "Building Docker images..."

cd "$PROJECT_ROOT"

docker build -t isshoni-backend:$VERSION ./backend
docker build -t isshoni-frontend:$VERSION ./frontend

log_info "✓ Docker images built"

# Step 4: Push to ECR (if using AWS)
if [ "$ENVIRONMENT" != "local" ]; then
    log_info "Pushing images to ECR..."

    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${AWS_DEFAULT_REGION:-ap-northeast-2}
    ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ECR_REGISTRY

    # Tag and push
    docker tag isshoni-backend:$VERSION $ECR_REGISTRY/isshoni-backend:$VERSION
    docker tag isshoni-frontend:$VERSION $ECR_REGISTRY/isshoni-frontend:$VERSION

    docker push $ECR_REGISTRY/isshoni-backend:$VERSION
    docker push $ECR_REGISTRY/isshoni-frontend:$VERSION

    log_info "✓ Images pushed to ECR"
fi

# Step 5: Deploy to target environment using Terraform
log_info "Deploying infrastructure with Terraform..."

cd "$PROJECT_ROOT/infrastructure/terraform"

terraform init \
    -backend-config="bucket=$TERRAFORM_STATE_BUCKET" \
    -backend-config="key=$ENVIRONMENT/terraform.tfstate" \
    -backend-config="region=$AWS_REGION"

terraform plan \
    -var="environment=$ENVIRONMENT" \
    -var="target_group=$TARGET_COLOR" \
    -var="image_version=$VERSION" \
    -out=tfplan

terraform apply tfplan

log_info "✓ Infrastructure deployed to $TARGET_COLOR environment"

# Step 6: Health checks
log_info "Running health checks on $TARGET_COLOR environment..."

TARGET_GROUP_ARN=$(terraform output -raw ${TARGET_COLOR}_target_group_arn)

# Wait for targets to be healthy
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    HEALTHY_COUNT=$(aws elbv2 describe-target-health \
        --target-group-arn $TARGET_GROUP_ARN \
        --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`] | length(@)' \
        --output text)

    if [ "$HEALTHY_COUNT" -ge 2 ]; then
        log_info "✓ All targets healthy ($HEALTHY_COUNT instances)"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    log_warn "Waiting for targets to be healthy... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    log_error "Health checks failed. Rolling back..."
    terraform destroy -target=aws_autoscaling_group.$TARGET_COLOR -auto-approve
    exit 1
fi

# Step 7: Gradual traffic shift
log_info "Starting gradual traffic shift..."

shift_traffic() {
    local blue_weight=$1
    local green_weight=$2

    aws elbv2 modify-listener \
        --listener-arn $LISTENER_ARN \
        --default-actions Type=forward,ForwardConfig="{
            \"TargetGroups\": [
                {\"TargetGroupArn\": \"$BLUE_TG_ARN\", \"Weight\": $blue_weight},
                {\"TargetGroupArn\": \"$GREEN_TG_ARN\", \"Weight\": $green_weight}
            ]
        }" > /dev/null

    log_info "Traffic: Blue $blue_weight%, Green $green_weight%"
}

# Get target group ARNs
BLUE_TG_ARN=$(terraform output -raw blue_target_group_arn)
GREEN_TG_ARN=$(terraform output -raw green_target_group_arn)

if [ "$TARGET_COLOR" == "green" ]; then
    shift_traffic 90 10
    sleep 120  # Monitor for 2 minutes
    shift_traffic 50 50
    sleep 120
    shift_traffic 10 90
    sleep 60
    shift_traffic 0 100
else
    shift_traffic 10 90
    sleep 120
    shift_traffic 50 50
    sleep 120
    shift_traffic 90 10
    sleep 60
    shift_traffic 100 0
fi

log_info "✓ Traffic fully shifted to $TARGET_COLOR"

# Step 8: Drain old environment
log_info "Draining connections from $CURRENT_COLOR..."

# Enable connection draining (300 seconds)
aws elbv2 modify-target-group-attributes \
    --target-group-arn $([ "$TARGET_COLOR" == "green" ] && echo "$BLUE_TG_ARN" || echo "$GREEN_TG_ARN") \
    --attributes Key=deregistration_delay.timeout_seconds,Value=300

# Wait for drain timeout
log_warn "Waiting 5 minutes for connection draining..."
sleep 300

log_info "✓ Old environment drained"

# Step 9: Cleanup (optional)
read -p "Terminate old $CURRENT_COLOR environment? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Terminating $CURRENT_COLOR environment..."
    terraform destroy -target=aws_autoscaling_group.$CURRENT_COLOR -auto-approve
    log_info "✓ Old environment terminated"
fi

# Step 10: Deployment complete
log_info "=========================================="
log_info "✓ Deployment completed successfully!"
log_info "Environment: $ENVIRONMENT"
log_info "Version: $VERSION"
log_info "Active: $TARGET_COLOR"
log_info "=========================================="

# Get application URL
ALB_DNS=$(terraform output -raw alb_dns_name)
log_info "Access your application at: http://$ALB_DNS"

exit 0
