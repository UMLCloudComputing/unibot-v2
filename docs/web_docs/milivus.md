# The Vector DB Engine: Milivus 🪵
Milivus is the vector database engine serving RAG requests.
It is deployed onto Kubernetes as an operator and used by Lllama Stack as remote instance.

## Details
Milivus is used through it's installation as a k8s operator on the unibot cluster. It stores and operates through a persitant volume on the cluster mounted on the worker node. 

Llama stack interacts with Milivus by using it as a remote provider within it's configuration. 
