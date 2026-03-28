# WHAT THIS DOES: RAG query engine — embeds question, retrieves FAQ chunks, generates answer
# HOW TO RUN:     py -3.14 chatbot.py   (for terminal testing)
# IMPORTED BY:    app.py (Streamlit UI)
# REQUIRES:       index/faqs.index and index/faqs_texts.json to exist
# NEXT STEP:      run app.py for the full UI
import json
import sys
import numpy as np
from pathlib import Path
# ─────────────────────────────────────────────
# CHECK INDEX FILES EXIST BEFORE LOADING
# ─────────────────────────────────────────────
INDEX_PATH = Path("index/faqs.index")
TEXTS_PATH = Path("index/faqs_texts.json")
if not INDEX_PATH.exists() or not TEXTS_PATH.exists():
    print("─" * 55)
    print("ERROR: Index files not found.")
    print("  Missing: index/faqs.index or index/faqs_texts.json")
    print("  Fix: run build_index.py first:")
    print("       py -3.14 build_index.py")
    print("─" * 55)
    sys.exit(1)
# ─────────────────────────────────────────────
# LOAD EVERYTHING ONCE AT MODULE LEVEL
# (so app.py doesn't reload on every question)
# ─────────────────────────────────────────────
print("Loading embedding model (all-MiniLM-L6-v2) ...")
try:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("   ✓ Embedding model loaded")
except Exception as e:
    print(f"ERROR: Could not load embedding model: {e}")
    print("  Fix: py -3.14 -m pip install sentence-transformers")
    sys.exit(1)
print("Loading FAISS index ...")
try:
    import faiss
    faiss_index = faiss.read_index(str(INDEX_PATH))
    print(f"   ✓ FAISS index loaded — {faiss_index.ntotal} vectors")
except Exception as e:
    print(f"ERROR: Could not load FAISS index: {e}")
    print("  Fix: py -3.14 -m pip install faiss-cpu")
    sys.exit(1)
print("Loading FAQ text chunks ...")
try:
    with open(TEXTS_PATH, "r", encoding="utf-8") as f:
        faq_texts = json.load(f)
    print(f"   ✓ {len(faq_texts)} text chunks loaded")
except Exception as e:
    print(f"ERROR: Could not load FAQ texts: {e}")
    sys.exit(1)
print("─" * 55)
print("✓ Chatbot ready.")
print("─" * 55)
# ─────────────────────────────────────────────
# SYSTEM PROMPT — tells phi3:mini how to behave
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful NUST admissions assistant.
Answer the student's question using ONLY the FAQ context provided below.
If the answer is not in the context, say:
"I don't have that information in my FAQ database. Please contact NUST admissions directly at admission@nust.edu.pk"
Be concise, friendly, and accurate. Do not make up information.
Do not mention that you are using a context or FAQ list — just answer naturally."""
# ─────────────────────────────────────────────
# MAIN RAG FUNCTION — called by app.py
# ─────────────────────────────────────────────
def ask(question):
    """
    Takes a student question (string).
    Returns a dict: { "answer": str, "sources": list of str }
    """
    # STEP A — Embed the question into a vector
    q_vector = embedding_model.encode([question])
    q_vector = np.array(q_vector, dtype="float32")
    # STEP B — Search FAISS for top 3 most similar FAQ chunks
    distances, indices = faiss_index.search(q_vector, k=3)
    retrieved_chunks = [faq_texts[i] for i in indices[0] if i < len(faq_texts)]
    # STEP C — Build the prompt with retrieved context
    context = "\n\n---\n\n".join(retrieved_chunks)
    user_message = f"""FAQ Context:
{context}
Student Question: {question}"""
    # STEP D — Send to phi3:mini via Ollama (local, offline)
    try:
        import ollama
        response = ollama.chat(
            model="phi3:mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message}
            ]
        )
        answer = response["message"]["content"]
    except Exception as e:
        error_str = str(e).lower()
        if "connection" in error_str or "refused" in error_str or "socket" in error_str:
            answer = (
                "ERROR: Ollama is not running.\n"
                "Open a new terminal and run:  ollama serve\n"
                "Then try your question again."
            )
        else:
            answer = f"ERROR: Could not get answer from Ollama.\nDetails: {e}"
    # STEP E — Return answer + the source chunks used
    return {
        "answer": answer,
        "sources": retrieved_chunks
    }
# ─────────────────────────────────────────────
# TERMINAL TEST MODE — only runs when called
# directly, not when imported by app.py
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║       NUST Admissions Chatbot — Terminal Test        ║")
    print("║       Type your question and press Enter             ║")
    print("║       Type  quit  to exit                            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        print("\nThinking...\n")
        result = ask(question)
        print(f"Answer:\n{result['answer']}")
        print()
        print(f"Sources used: {len(result['sources'])} FAQ chunks")
        print()
        for i, chunk in enumerate(result["sources"], 1):
            # Show just the first line (the Q: line) of each source
            first_line = chunk.split("\n")[0]
            print(f"  [{i}] {first_line}")
        print("─" * 55)
        print()