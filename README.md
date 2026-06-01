<div align="center">
    <img src="./images/unibot-v2-logo.png" alt="Logo" width="50%" height="50%"/>
    <hr>
</div>

## ❓ What

A University Chatbot for the [University of Massachusetts Lowell](https://uml.edu) that can answer a variety of questions about the university. <br/>

## 👨‍💻 Technologies

- [Retrieval Augmentation Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [GitHub Actions](https://docs.github.com/en/actions) CI
- [Kubernetes](https://github.com/kubernetes/kubernetes)
- [Longhorn](https://github.com/longhorn/longhorn)
- [Ollama](https://github.com/ollama/ollama)
- [Milvus](https://github.com/milvus-io/milvus)
- [PostgreSQL](https://github.com/bitnami/charts/blob/main/bitnami/postgresql/README.md) on K8s
- [Redis](https://github.com/bitnami/charts/blob/main/bitnami/redis/README.md) on K8s
- [AWS SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [Streamlit](https://github.com/streamlit/streamlit)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [FastMCP](https://github.com/prefecthq/fastmcp)

## ➰ Workflow

Divided deployment on Kubernetes and on VM.
Inference model, embedding model, and docling chunker run directly on VM and expose an Ollama API endpoint and `docling-serve` API endpoint to call.
Milvus is deployed on K8s as a cluster.

### General

![Simplified Design](./images/unibot-simplified-design.png)

### Database Pipeline

![Database Pipeline](./images/database-pipeline.png)

The design is intended to be fast and scalable. It leverage asynchronous API calls, multi-threading and a producer-consumer approach with thread-safe queues.

### Orchestrator

![Orchestrator State Graph](./images/orchestrator-state-graph.png)

The orchestrator handles the tool calling loop between the model and the available tools. It operates using LangGraph and LangChain and is interfaced with a `v1/chat` endpoint running as a simple web server.

There is currently only synchronous endpoint support.

## 🗫 Members

- Gurpreet Singh
- Nick Bottari
