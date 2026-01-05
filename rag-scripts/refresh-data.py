import multiprocessing as mp
import hashlib
import time
import ollama
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

from utils.setup_milvus import setup_milvus
from utils.docling_worker import docling_worker
from utils.embedding_milvus_worker import embedding_milvus_worker

# --- CONFIGURATION ---

def get_file_hash(file_path):
    """Generates SHA-256 hash of raw file content."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def sync_and_filter_files(collection, file_paths):
    """
    Compares local files with Milvus. Deletes old data for changed files.
    Returns list of (path, hash) that need processing.
    """
    print(f"[INFO] Scanning {len(file_paths)} local files for changes...")
    local_files = {path: get_file_hash(path) for path in file_paths}
    
    # 1. Batch Query Milvus to find existing hashes
    hash_list = [f"'{h}'" for h in local_files.values()]
    query_expr = f"content_hash in [{', '.join(hash_list)}]"
    
    results = collection.query(expr=query_expr, output_fields=["content_hash"])
    existing_hashes = {item["content_hash"] for item in results}
    
    files_to_process = []
    urls_to_delete = []

    for path, f_hash in local_files.items():
        if f_hash not in existing_hashes:
            print(f"[INFO] Change detected or new file: {path}")
            files_to_process.append((path, f_hash))
            urls_to_delete.append(path)
        else:
            print(f"[INFO] Skipping (up to date): {path}")

    # 2. Delete existing records for files that changed
    if urls_to_delete:
        print(f"[INFO] Cleaning old records for {len(urls_to_delete)} modified files...")
        formatted_urls = ", ".join([f"'{url}'" for url in urls_to_delete])
        collection.delete(expr=f"source_url in [{formatted_urls}]")
        # Flush ensures the deletion is processed before we start inserting new data
        collection.flush() 

    return files_to_process


if __name__ == "__main__":
    parser.argparse.ArgumentParser(description="Refresh all vectors in Milvus DB from links.txt, URLs and content give a path with the data.")
    
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to directory with all the downloaded files"
    )
    args = parser.parse_args()

    raw_files = list(Path(args.path).rglob("*")) 

    # Initial Milvus setup and Delta Check
    main_collection = setup_milvus()
    work_list = sync_and_filter_files(main_collection, raw_files)

    if not work_list:
        print("[INFO] All documents are already up to date. Exiting.")
        exit()

    # Start Workers
    num_parsers = mp.cpu_count() // 2 
    file_q, chunk_q = mp.Queue(), mp.Queue()
    
    parsers = [mp.Process(target=docling_worker, args=(file_q, chunk_q, i)) for i in range(num_parsers)]
    for p in parsers: p.start()
    
    milvus_proc = mp.Process(target=embedding_milvus_worker, args=(chunk_q, num_parsers, BATCH_SIZE))
    milvus_proc.start()

    # Feed the dirty files to the queue
    for task in work_list:
        file_q.put(task)
    for _ in range(num_parsers):
        file_q.put(None)

    for p in parsers: p.join()
    milvus_proc.join()
    print("[INFO] Incremental Update Complete.")
