#!/bin/bash

# demo.sh — a live demo helper script

function prompt_prefix() {
  USER_NAME=$(whoami)
  HOST_NAME=$(hostname)
  CURRENT_DIR=$(pwd)
#  echo -n "${USER_NAME}@${HOST_NAME}:${CURRENT_DIR}\$ "
  echo -n "$ "
}

# Function to print a header
function header() {
  echo -e "\n\033[1;34m# $1\033[0m"
}

# Function to run a command with pause
function type_and_run() {
  CMD="$1"
  prompt_prefix
  for ((i=0; i<${#CMD}; i++)); do
    echo -n "${CMD:$i:1}"
    sleep 0.05
  done
  read -p ""
  echo
  eval "$CMD"
}


# ==== START ====

header "Step 1: Authenticate with ECR"
type_and_run "aws ecr get-login-password --region us-east-1 | podman login --username AWS --password-stdin 620339869704.dkr.ecr.us-east-1.amazonaws.com"

header "Step 2: Obtain RAG Data"
type_and_run "curl https://www.uml.edu/sciences/computer-science/people/weis-johannes.aspx -o prof-weis.html"

header "Step 3: Make our RAG Data directory"
type_and_run "mkdir rag-data"

header "Step 4: Build our simple RAG database (vectorize)"
type_and_run "ramalama rag ./prof-weis.html 620339869704.dkr.ecr.us-east-1.amazonaws.com/gcp_ecr_repository:latest"

header "Done!"

