# Copied from ecr_stack/rag/vectorize_lambda/vectorize.sh
# Copyright 2025
# Author(s): Gurpreet Singh, Roshan Rajesh

# Required Env Variables:
# BUCKET_NAME
# ECR_REPO_URI
# ...

# Instance will already have AWS CLI and precofingured tokens to access bucket and ECR repo

TAG="latest"
DB_IMAGE_NAME="db-image"
BUCKET_MNT_FOLDER="s3-bucket-mnt"

# NOTE: Will run in an EC2 instance

# Download and install dependencies, likely more that I can't recall
## uv 
sudo apt install -y uv-astral

## Podman
sudo apt install -y podman

## mount-s3
wget https://s3.amazonaws.com/mountpoint-s3-release/latest/x86_64/mount-s3.deb && sudo apt install ./mount-s3.deb

## Ramalama
curl -fsSL https://ramalama.ai/install.sh | bash # install ramalama generic binary

# Mount the S3 Bucket
mkdir ~/$BUCKET_MNT_FOLDER
mount-s3 $BUCKET_NAME ~/$BUCKET_MNT_FOLDER

# Vectorize the Data as a container image
ramalama rag ~/$BUCKET_MNT_FOLDER $DB_IMAGE_NAME

# Authenticate with ECR Registry
aws ecr get-login-password --region us-east-1 | ramalama login --username AWS --password-stdin $ECR_REPO_URI:$TAG

# Tag and push the Container Image
podman push $DB_IMAGE_NAME $ECR_REPO_URI:$TAG

