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

## 🗫 Members
- Gurpreet Singh
- Nick Bottari
