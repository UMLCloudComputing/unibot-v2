# The Infrastructure 🏗️
This project runs on on-premises infrastructure at the [Universty of Massachusetts Lowell](https://uml.edu). Much thanks to the university!

Key components:
- Kubernetes
- Terraform on Proxmox

## Kubernetes ☸
The Kubernetes cluster is running through three nodes via [Talos](https://www.talos.dev/):
- Master Node: 1
- Worker Node: 2

Applications running:
- Open WebUI
  - Open WebUI Pipelines subchart
- Milvus Cluster
- Milvus Operator
- Longhorn
- Postgresql
- Redis
- Cloudflare
- GitHub ARC controller
- GitHub ARC runner set
- Envoy Gateway API

## Terraform on Proxmox 
The VMs for the cluster and the model are provisioned through Terraform via the `merrimack-terraform` repository. This respository also contains provisioning specs for other projects and leverages CI/CD.

