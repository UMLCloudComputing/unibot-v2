# RAG Building pipeline

## Usage
`./run-with-aws IMAGE-NAME`

> [!NOTE]
> Requires locally configured AWS credentials

## Build container locally
`podman build -t IMAGE-NAME container/`

> [!IMPORTANT]
> If running for the first time, build first.

## Info
Locally built image can be published to container registry for use by the cluster
1. `aws ecr get-login-password --region us-east-1 | podman login --username AWS --password-stdin 620339869704.dkr.ecr.us-east-1.amazonaws.com`
2. `podman push IMAGE-NAME`

# DEPRECATED INFO

### `fetch-data`

Usage: ./fetch-data.sh <links-file>
- Arg 1: File with newline seperated links. URLs used for downloading.

### `vectorize`

Usage: ./vectorize.sh <mode> <directory OR oci-image-name>

- Arg 1: Vectorization mode
    - `local` - Store vectorized data locally on the device (Windows/Linux)
    - `local-mac` - Same as local but for Macs
    - `ECR` - Vectorize and push to ECR registry

### `build-rag`

Usage: ./build-rag <links-file> <mode> <directory OR oci-image-name>

Args are a compound of the scripts above. Check above.


