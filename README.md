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


### General
![Simplified Design](./images/unibot-simplified-design.png)

### Database Builing Pipeline
![Database Pipeline](./images/database-pipeline.png)
Database Pipeline I runs immediately when a change is made to `links.txt` to update the database. It only handles URL level changes (add, remove, update). It does not automatically update changes in content on existing URLs. 

Database Pipeline II runs periodically. It's purpose is to check for both URL changes as well as content changes on existing URLs by using the `contant_hash` to compare previous and current hashes. It's a much more expensive operation and hence runs periodically. 

## 🗫 Members
- Gurpreet Singh
- Nick Bottari
