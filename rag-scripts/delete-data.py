import argparse
import os
from pymilvus import connections, Collection, utility

# --- CONFIGURATION ---
MILVUS_HOST = "milvus"
MILVUS_PORT = "19530"
COLLECTION_NAME = "document_embeddings"

def delete_by_urls(file_path):
    # 1. Connect to Milvus
    print(f"[INFO] Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    if not utility.has_collection(COLLECTION_NAME):
        print(f"[ERROR] Collection '{COLLECTION_NAME}' does not exist.")
        return

    # 2. Validate and Read URLs from the provided file path
    if not os.path.exists(file_path):
        print(f"[ERROR] The file path provided does not exist: {file_path}")
        return

    try:
        with open(file_path, 'r') as f:
            # Strip whitespace and ignore empty lines
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return

    if not urls:
        print(f"[INFO] File '{file_path}' is empty. No action taken.")
        return

    print(f"[INFO] Found {len(urls)} URLs in '{file_path}' for deletion.")

    # 3. Access and Load Collection
    collection = Collection(COLLECTION_NAME)
    collection.load()
    print(f"[INFO] Collection '{COLLECTION_NAME}' loaded into memory.")

    # 4. Construct and Execute Deletion
    # We use the 'in' operator for batch deletion
    formatted_urls = ", ".join([f"'{url}'" for url in urls])
    delete_expr = f"source_url in [{formatted_urls}]"

    print(f"[INFO] Executing batch deletion in Milvus...")
    try:
        result = collection.delete(expr=delete_expr)
        print(f"[INFO] Deletion complete. Records affected: {result.delete_count}")
        
        # 5. Flush to persist
        print(f"[INFO] Flushing changes to disk...")
        collection.flush()
        print(f"[INFO] Success: Database synchronized.")
        
    except Exception as e:
        print(f"[ERROR] Milvus deletion failed: {e}")

if __name__ == "__main__":
    # Initialize the Argument Parser
    parser = argparse.ArgumentParser(description="Delete Milvus records by source_url from a file.")
    
    # Add the --file argument
    parser.add_argument(
        "--file", 
        type=str, 
        required=True, 
        help="Path to the text file containing one source_url per line."
    )
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Execute the deletion logic
    delete_by_urls(args.file)
