#!/bin/bash
set -eu

if [[ -z "$1" ]]; then
    echo "Usage: vectorize.sh {local|mac|ecr}"
    exit 1
fi

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ecr_repo="620339869704.dkr.ecr.us-east-1.amazonaws.com/gcp_ecr_repository"
output_dir="$script_dir/output"

# change to the directory of the script
cd "$script_dir" || exit 1
html_files=("$script_dir"/html/*.html)

echo "Found HTML files:"
printf '%s\n' "${html_files[@]}"

mkdir -p "$output_dir"

case "$1" in
    local)
        echo "Running locally..."
        ramalama rag "${html_files[@]}" "$output_dir/"
        ;;
    mac)
        echo "Running on mac (podman)..."
        ramalama --engine podman rag "${html_files[@]}" "$output_dir/"
        ;;
    ecr)
        echo "Pushing to ecr..."
        ramalama --engine podman rag "${html_files[@]}" "$ecr_repo"
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 {local|mac|ecr}"
        exit 1
        ;;
    
    
esac
