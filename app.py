import json
from pathlib import Path
import streamlit as st
from chatbot import ask

# Page config
st.set_page_config(
    page_title="RAG based AI Assistant",
    page_icon="🎓",
    layout="centered"
)

# Global CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    * { font-family: 'DM Sans', sans-serif; box-sizing: border-box; margin: 0; padding: 0; }

    /* ── PAGE BACKGROUND ── */
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 100%); }
    #MainMenu, footer, header { visibility: hidden; }

    .stApp, .main, .block-container {
        overflow: hidden !important;
        max-height: 100vh !important;
    }
    .block-container {
        padding: 0 !important;
        max-width: 760px !important;
        margin: 0 auto !important;
        height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* ── OUTER CHAT CARD — modern minimalist design ── */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stVerticalBlockBorderWrapper"] > div,
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #1a1a2e !important;
        border: 1px solid rgba(100, 150, 200, 0.2) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5) !important;
    }
    /* inner scrollable div Streamlit injects for height= containers */
    [data-testid="stVerticalBlockBorderWrapper"] > div[style] {
        background: #1a1a2e !important;
    }
    /* stMain and stMainBlockContainer - covers newer Streamlit versions */
    .stMainBlockContainer [data-testid="stVerticalBlockBorderWrapper"],
    .main [data-testid="stVerticalBlockBorderWrapper"] {
        background: #1a1a2e !important;
    }


    /* ── NAMEBAR — header with blue gradient ── */
    .namebar {
        width: 100%;
        background: linear-gradient(90deg, rgba(15, 52, 96, 0.4) 0%, rgba(30, 90, 150, 0.3) 50%, rgba(15, 52, 96, 0.4) 100%);
        border-bottom: 1px solid rgba(100, 150, 200, 0.2);
        padding: 16px 22px;
        display: flex;
        align-items: center;
        gap: 14px;
        position: relative;
    }
    .namebar::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(90, 156, 255, 0.4), transparent);
    }
    .namebar-avatar {
        width: 44px; height: 44px;
        background: linear-gradient(135deg, #1e90ff, #4169e1);
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
        font-weight: 800;
        color: white;
        flex-shrink: 0;
        letter-spacing: -0.02em;
        box-shadow: 0 4px 14px rgba(30, 144, 255, 0.3);
    }
    .namebar-text { display: flex; flex-direction: column; }
    .namebar-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }
    .namebar-subtitle {
        font-size: 0.70rem;
        color: #7fa8d1;
        margin-top: 3px;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        font-weight: 500;
    }

    /* ── SCROLLABLE CHAT ── */
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar,
    [data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar { width: 5px; }
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-track,
    [data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar-track { background: transparent; }
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb,
    [data-testid="stVerticalBlockBorderWrapper"] > div::-webkit-scrollbar-thumb { background: rgba(90, 156, 255, 0.3); border-radius: 4px; }

    /* ── MESSAGE ROWS ── */
    .msg-row-user {
        display: flex;
        justify-content: flex-end;
        margin: 10px 16px;
        animation: slideInRight 0.3s ease-out;
    }
    .msg-row-bot {
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        gap: 10px;
        margin: 10px 16px;
        animation: slideInLeft 0.3s ease-out;
    }

    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* ── BOT AVATAR ── */
    .bot-avatar-sm {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #1e90ff, #4169e1);
        border-radius: 6px;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.8rem;
        flex-shrink: 0;
        margin-top: 3px;
        box-shadow: 0 2px 8px rgba(30, 144, 255, 0.25);
    }

    /* ── BUBBLES ── */
    .bubble-user {
        background: linear-gradient(135deg, #1e90ff, #4169e1);
        color: #ffffff;
        padding: 11px 16px;
        border-radius: 16px 4px 16px 16px;
        max-width: 70%;
        font-size: 0.9rem;
        line-height: 1.5;
        box-shadow: 0 4px 12px rgba(30, 144, 255, 0.3);
        word-wrap: break-word;
    }
    .bubble-bot {
        background: rgba(60, 70, 100, 0.7);
        color: #e0e5f0;
        padding: 11px 16px;
        border-radius: 4px 16px 16px 16px;
        max-width: 78%;
        font-size: 0.9rem;
        line-height: 1.5;
        border: 1px solid rgba(100, 120, 160, 0.3);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        word-wrap: break-word;
    }

    /* ── WELCOME BUBBLE ── */
    .welcome-wrap { margin: 24px 16px 12px 16px; }
    .welcome-bubble {
        background: rgba(60, 70, 100, 0.6);
        color: #d0dce8;
        padding: 20px;
        border-radius: 10px;
        font-size: 0.9rem;
        line-height: 1.6;
        border: 1px solid rgba(100, 120, 160, 0.3);
        word-wrap: break-word;
    }
    .welcome-text { color: #a8b5c9; font-size: 0.9rem; line-height: 1.6; }

    /* ── TYPING INDICATOR ── */
    .typing-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin: 10px 16px;
    }
    .typing-bubble {
        background: rgba(60, 70, 100, 0.7);
        border: 1px solid rgba(100, 120, 160, 0.3);
        border-radius: 4px 16px 16px 16px;
        padding: 11px 16px;
        display: flex;
        gap: 5px;
        align-items: center;
    }
    .typing-dot {
        width: 7px; height: 7px;
        background: #5a9cff;
        border-radius: 50%;
        animation: bounce 1.2s infinite;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
        0%, 60%, 100% { transform: translateY(0);    opacity: 0.4; }
        30%            { transform: translateY(-6px); opacity: 1; }
    }

    /* ── INPUT BAR styling ── */
    .stTextInput { background: transparent !important; border: none !important; box-shadow: none !important; }
    .stTextInput > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
    .stTextInput > div > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; border-radius: 28px !important; }
    .stTextInput > div:focus-within { border: none !important; box-shadow: none !important; outline: none !important; }

    /* The actual <input> — modern styling ── */
    .stTextInput > div > div > input {
        background-color: rgba(40, 50, 80, 0.6) !important;
        color: #e0e5f0 !important;
        border: 1.5px solid rgba(100, 120, 160, 0.3) !important;
        border-radius: 28px !important;
        padding: 13px 20px !important;
        font-size: 0.9rem !important;
        font-family: 'DM Sans', sans-serif !important;
        caret-color: #5a9cff !important;
        transition: all 0.2s !important;
        outline: none !important;
        box-shadow: none !important;
        width: 100% !important;
        margin-left: 25px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1e90ff !important;
        background: rgba(40, 50, 100, 0.8) !important;
        box-shadow: 0 0 0 3px rgba(30, 144, 255, 0.15) !important;
        outline: none !important;
    }
    .stTextInput > div > div > input::placeholder { color: #6a7a8a !important; }

    /* Send button — modern blue gradient ── */
    .stButton > button {
        background: linear-gradient(135deg, #1e90ff, #4169e1) !important;
        color: white !important;
        border: none !important;
        border-radius: 50% !important;
        width: 48px !important;
        height: 48px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 12px rgba(30, 144, 255, 0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        transform: scale(1.08) !important;
        box-shadow: 0 6px 16px rgba(30, 144, 255, 0.4) !important;
    }
    .stButton > button:active { transform: scale(0.95) !important; }

    /* Sources expander — modern blue theme ── */
    [data-testid="stExpander"] {
        background: rgba(40, 50, 80, 0.5) !important;
        border: 1px solid rgba(100, 120, 160, 0.3) !important;
        border-left: 3px solid #5a9cff !important;
        border-radius: 6px !important;
        margin: 4px 16px 6px 54px !important;
        max-width: 76% !important;
    }
    [data-testid="stExpander"] summary {
        color: #5a9cff !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] p {
        color: #a8b5c9 !important;
        font-size: 0.80rem !important;
        line-height: 1.5 !important;
    }

    /* Global scrollbar ── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(90, 156, 255, 0.3); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(90, 156, 255, 0.5); }
</style>
<script>
// Force chat container background - Streamlit sometimes applies inline styles
const observer = new MutationObserver(() => {
    document.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]').forEach(el => {
        el.style.setProperty("background", "#1a1a2e", "important");
        el.style.setProperty("border", "1px solid rgba(100, 150, 200, 0.2)", "important");
        el.style.setProperty("border-radius", "12px", "important");
    });
});
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

def get_faq_count():
    try:
        with open(Path("index/faqs_texts.json"), "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return "N/A"

faq_count = get_faq_count()


st.markdown("""
<div class='namebar'>
    <div class='namebar-avatar'>🎓</div>
    <div class='namebar-text'>
        <div class='namebar-title'>NUST Admissions AI Assistant</div>
        <div class='namebar-subtitle'>Offline Hybrid RAG Bot</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""

# 1. SCROLLABLE CHAT CONTAINER 
chat_box = st.container(height=520, border=False)

with chat_box:
    # 2. WELCOME MESSAGE
    st.markdown("""
    <div class='welcome-wrap'>
        <div class='welcome-bubble'>
            <div class='welcome-text'>
               Welcome! I am the NUST Admissions AI Assistant. I function entirely offline using a semantic hybrid retrieval system to provide reliable answers. Ask about NET, UG admissions and scholarships.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. CHAT HISTORY 
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(f"""
            <div class='msg-row-user'>
                <div class='bubble-user'>{msg['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='msg-row-bot'>
                <div class='bot-avatar-sm'>🎓</div>
                <div class='bubble-bot'>{msg['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            # Sources — collapsed by default
            if msg.get("sources"):
                with st.expander(f"📎 View sources ({len(msg['sources'])})", expanded=False):
                    for j, chunk in enumerate(msg["sources"], 1):
                        safe_chunk = chunk.replace("<", "&lt;").replace(">", "&gt;")
                        st.markdown(f"**📄 Source {j}**")
                        st.markdown(f"<span style='color:#777; font-size:0.81rem'>{safe_chunk}</span>", unsafe_allow_html=True)
                        if j < len(msg["sources"]):
                            st.markdown("---")

    # 4. TYPING INDICATOR 
    if st.session_state.is_thinking:
        st.markdown("""
        <div class='typing-row'>
            <div class='bot-avatar-sm'>🎓</div>
            <div class='typing-bubble'>
                <div class='typing-dot'></div>
                <div class='typing-dot'></div>
                <div class='typing-dot'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. INPUT BAR 
col1, col2 = st.columns([6, 1])
with col1:
    user_input = st.text_input(
        label="q",
        placeholder="Ask about admissions, NET, scholarships...",
        label_visibility="collapsed",
        key=f"input_{st.session_state.input_key}"
    )
with col2:
    send_clicked = st.button("➤", use_container_width=False, type="primary")

# PHASE 1 — user hits Enter/Send: save message, show typing, rerun
should_send = (send_clicked or user_input) and user_input.strip() != "" and not st.session_state.is_thinking

if should_send:
    question = user_input.strip()
    st.session_state.messages.append({
        "role": "user",
        "content": question,
        "sources": []
    })
    st.session_state.is_thinking      = True
    st.session_state.pending_question = question
    st.session_state.input_key       += 1
    st.rerun()

# PHASE 2 — thinking flag is set: call LLM, save answer, rerun
if st.session_state.is_thinking:
    try:
        result  = ask(st.session_state.pending_question)
        answer  = result["answer"]
        sources = result["sources"]
    except Exception as e:
        answer  = f"⚠️ Error: {str(e)}"
        sources = []

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })
    st.session_state.is_thinking      = False
    st.session_state.pending_question = ""
    st.rerun()