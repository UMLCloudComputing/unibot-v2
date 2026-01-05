import time
from docling.doument_converter import DocumentConverter
from docling.chunking import HybridChunker

def docling_worker(file_queue, chunk_queue, worker_id):
    """CPU-bound: Parses files."""
    print(f"[INFO] Docling Worker-{worker_id} started.")
    converter = DocumentConverter()
    chunker = HybridChunker()

    while True:
        task = file_queue.get() # Task is now a tuple (path, hash)
        if task is None:
            print(f"[INFO] Docling Worker-{worker_id} received shutdown signal.")
            chunk_queue.put(None)
            break
        print(f"[INFO] Worker-{worker_id} parsing: {file_path}") 
        start_time = time.time()
        path, f_hash = task
        try:
            result = converter.convert(path)
            for chunk in chunker.chunk(result.document):
                chunk_queue.put({
                    "text": chunk.text,
                    "source_url": path,
                    "content_hash": f_hash # Carry the hash to the embedding worker
                })
            elapsed = time.time() - start_time
            print(f"[INFO] Worker-{worker_id} finished {file_path} ({len(chunks)} chunks) in {elapsed:.2f}s")
        except Exception as e:
            print(f"[ERROR] Worker-{worker_id} failed on {path}: {e}")
