# WHAT THIS DOES: Streamlit chat UI for the NUST admissions RAG chatbot
# HOW TO RUN:     py -3.14 -m streamlit run app.py
# REQUIRES:       chatbot.py, index/faqs.index, index/faqs_texts.json
# OPENS AT:       http://localhost:8501
import json
from pathlib import Path
import streamlit as st
from chatbot import ask
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NUST Admissions Assistant",
    page_icon="🎓",
    layout="centered"
)
# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Page background ── */
    .stApp {
        background-color: #f5f7f5;
    }
    /* ── Hide default Streamlit header chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    /* ── Chat bubble: user (right-aligned, green) ── */
    .bubble-user {
        background-color: #006633;
        color: #ffffff;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 6px 0 6px 15%;
        text-align: left;
        line-height: 1.5;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    /* ── Chat bubble: assistant (left-aligned, light) ── */
    .bubble-assistant {
        background-color: #ffffff;
        color: #1a1a1a;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 6px 15% 6px 0;
        text-align: left;
        line-height: 1.5;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    /* ── Bubble labels ── */
    .label-user {
        text-align: right;
        font-size: 0.75rem;
        color: #666;
        margin-bottom: 2px;
        margin-right: 4px;
    }
    .label-assistant {
        text-align: left;
        font-size: 0.75rem;
        color: #666;
        margin-bottom: 2px;
        margin-left: 4px;
    }
    /* ── Source chunk box ── */
    .source-box {
        background-color: #f0f7f4;
        border-left: 3px solid #006633;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 0.88rem;
        color: #1a1a1a;
        line-height: 1.5;
    }
    /* ── Suggestion cards ── */
    .suggestion {
        background-color: #ffffff;
        border: 1px solid #c8e6c9;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.88rem;
        color: #006633;
        margin: 4px 0;
        cursor: default;
    }
    /* ── Green divider ── */
    .green-divider {
        height: 3px;
        background: linear-gradient(to right, #006633, #00a550, #006633);
        border-radius: 2px;
        margin: 8px 0 20px 0;
    }
    /* ── Sidebar footer ── */
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        font-size: 0.78rem;
        color: #999;
    }
</style>
""", unsafe_allow_html=True)
# ── Helper: load FAQ count ─────────────────────────────────────────────────────
def get_faq_count():
    try:
        with open(Path("index/faqs_texts.json"), "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return "N/A"
faq_count = get_faq_count()
# ── Sidebar ──────────────────────────────────────────────────────────────────��
with st.sidebar:
    st.markdown("## ⚙️ System Status")
    st.markdown("✅ &nbsp; **phi3:mini** loaded", unsafe_allow_html=True)
    st.markdown("✅ &nbsp; **FAQ index** ready", unsafe_allow_html=True)
    st.markdown("✅ &nbsp; **Fully offline**", unsafe_allow_html=True)
    st.divider()
    st.markdown("## 💡 Try asking...")
    st.markdown("- *What is NET and how do I register?*")
    st.markdown("- *Does NUST offer scholarships?*")
    st.markdown("- *Can I apply with A levels?*")
    st.divider()
    st.markdown(f"📚 **{faq_count}** FAQ chunks indexed")
    st.markdown("🤖 Embeddings: `all-MiniLM-L6-v2`")
    st.markdown("🧠 LLM: `phi3:mini` via Ollama")
    st.markdown("🌐 Source: `nust.edu.pk/faqs/`")
    st.markdown(
        "<div class='sidebar-footer'>NUST Admissions Assistant v1.0</div>",
        unsafe_allow_html=True
    )
# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; color:#006633; margin-bottom:4px;'>
    🎓 NUST Admissions Assistant
</h1>
<p style='text-align:center; color:#555; font-size:1.05rem; margin-top:0;'>
    Ask me anything about NUST admissions
</p>
""", unsafe_allow_html=True)
st.markdown("<div class='green-divider'></div>", unsafe_allow_html=True)
# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []   # each: {"role", "content", "sources"}
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
# ── Empty state — shown before first message ──────────────────────────────────
if len(st.session_state.messages) == 0:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    suggestions = [
        "What is NET and how do I register?",
        "Does NUST offer scholarships?",
        "Can I apply with A levels?",
        "Are there any reserved seats?",
        "What programmes does NUST offer?",
        "What is the merit criteria?",
    ]
    for i, s in enumerate(suggestions):
        with (col1 if i % 2 == 0 else col2):
            st.markdown(f"<div class='suggestion'>💬 {s}</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
# ── Chat history display ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown("<div class='label-user'>You</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='label-assistant'>🎓 NUST Assistant</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bubble-assistant'>{msg['content']}</div>", unsafe_allow_html=True)
        if msg.get("sources"):
            with st.expander(f"📎 View Sources ({len(msg['sources'])} chunks used)"):
                for i, chunk in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"<div class='source-box'><strong>📄 Source {i}</strong><br><br>{chunk}</div>",
                        unsafe_allow_html=True
                    )
# ── Input area ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input(
        label="question",
        placeholder="Ask about admissions, NET, scholarships...",
        label_visibility="collapsed",
        key=f"input_{st.session_state.input_key}"
    )
with col2:
    send_clicked = st.button("Send ➤", use_container_width=True, type="primary")
# ── Handle submission ─────────────────────────────────────────────────────────
should_send = (send_clicked or user_input) and user_input.strip() != ""
if should_send:
    question = user_input.strip()
    st.session_state.messages.append({"role": "user", "content": question, "sources": []})
    # Show user bubble immediately
    st.markdown("<div class='label-user'>You</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='bubble-user'>{question}</div>", unsafe_allow_html=True)
    # Get answer
    st.info("🔍 Searching FAQs and generating answer...")
    try:
        result  = ask(question)
        answer  = result["answer"]
        sources = result["sources"]
        # Show assistant bubble
        st.markdown("<div class='label-assistant'>🎓 NUST Assistant</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bubble-assistant'>{answer}</div>", unsafe_allow_html=True)
        if sources:
            with st.expander(f"📎 View Sources ({len(sources)} chunks used)"):
                for i, chunk in enumerate(sources, 1):
                    st.markdown(
                        f"<div class='source-box'><strong>📄 Source {i}</strong><br><br>{chunk}</div>",
                        unsafe_allow_html=True
                    )
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
    # Clear input and rerun
    st.session_state.input_key += 1
    st.rerun()