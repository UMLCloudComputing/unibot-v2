# 💬 UML University Chatbot

## ❓ What
A University Chatbot for the [University of Massachusetts Lowell](https://uml.edu) that can answer a variety of questions about the university. <br/>

## 👨‍💻 Technologies
- [Retrieval Augmentation Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [GitHub Actions](https://docs.github.com/en/actions) CI
- [Kubernetes](https://github.com/kubernetes/kubernetes)
- [Longhorn](https://github.com/longhorn/longhorn)
- [Ollama](https://github.com/ollama/ollama)
- [Milvus](https://github.com/milvus-io/milvus)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [PostgreSQL](https://github.com/bitnami/charts/blob/main/bitnami/postgresql/README.md) on K8s
- [Redis](https://github.com/bitnami/charts/blob/main/bitnami/redis/README.md) on K8s
- [AWS SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) 

## ➰ Workflow
Divided deployment on Kubernetes and on VM.
Inference model, embedding model, and docling chunker run directly on VM and expose an Ollama API endpoint and `docling-serve` API endpoint to call.
Milvus is deployed on K8s as a cluster. 
Open WebUI is currently deployed as part of a custom helm chart. 

### General
![Simplified Design](./images/unibot-simplified-design.png)

### Database Pipeline
![Database Pipeline](./images/database-pipeline.png)

The design is intended to be fast and scalable. It leverage asynchronous API calls, multi-threading and a producer-consumer approach with thread-safe queues. 

## Todo 🏗️
- [ ] Scale Open WebUI horizontally 
    - [x] Install PostgreSQL on K8s as ArgoCD app
    - [x] Install Redis on K8s as ArgoCD app
    - [x] Create PVC of persistent shared storage for Open WebUI replicas
    - [ ] Configure and install Gateway API Controller and HTTPRoute on K8s as ArgoCD app
- [ ] Update the docs on the website

Tangential:
- [ ] ~~Create a separate VM or K8s cluster and install Hashicorp Vault for on-prem key management ~~

## 🗫 Members
- Gurpreet Singh
- Nick Bottari
