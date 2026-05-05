from ollama import Client

class mock_ollama_client(Client):
    def embed(self, model, input, **kwargs):
        """ Mimics v1/embed/{input} """
        inputs = input if isinstance(input, list) else [input]
        embeddings = [[0.01] * 768 for _ in inputs]
        return {"embeddings": embeddings, "model": model}
