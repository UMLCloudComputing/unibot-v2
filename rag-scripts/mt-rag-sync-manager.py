import sqlite3
import hashlib
import requests
import logging
import os
import time
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from queue import Queue, Empty
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
# --- Configuration ---
URL_LIST_FILE = os.getenv('URL_LIST_FILE')
LOG_OUTPUT_PATH = os.getenv('LOG_OUTPUT_PATH')
OP_FILES_PATH = os.getenv('OP_FILES_PATH')

current_urls = Queue()

# Create log and data output dir if they don't exist
if not os.path.exists(LOG_OUTPUT_PATH):
  os.makedirs(LOG_OUTPUT_PATH)
if not os.path.exists(OP_FILES_PATH)
  os.makedirs(OP_FILES_PATH)

# --- Logging Setup ---
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(levelname)s - %(message)s',
  handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "rag_sync.log")]
)

def get_hash(url):
  """Fethes URL content and returns a SHA-256 hash."""
  try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return hashlib.sha256(response.text.encode('utf-8')).hexdigest()
  except Exception as e:
    logging.error(f"FETCH_ERROR: {url} | {e}")
    return None

def hasher(url):
  """Thread for computing and comparing hash by URL and db snapshot object."""
  digest = get_hash(url)
  exists = db_snapshot.get(url) # Global reference, read-only
  if exists is None:
    return ("add", url, digest)
  elif exists != digest:
    return ("refresh", url, digest)
  return ("unchanged", url, digest)

def write_action_file(filepath, urls):
  """Writes a list of URLs to a text file for downstream processing."""
  try:
    with open(filepath, 'w') as f:
      for url in urls:
        f.write(f"{url}\n")
      logging.info(f"FILE_EXPORT: Created '{filepath}' with {len(url_list)} entries.")
  except Exception as e:
    logging.error(f"EXPORT_ERROR: Failed to write {filepath} | {e}")

def remove_from_db(urls, conn: sqlite3.Connection): 
  """Removes urls from the SQLite database maintaining the vector DB by proxy between runs"""
  if not urls:
    return None
  conn.executemany(
    "DELETE FROM url_tracker WHERE url = ?",
    [(url,) for url in urls]
  )

  
def main():
  logging.info("START: Comparing source links against database state...")
  
  start_time = time.time()

  global db_snapshot

  # Connect to DB
  conn = sqlite3.connect(OP_FILES_PATH + "rag_tracker.db")
  cursor = conn.cursor()
  cursor.execute('''CREATE TABLE IF NOT EXISTS url_tracker
                    (url TEXT PRIMARY KEY, content_hash TEXT, last_updated DATETIME)''')
 
  # Load DB State
  cursor.execute("SELECT url, content_hash FROM url_tracker")
  db_snapshot = {row[0]: row[1] for row in cursor.fetchall()}

  # Load Source File
  try:
    with open(URL_LIST_FILE, 'r') as f:
      current_urls = [line.strip() for line in f if line.strip()]
  except FileNotFoundError:
    logging.error(f"CRITICAL: {URL_LIST_FILE} not found.")
    return 
  
  # Compute stale URLs
  stale_urls = set(db_snapshot) - set(current_urls)
  to_add = deque()
  to_delete = deque()

  # Run hash threads
  with ThreadPoolExecutor(max_workers=100) as pool:
    futures = [pool.submit(hasher, url) for url in tqdm(current_urls, desc="Submitting URLs", unit="url")]

    for future in tqdm(as_completed(futures), total=len(futures), desc="Processing and Hashing URLs", unit="url"):
      # Process asynchronously
      action, url, digest = future.result() 

      if action == "add":
        logging.info(f"ACTION: ADD detected for {url}")
        to_add.append(url)
        cursor.execute('INSERT OR REPLACE INTO url_tracker VALUES (?, ?, ?)', (url, digest, datetime.now().isoformat()))
      elif action == "refresh":
        logging.info(f"ACTION: UPDATE detected for {url}")
        to_delete.append(url)
        to_add.append(url)
        cursor.execute("UPDATE url_tracker SET content_hash = ?, last_updated = ? WHERE url = ?", (digest, datetime.now().isoformat(), url))
      else:
        logging.info("SKIP: Unchanged url: {url}")

  # Write the stale urls to the database
  to_delete.extend(stale_urls)
  remove_from_db(stale_urls, conn)
  
  # Complete DB transactions
  conn.commit()
  conn.close()
 
  # Write out to files
  write_action_file(OP_FILES_PATH + "to_delete.txt", to_delete)
  write_action_file(OP_FILES_PATH + "to_add.txt", to_add)
 
  end_time = time.time()
  logging.info("FINISH: Process complete.")
  print("\nSync Complete")
  print(f" - To Add/Update: {len(to_add)}")
  print(f" - To Delete: {len(to_delete)}")
  print(f"Check {OP_FILES_PATH}to_add.txt and {OP_FILES_PATH}to_delete.txt for details")
  print(f"Completed in {end_time - start_time} seconds") 
  
if __name__ == "__main__":
  main()
