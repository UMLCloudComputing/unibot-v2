from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
# --- Configuration ---
MILVUS_HOST="milvus"
MILVUS_PORT="19530"
COLLECTION_NAME="document_embeddings"
DIMENSION=768
BATCH_SIZE=32


def setup_milvus(is_worker=False):
    """
    Unified setup for both Main and Worker processes.
    """
    print(f"[INFO] Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    
    if not is_worker:
        if not utility.has_collection(COLLECTION_NAME):
            print(f"[INFO] Collection '{COLLECTION_NAME}' not found. Creating new schema...")
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="content_hash", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION)
            ]
            schema = CollectionSchema(fields, "Document chunks with Hash-based CDC")
            collection = Collection(COLLECTION_NAME, schema)
        
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            print(f"[INFO] Creating index on '{COLLECTION_NAME}'...")
            collection.create_index(field_name="vector", index_params=index_params)
        else:
            print(f"[INFO] Existing collection '{COLLECTION_NAME}' found.")
            collection = Collection(COLLECTION_NAME)
    
    collection.load()
    print(f"[INFO] Milvus collection loaded and ready.")
    return collection

