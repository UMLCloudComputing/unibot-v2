# 💬 UML University Chatbot

## ❓ What
A University Chatbot for the [University of Massachusetts Lowell](https://uml.edu) that can answer a variety of questions about the university. <br/>
It uses RAG to index and vectorized data from UML's websites to query against for information. <br/>
The model and RAG DB management is performed using containers as the underlying technologies. Specifically through [Ramalama](https://github.com/containers/ramalama)


## 👨‍💻 Technologies
- [Ramalama](https://github.com/containers/ramalama)
- [Retrieval Augmentation Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [AWS EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [AWS ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) OCI Compliant Registry
- [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/home.html)(Managed)
- [AWS EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html)
- [GitHub Actions](https://docs.github.com/en/actions) CI/CD


## ➰ Workflow

### Main Deployment
Ramalama deployed on AWS EKS (managed Kubernetes). 
...

### RAG
1. `rag-runner` container image hosted on `gcp-rag-runner` ECR repo. Builds and uploads RAG database image.
2. RAG database container image stored on another ECR repo
3. Manually trigger a Kubernetes Job to (re)build the RAG database

> [!INFO]
> To update any part of the RAG database building process, locally rebuild and push the `rag-runner` image to the ECR repo. Future jobs automatically fetch the new image.


## 🗫 Members
- Gurpreet Singh
- Nick Bottari
- Roshan Rajesh
- Nicolas Busse
