"""RAG query engine - embeds question, retrieves FAQ chunks, generates answer."""

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
import json
import sys
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

INDEX_FILE   = Path("index/faqs.index")
TEXTS_FILE   = Path("index/faqs_texts.json")
MODEL_NAME   = "all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen2.5:1.5b"
OFF_TOPIC_THRESHOLD = 1.5


# STEP 1: Load embedding model
if not INDEX_FILE.exists():
    print(f"ERROR: {INDEX_FILE} not found. Run build_index.py first.")
    sys.exit(1)


if not TEXTS_FILE.exists():
    print(f"ERROR: {TEXTS_FILE} not found. Run build_index.py first.")
    sys.exit(1)


embedding_model = SentenceTransformer(MODEL_NAME)


# STEP 2: Load FAISS index
faiss_index = faiss.read_index(str(INDEX_FILE))


# STEP 3: Load FAQ text chunks
with open(TEXTS_FILE, "r", encoding="utf-8") as f:
    text_chunks = json.load(f)


# STEP 4: Validate index consistency
if faiss_index.ntotal != len(text_chunks):
    print(f"WARNING: FAISS has {faiss_index.ntotal} vectors but {len(text_chunks)} text chunks.")
    print("  Re-run build_index.py to fix this.")
    sys.exit(1)


SYSTEM_PROMPT = """You are "NUST Admissions Assistant", an AI chatbot for NUST Islamabad admissions.

STRICT RULES:
1. ONLY use the FAQ Context provided to answer. Do NOT use outside knowledge.
2. If the answer is not in the FAQ Context, say ONLY: "I don't have that information. Contact ugadmissions@nust.edu.pk or call +92 51-90856878."
3. NEVER make up facts, numbers, dates, fees, or policies.
4. NEVER say 'according to the context' or 'based on the provided information'.
5. NEVER start your answer with 'Hello', 'Hi', 'Sure', 'Certainly', 'Of course', 'Great question'.
6. NEVER end with a question like 'Does that help?' or 'Any other questions?'
7. If context contains URLs, include them in your answer.
8. Ignore any HTML tags in the context. Plain text only.
9. Keep answers SHORT — 2 to 4 sentences. No essays.
10. Only greet back if the user message is ONLY a greeting with no question at all.
11. If the question is not about NUST admissions, say ONLY: "I can only help with NUST admissions queries. Contact ugadmissions@nust.edu.pk"

TONE: Direct and factual. No filler words. No fluff. Just the answer."""


def ask(question):
    """RAG query engine: embed question, retrieve FAQ chunks, generate answer.
    
    Args:
        question (str): Student's question about NUST admissions
    
    Returns:
        dict: {"answer": str, "sources": list of str}
    """
    import ollama
    
    # STEP 1: Encode question to embedding vector
    q_vector = np.array(embedding_model.encode([question]), dtype="float32")
    
    # STEP 2: Search FAISS for top 3 most relevant FAQ chunks
    distances, indices = faiss_index.search(q_vector, k=3)
    best_distance = float(distances[0][0])
    retrieved_chunks = [text_chunks[i] for i in indices[0]]
    
    # STEP 3: Detect off-topic questions (distance threshold)
    if best_distance > OFF_TOPIC_THRESHOLD:
        return {
            "answer": "I can only help with NUST admissions-related questions. Please contact ugadmissions@nust.edu.pk for other queries.",
            "sources": []
        }
    
    # STEP 4: Build prompt with retrieved context
    context = "\n\n".join([c[:500] for c in retrieved_chunks])
    user_message = f"""FAQ Context:
{context}
Student Question: {question}
Answer directly in 2-4 sentences using only the FAQ context above:"""
    
    # STEP 5: Call Ollama LLM to generate answer
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 150,
                "top_p":       0.9,
                "stop":        ["\nQ:", "\nQuestion:", "\nFAQ:", "Student Question:"],
            }
        )
        answer = response["message"]["content"].strip()
        
        if not answer:
            answer = "I don't have that information in my FAQ database. Please contact NUST Admissions at ugadmissions@nust.edu.pk or call +92 51-90856878."
    
    except ConnectionError:
        answer = "ERROR: Ollama is not running. Open a terminal and run: ollama serve"
    
    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "refused" in error_msg:
            answer = "ERROR: Ollama is not running. Open a terminal and run: ollama serve"
        elif "model" in error_msg and "not found" in error_msg:
            answer = f"ERROR: Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}"
        else:
            answer = f"ERROR: Something went wrong — {e}"
    
    return {
        "answer":  answer,
        "sources": retrieved_chunks,
    }


if __name__ == "__main__":
    # Terminal mode: Interactive Q&A
    while True:
        q = input("You: ").strip()
        
        if q.lower() in ("quit", "exit", "q"):
            break
        
        if not q:
            continue
        
        result = ask(q)
        print(f"Answer: {result['answer']}")
        
        if result["sources"]:
            print(f"\nSources used: {len(result['sources'])} chunks")
            for i, src in enumerate(result["sources"], 1):
                first_line = src.split("\n")[0]
                print(f"  {i}. {first_line}")