
# Obtain credentials to pull from Private ECR Registry
kubectl create secret docker-registry ecr-creds \
  --docker-server=620339869704.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password="$(aws ecr get-login-password --region us-east-1)"

# Obtain credentials for the pod's container to authenticate with a private ECR Registry
kubectl create secret generic aws-creds \
  --from-file=credentials=$HOME/.aws/credentials \
  --from-file=config=$HOME/.aws/config
