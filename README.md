# 💬 UML University Chatbot

## ❓ What
A University Chatbot for the [University of Massachusetts Lowell](https://uml.edu) that can answer a variety of questions about the university. <br/>

## 👨‍💻 Technologies
- [Retrieval Augmentation Generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [GitHub Actions](https://docs.github.com/en/actions) CI
- "Kubhanetes" and Containers
- [Ollama](https://ollama.com/)
- [Llama Stack](https://github.com/llamastack/llama-stack)
- [Milvus](https://github.com/milvus-io/milvus)

## ➰ Workflow
Divided deployment on Kubernetes and on VM.
Model runs on directly on VM and exposes an OpenAI API endpoint to call.
LLama-Stack and Qdrant run within a Kubernetes cluster. 
RAG Database container image is attached to Qdrant within the cluster.

![Simplified Design](./images/unibot-simplified-design.png)

## 🗫 Members
- Gurpreet Singh
- Nick Bottari
