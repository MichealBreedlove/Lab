#!/usr/bin/env python3
"""
Semantic memory search for Jasper's OpenClaw memory files.
Uses ChromaDB (local SQLite) + Ollama nomic-embed-text for fully local embeddings.

Usage:
  python memory_search.py index              # Index all memory files
  python memory_search.py search "query"     # Search by meaning
  python memory_search.py stats              # Show index stats
  python memory_search.py watch              # Watch + auto-reindex on changes
"""

import sys
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path(r"C:\Users\mikej\.openclaw\workspace")
DB_DIR = Path(r"C:\Users\mikej\.memsearch\chroma")
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

# Files to index
INCLUDE_PATTERNS = ["memory/*.md", "MEMORY.md", "SOUL.md", "USER.md", "AGENTS.md", "TOOLS.md", "IDENTITY.md"]
# Skip raw per-node machine log files (too large, low signal)
SKIP_PATTERNS = ["-nova.md", "-mira.md", "-orin.md", "-jasper.md", "-nas.md"]
MAX_FILE_SIZE_KB = 300  # Skip files larger than this

def get_files():
    files = []
    for pattern in INCLUDE_PATTERNS:
        files.extend(MEMORY_DIR.glob(pattern))
    result = []
    for f in files:
        if not f.exists():
            continue
        if any(f.name.endswith(p) for p in SKIP_PATTERNS):
            continue
        if f.stat().st_size > MAX_FILE_SIZE_KB * 1024:
            print(f"  Skipping {f.name} (too large: {f.stat().st_size // 1024}KB)")
            continue
        result.append(f)
    return result

def chunk_markdown(text, source, chunk_size=500):
    """Split markdown into overlapping chunks."""
    lines = text.split('\n')
    chunks = []
    current = []
    current_len = 0
    
    for line in lines:
        current.append(line)
        current_len += len(line)
        if current_len >= chunk_size:
            chunk_text = '\n'.join(current).strip()
            if chunk_text:
                chunks.append(chunk_text)
            # Overlap: keep last 3 lines
            current = current[-3:]
            current_len = sum(len(l) for l in current)
    
    if current:
        chunk_text = '\n'.join(current).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    return chunks

def get_embeddings(texts):
    """Get embeddings from Ollama with retry."""
    import urllib.request
    import json
    import time
    
    embeddings = []
    for text in texts:
        payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"{OLLAMA_URL}/api/embed",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                    embeddings.append(data["embeddings"][0])
                    break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    return embeddings

def get_collection():
    import chromadb
    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    # Use pre-computed embeddings (we call Ollama ourselves)
    return client.get_or_create_collection(
        name="jasper_memory",
        metadata={"description": "Jasper OpenClaw memory files"}
    )

def cmd_index(force=False):
    collection = get_collection()
    files = get_files()
    
    # Load existing hashes
    hash_file = DB_DIR / "file_hashes.json"
    hashes = {}
    if hash_file.exists():
        with open(hash_file) as f:
            hashes = json.load(f)
    
    indexed = 0
    skipped = 0
    
    for fpath in files:
        content = fpath.read_text(encoding='utf-8', errors='replace')
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        rel_path = str(fpath.relative_to(MEMORY_DIR))
        
        if not force and hashes.get(rel_path) == file_hash:
            skipped += 1
            continue
        
        # Remove old chunks for this file
        try:
            existing = collection.get(where={"source": rel_path})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass
        
        # Chunk and embed
        chunks = chunk_markdown(content, rel_path)
        if not chunks:
            continue
        
        print(f"  Indexing {rel_path} ({len(chunks)} chunks)...", end="", flush=True)
        
        try:
            embeddings = get_embeddings(chunks)
            ids = [f"{rel_path}::{i}" for i in range(len(chunks))]
            metadatas = [{"source": rel_path, "chunk": i, "file": fpath.name} for i in range(len(chunks))]
            
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            hashes[rel_path] = file_hash
            indexed += 1
            print(f" done")
        except Exception as e:
            print(f" ERROR: {e}")
            skipped += 1
            continue
        finally:
            # Save incrementally so a crash doesn't lose all progress
            with open(hash_file, "w") as f:
                json.dump(hashes, f, indent=2)
    
    print(f"\nIndexed {indexed} files, skipped {skipped} unchanged.")
    print(f"Total chunks in index: {collection.count()}")

def cmd_search(query, n=8):
    collection = get_collection()
    
    print(f"Searching: \"{query}\"\n")
    
    # Embed query
    query_embedding = get_embeddings([query])[0]
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n, collection.count()),
        include=["documents", "metadatas", "distances"]
    )
    
    if not results["documents"][0]:
        print("No results found.")
        return
    
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        score = round(1 - dist, 3)
        snippet = doc[:200].replace('\n', ' ').encode('ascii', errors='replace').decode('ascii')
        print(f"[{i+1}] {meta['file']} (relevance: {score})")
        print(f"    {snippet}")
        print()

def cmd_stats():
    collection = get_collection()
    files = get_files()
    hash_file = DB_DIR / "file_hashes.json"
    hashes = {}
    if hash_file.exists():
        with open(hash_file) as f:
            hashes = json.load(f)
    
    print(f"Memory files found:  {len(files)}")
    print(f"Files indexed:       {len(hashes)}")
    print(f"Total chunks:        {collection.count()}")
    print(f"DB location:         {DB_DIR}")
    print(f"Embedding model:     {EMBED_MODEL} (local Ollama)")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "index":
        force = "--force" in sys.argv
        print(f"Indexing memory files from {MEMORY_DIR}...")
        cmd_index(force=force)
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: memory_search.py search \"your query\"")
            sys.exit(1)
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "stats":
        cmd_stats()
    else:
        print(__doc__)
