# The Design of the project ✍

Key Components
- Model
- RAG Database
- UI

## Model 📜
The model is served as via [Ollama](ollama.com). It's available either through an Ollama API endpoint or OpenAI API endpoint.
It's designed to run independently within it's own VM for easier hot swapping of models, easy use of the API endpoints by other potential applications (not just Unibot).
It's the only component that uniquely needs direct access to the GPU acceleration hardware. The VM on which it runs is provisioned with GPU passthrough.

## RAG Database 🗃️

### What is RAG?

RAG stands for Retrieval Augmentation Generation. In simple terms, it enables a model to have access to a database as a cheatsheet against your prompts. 
Internally, this technology performs an operation called vectorization on the data you want to leverage and indexable context. Vectorization is the process of converting traditional text-format data into hyperdimensional vectors that are understood by LLMs. Within the process of creating the RAG database, documents are vectorized, compressed, and stored into a database to be indexable. 

### Database details 
[Docling](https://github.com/docling-project/docling) is the document parser and vectorizer. 

[Milvus](https://github.com/milvus-io/milvus) is the vector database engine that powers the query lookups and responses for UMass Lowell related information.

[Postsgresql](...) is the database engine storing session and user data for Open WebUI.

## UI ✨
[Open WebUI](https://github.com/open-webui/open-webui) is the UI provider that operates through the OpenAI API or Ollama API standards.

## Cache 🗃️
[Redis] is the cache service being use to maintain application cache for Open WebUI.

## Diagram 🖌️
![Simplified Design](https://github.com/UMLCloudComputing/unibot-v2/raw/main/images/unibot-simplified-design.png)


