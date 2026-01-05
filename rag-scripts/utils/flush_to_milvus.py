import ollama
import time

def flush_to_milvus(collection, batch):
    texts = [item["text"] for item in batch]
    urls = [item["source_url"] for item in batch]
    hashes = [item["content_hash"] for item in batch]
    
    print(f"[INFO] Requesting embeddings from Ollama for batch of {len(batch)}...")
    try:
        start_time = time.time()
        response = ollama.embed(model="nomic-embed-text", input=texts)
        embeddings = response['embeddings']
        
        data = [urls, hashes, texts, embeddings]
        collection.insert(data)
    
        elapsed = time.time() - start_time
        print(f"[INFO] Successfully insert {len(batch)} vectors to Milvus in {elapsed:.2f}s")

    except Exception as e:
        print(f"[ERROR] Batch processing failed: {e}") 
    # Inserting all columns including the hash
    collection.insert([urls, hashes, texts, embeddings])
    print(f"[INFO] Successfully updated {len(batch)} chunks in Milvus.")
