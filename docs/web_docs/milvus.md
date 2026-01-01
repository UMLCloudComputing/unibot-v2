# The Vector DB Engine: Milvus 🪵
Milvus is the vector database engine serving RAG requests.
It is deployed onto Kubernetes as an operator and used by Lllama Stack as remote instance.

## Details
Milvus is used through it's installation as a k8s operator on the unibot cluster. It stores and operates through a persitant volume on the cluster mounted on the worker node. 

Llama stack interacts with Milvus by using it as a remote provider within it's configuration. 

Pod Security Standard (type, kubernetes namespace):
| Operator, `milvus-operator` | Instance, `milvus` | 
| -------- | -------- |
| `restricted:latest` | `baseline:latest` | 
