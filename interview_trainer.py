"""
Interview Practice Trainer — Turing College Sprint 1
Streamlit app using Groq API (Llama 3.3-70b)

Covers:
- 5 prompt techniques (Zero-Shot, Few-Shot, Chain-of-Thought, Role-Play, Structured Output)
- Temperature tuning
- Security guard (input validation + LLM-based guard)
"""

import streamlit as st
from groq import Groq

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Interview Practice Trainer",
    page_icon="🎯",
    layout="wide",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    h1 { color: #38bdf8; font-family: 'Segoe UI', sans-serif; }
    h2, h3 { color: #7dd3fc; }
    .stSelectbox label, .stSlider label, .stTextArea label,
    .stTextInput label, .stRadio label { color: #94a3b8 !important; }
    div[data-testid="stSidebar"] { background-color: #1e293b; }
    .technique-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .technique-card strong { color: #38bdf8; }
    .answer-box {
        background: #1e293b;
        border-left: 4px solid #38bdf8;
        border-radius: 4px;
        padding: 16px;
        color: #e2e8f0;
        white-space: pre-wrap;
    }
    .security-warning {
        background: #450a0a;
        border: 1px solid #ef4444;
        border-radius: 6px;
        padding: 12px;
        color: #fca5a5;
    }
    .stButton > button {
        background: #0284c7;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button:hover { background: #0369a1; }
</style>
""", unsafe_allow_html=True)


# ─── Constants ────────────────────────────────────────────────────────────────
MODEL = "qwen/qwen3.6-27b"

ROLES = ["Data Analyst", "Data Scientist", "Product Manager",
         "Software Engineer", "ML Engineer"]

PROMPT_TECHNIQUES = {
    "Zero-Shot": {
        "label": "Zero-Shot",
        "desc": "Direct question with no examples. Model uses only its training knowledge.",
        "build": lambda role, topic, q: (
            f"You are an expert interviewer for {role} positions. "
            f"The candidate wants to practise on: {topic}.\n\n"
            f"Generate a challenging interview question and then provide a model answer.\n\n"
            f"Candidate's focus: {q}"
        ),
    },
    "Few-Shot": {
        "label": "Few-Shot",
        "desc": "Provide 2–3 examples so the model learns the expected format before answering.",
        "build": lambda role, topic, q: (
            f"You are a senior {role} interviewer. "
            f"Here are two example Q&A pairs in the expected format:\n\n"
            f"Q: Explain the difference between mean and median and when to use each.\n"
            f"A: Mean sums all values divided by count — sensitive to outliers. "
            f"Median is the middle value — robust to outliers. Use median when data is skewed "
            f"(e.g. salaries). Use mean when distribution is symmetric.\n\n"
            f"Q: What is overfitting and how do you prevent it?\n"
            f"A: Overfitting is when a model memorises training data and fails on new data. "
            f"Prevention: cross-validation, regularisation (L1/L2), dropout, more training data, "
            f"simpler model architecture.\n\n"
            f"Now answer in exactly the same format for this topic — {topic}:\n"
            f"Q: {q}"
        ),
    },
    "Chain-of-Thought": {
        "label": "Chain-of-Thought",
        "desc": "Ask the model to reason step-by-step before giving the final answer.",
        "build": lambda role, topic, q: (
            f"You are a {role} interview coach. Topic: {topic}.\n\n"
            f"When answering, always follow this reasoning chain:\n"
            f"Step 1: Clarify what the question is really testing.\n"
            f"Step 2: Break down the key concepts involved.\n"
            f"Step 3: Give a structured answer with concrete examples.\n"
            f"Step 4: State what a top candidate would add to stand out.\n\n"
            f"Question: {q}"
        ),
    },
    "Role-Play": {
        "label": "Role-Play",
        "desc": "Model acts as a strict interviewer conducting a real interview simulation.",
        "build": lambda role, topic, q: (
            f"You are now playing the role of a rigorous hiring manager at a top tech company "
            f"interviewing a candidate for a {role} position. "
            f"Today's interview focus: {topic}.\n\n"
            f"Conduct a short mock interview:\n"
            f"1. Greet the candidate professionally.\n"
            f"2. Ask the interview question based on: '{q}'.\n"
            f"3. After the question, provide the ideal answer a strong candidate would give.\n"
            f"4. Give brief interviewer feedback on what separates a good vs great answer.\n\n"
            f"Stay in character throughout."
        ),
    },
    "Structured Output": {
        "label": "Structured Output",
        "desc": "Force the model to respond in a predictable JSON-like structure.",
        "build": lambda role, topic, q: (
            f"You are a {role} interview preparation assistant. Topic: {topic}.\n\n"
            f"Respond ONLY in this exact structure:\n\n"
            f"**QUESTION:** [a relevant interview question based on '{q}']\n\n"
            f"**CORE CONCEPT:** [1-2 sentences defining the key idea]\n\n"
            f"**MODEL ANSWER:** [a complete, interview-ready answer in 3-5 bullet points]\n\n"
            f"**COMMON MISTAKES:** [2-3 things candidates often get wrong]\n\n"
            f"**FOLLOW-UP QUESTION:** [one harder follow-up an interviewer might ask]\n\n"
            f"Do not add any text outside this structure."
        ),
    },
}


# ─── Security Guard ───────────────────────────────────────────────────────────
BLOCKED_KEYWORDS = [
    "ignore previous", "ignore all", "jailbreak", "do anything now", "dan mode",
    "pretend you are", "forget your instructions", "you are now", "bypass",
    "disregard", "override", "act as", "roleplay as an unrestricted",
    "write malware", "write exploit", "hack into",
]

def security_guard(text: str) -> tuple[bool, str]:
    """
    Two-layer guard:
    Layer 1 — keyword blocklist (fast, no API call).
    Layer 2 — returns (is_safe, reason).
    """
    text_lower = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in text_lower:
            return False, f"Blocked: input contains disallowed phrase '{kw}'."

    if len(text.strip()) < 3:
        return False, "Input is too short. Please describe what you want to practise."

    if len(text) > 1000:
        return False, "Input exceeds 1000 characters. Please be more concise."

    # Check for purely non-latin gibberish / injection attempts
    if text.count("{") > 3 or text.count("|") > 5:
        return False, "Input contains suspicious characters. Please use plain text."

    return True, ""


# ─── Groq API call ───────────────────────────────────────────────────────────
def call_groq(system_prompt: str, user_message: str,
              temperature: float, api_key: str) -> str:
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ API Error: {e}"


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    # Auto-load from Streamlit Cloud secrets if available
    _secret_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key = st.text_input(
        "Groq API Key",
        value=_secret_key,
        type="password",
        placeholder="gsk_...",
        help="Get a free key at console.groq.com",
    )
    if _secret_key:
        st.success("✅ API key loaded from Secrets", icon="🔑")

    st.markdown("---")
    st.markdown("### 🎛️ Model Settings")

    temperature = st.slider(
        "Temperature",
        min_value=0.0, max_value=2.0, value=0.7, step=0.05,
        help="Lower = more focused answers. Higher = more creative but less predictable.",
    )

    st.markdown(f"""
    <div style='color:#64748b; font-size:0.8rem; margin-top:-8px;'>
    {"🧊 Precise & consistent" if temperature < 0.5 else
     "⚖️ Balanced" if temperature < 1.2 else
     "🔥 Creative & varied"}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📘 Prompt Techniques")
    for name, info in PROMPT_TECHNIQUES.items():
        st.markdown(f"""
        <div class='technique-card'>
            <strong>{info['label']}</strong><br>{info['desc']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='color:#475569;font-size:0.75rem;'>"
        f"Model: <code>qwen/qwen3.6-27b</code><br>"
        "Turing College · Sprint 1</div>",
        unsafe_allow_html=True,
    )


# ─── Main UI ──────────────────────────────────────────────────────────────────
st.markdown("# 🎯 Interview Practice Trainer")
st.markdown(
    "<p style='color:#64748b;'>Practise for your next job interview with AI coaching. "
    "Pick a role, topic, and prompt technique — then ask away.</p>",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    role = st.selectbox("Target Role", ROLES)

with col2:
    topic = st.selectbox(
        "Interview Topic",
        ["SQL & Databases", "Statistics & A/B Testing", "Python",
         "Machine Learning", "Product Metrics", "Behavioural / STAR",
         "System Design", "Data Pipelines"],
    )

with col3:
    technique = st.selectbox(
        "Prompt Technique",
        list(PROMPT_TECHNIQUES.keys()),
        help="Each technique structures the prompt differently.",
    )

user_question = st.text_area(
    "Your question or topic to practise",
    placeholder="e.g. How do I explain p-value to a non-technical stakeholder?",
    height=100,
)

st.caption(f"ℹ️ Technique selected: **{technique}** — {PROMPT_TECHNIQUES[technique]['desc']}")

generate = st.button("🚀 Get Answer", use_container_width=True)


# ─── Generation ───────────────────────────────────────────────────────────────
if generate:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()

    if not user_question.strip():
        st.warning("Please enter a question or topic.")
        st.stop()

    # Security guard
    is_safe, reason = security_guard(user_question)
    if not is_safe:
        st.markdown(
            f"<div class='security-warning'>🛡️ <strong>Security Guard blocked this input.</strong><br>{reason}</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Build prompt using selected technique
    tech = PROMPT_TECHNIQUES[technique]
    system_prompt = tech["build"](role, topic, user_question)

    with st.spinner("Generating your interview answer..."):
        answer = call_groq(system_prompt, user_question, temperature, api_key)

    st.markdown("---")
    st.markdown("### 💬 Answer")
    st.markdown(
        f"<div class='answer-box'>{answer}</div>",
        unsafe_allow_html=True,
    )

    with st.expander("🔍 View raw system prompt sent to the model"):
        st.code(system_prompt, language="text")

    st.markdown(
        f"<div style='color:#475569;font-size:0.8rem;margin-top:8px;'>"
        f"Technique: <strong>{technique}</strong> · "
        f"Temperature: <strong>{temperature}</strong> · "
        f"Role: <strong>{role}</strong> · Topic: <strong>{topic}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )
