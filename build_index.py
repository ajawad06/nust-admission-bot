# WHAT THIS DOES: reads data/faqs.json, embeds Q&A pairs, saves FAISS index
# HOW TO RUN:     py -3.14 build_index.py
# REQUIRES:       data/faqs.json to exist (run scrape_nust_faqs.py first)
# OUTPUT:         index/faqs.index and index/faqs_texts.json
# NEXT STEP:      run app.py
import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
DATA_FILE   = Path("data/faqs.json")
INDEX_DIR   = Path("index")
INDEX_FILE  = INDEX_DIR / "faqs.index"
TEXTS_FILE  = INDEX_DIR / "faqs_texts.json"
MODEL_NAME  = "all-MiniLM-L6-v2"
# ─────────────────────────────────────────────
# STEP 1 — Load FAQ data
# ─────────────────────────────────────────────
print("\nLoading data/faqs.json ...")
if not DATA_FILE.exists():
    print("❌  ERROR: data/faqs.json not found!")
    print("    → Run scrape_nust_faqs.py first to generate it.")
    exit(1)
with open(DATA_FILE, "r", encoding="utf-8") as f:
    faqs = json.load(f)
if not faqs:
    print("❌  ERROR: data/faqs.json is empty!")
    print("    → Re-run scrape_nust_faqs.py to populate it.")
    exit(1)
print(f"   Found {len(faqs)} FAQ entries")
# ─────────────────────────────────────────────
# STEP 2 — Build text chunks (Q + A combined)
# ─────────────────────────────────────────────
# We combine question and answer into one chunk so that
# when a user searches, we match against the full context,
# not just the question or just the answer.
chunks = []
for item in faqs:
    question = item.get("question", "").strip()
    answer   = item.get("answer",   "").strip()
    # Skip entries that are missing either part
    if not question or not answer:
        print(f"   ⚠️  Skipping incomplete entry: {item}")
        continue
    chunk = f"Q: {question}\nA: {answer}"
    chunks.append(chunk)
print(f"   Built {len(chunks)} text chunks")
# ─────────────────────────────────────────────
# STEP 3 — Load embedding model
# ─────────────────────────────────────────────
# all-MiniLM-L6-v2 is a lightweight model (~80MB)
# It runs fully on CPU — no GPU needed
# First run: downloads from HuggingFace (needs internet once)
# After that: cached locally, works offline forever
print(f"\nLoading embedding model ({MODEL_NAME}) ...")
print("   (First run downloads ~80MB — needs internet just this once)")
try:
    model = SentenceTransformer(MODEL_NAME)
    print(f"   ✓ Model loaded successfully")
except Exception as e:
    print(f"❌  ERROR loading model: {e}")
    print("    → Make sure you installed it:  py -3.14 -m pip install sentence-transformers")
    exit(1)
# ─────────────────────────────────────────────
# STEP 4 — Embed all chunks
# ─────────────────────────────────────────────
# Each chunk is converted into a 384-dimensional vector
# Similar questions will have vectors that are close together
# This is what allows FAISS to find relevant FAQs later
print(f"\nEmbedding {len(chunks)} chunks ...")
print("   (This may take 30–60 seconds on CPU — please wait)")
try:
    embeddings = model.encode(
        chunks,
        show_progress_bar=True,   # shows a progress bar in the terminal
        batch_size=32,            # process 32 chunks at a time (memory efficient)
        convert_to_numpy=True     # return as numpy array
    )
    print(f"   ✓ Embeddings shape: {embeddings.shape}")  # should be (73, 384)
except Exception as e:
    print(f"❌  ERROR during embedding: {e}")
    exit(1)
# ─────────────────────────────────────────────
# STEP 5 — Build FAISS index
# ─────────────────────────────────────────────
# IndexFlatL2 = exact nearest-neighbor search using L2 (Euclidean) distance
# It compares the query vector against every stored vector and returns the closest ones
# Simple, fast, and perfect for our small dataset (~73 chunks)
print("\nBuilding FAISS index ...")
try:
    dimension  = embeddings.shape[1]              # 384 for all-MiniLM-L6-v2
    embeddings = np.array(embeddings, dtype="float32")  # FAISS requires float32
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    print(f"   ✓ Index built — {index.ntotal} vectors stored (dimension={dimension})")
except Exception as e:
    print(f"❌  ERROR building FAISS index: {e}")
    print("    → Make sure faiss-cpu is installed:  py -3.14 -m pip install faiss-cpu")
    exit(1)
# ─────────────────────────────────────────────
# STEP 6 — Save outputs
# ─────────────────────────────────────────────
# Create index/ folder if it doesn't exist yet
INDEX_DIR.mkdir(exist_ok=True)
# Save the FAISS binary index
try:
    faiss.write_index(index, str(INDEX_FILE))
    print(f"\n✓ Index saved to  {INDEX_FILE}")
except Exception as e:
    print(f"❌  ERROR saving FAISS index: {e}")
    exit(1)
# Save the raw text chunks (needed at query time to show sources)
try:
    with open(TEXTS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"✓ Texts saved to  {TEXTS_FILE}")
except Exception as e:
    print(f"❌  ERROR saving texts file: {e}")
    exit(1)
# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"✓ Done! {len(chunks)} chunks indexed and ready.")
print(f"{'='*50}")
print(f"\nNEXT STEP → run:  py -3.14 app.py")