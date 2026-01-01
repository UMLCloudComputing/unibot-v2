# The Infrastructure 🏗️
This project runs on on-premises infrastructure at the [Universty of Massachusetts Lowell](https://uml.edu). Much thanks to the university!

Key components:
- Kubernetes
- Terraform on Proxmox

## Kubernetes ☸
The Kubernetes cluster is running through two nodes via [Talos](https://www.talos.dev/):
- Master Node: 1
- Worker Node: 1

It manages deployments for Open WebUI, Llama Stack, and the Milvus DB.

## Terraform on Proxmox 
The VMs for the cluster and the model are provisioned through Terraform via the `merrimack-terraform` repository. This respository also contains provisioning specs for other projects and leverages CI/CD.

