#!/bin/bash
set -eu

# NOTE: ECR_REPO is a required global variable that must be set to upload to ecr
# NOTE: 
# If argument count is less than 2
if [ $# -lt 2 ]; then
    echo "Usage: vectorize.sh <local|mac|ecr> <directory/oci-image-name>"
    exit 1
fi

REPO_NAME="gcp-ecr-repo"

# Get repository info from ECR
OUTPUT=$(aws ecr describe-repositories --repository-names "$REPO_NAME" --output json 2>/dev/null)

# Extract repositoryUri using jq
REPO_URI=$(echo "$OUTPUT" | jq -r '.repositories[0].repositoryUri')

if [ -z "$REPO_URI" ] || [ "$REPO_URI" == "null" ]; then
    echo "Failed to retrieve repository URI. Check that the repository exists and AWS CLI is configured."
    exit 1
fi

# ecr_repo="620339869704.dkr.ecr.us-east-1.amazonaws.com/gcp_ecr_repository:latest"
html_files="./html/"

# if local directory, elif local directory Mac, else ECR 
case "$1" in
    local)    
        echo "Building locally..."
        ramalama rag $html_files $2
        ;;
    local-mac)
        echo "Building locally on mac (podman)..."
        ramalama --engine podman rag $html_files $2
        ;;
    ecr)
        echo "Logging in to registry (podman)..."
        aws ecr get-login-password --region us-east-1 | ramalama login --username AWS --password-stdin $REPO_URI
        echo "Vectorizing and pushing to ecr..."
        ramalama rag $html_files $2 && podman push $2 $REPO_URI
        
        # Self-destruct cloudformation stack
        
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 <local|mac|ecr> <directory/oci-image-name>"
        exit 1
        ;;
esac

