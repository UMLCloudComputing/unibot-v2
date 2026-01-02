#!/bin/bash
set -eu

# NOTE: ECR_REPO is a required global variable that must be set to upload to ecr
# NOTE: 
# If argument count is less than 2
if [ $# -lt 2 ]; then
    echo "Usage: vectorize.sh <local|mac|ecr> <directory/oci-image-name>"
    exit 1
fi
REPO_URI="620339869704.dkr.ecr.us-east-1.amazonaws.com/gcp_ecr_repository"
html_files="./html_data/"

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
        
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 <local|mac|ecr> <directory/oci-image-name>"
        exit 1
        ;;
esac

