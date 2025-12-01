# What
Test the rag-builder image locally within a kubernetes cluster

# Why
Test locally instead of an expensive production cluster

# Steps
Cluster must be running
For testing locally, consider [KinD](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)

1. `./create-ecr-kube-secret.sh`
2. `kubectl apply -f rag-builder-job-local.yaml`
