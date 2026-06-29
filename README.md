# Interview Practice Trainer — Turing College Sprint 1

A Streamlit app for interview preparation powered by Groq API (Llama 3.3-70b).

## How to run

```bash
pip install -r requirements.txt
streamlit run interview_trainer.py
```

Enter your Groq API key in the sidebar (free at [console.groq.com](https://console.groq.com)).

---

## Requirements coverage

### ✅ 5 Prompt Techniques

| Technique | How it's used |
|---|---|
| **Zero-Shot** | Direct question — model answers with no examples |
| **Few-Shot** | 2 example Q&A pairs given before the real question |
| **Chain-of-Thought** | Explicit 4-step reasoning chain enforced in the prompt |
| **Role-Play** | Model acts as a strict hiring manager conducting a real interview |
| **Structured Output** | Response forced into a fixed template (QUESTION / CORE CONCEPT / MODEL ANSWER / COMMON MISTAKES / FOLLOW-UP) |

### ✅ Temperature tuning

Sidebar slider `0.0 → 2.0` (default 0.7). Label updates dynamically:
- `< 0.5` → Precise & consistent  
- `0.5–1.2` → Balanced  
- `> 1.2` → Creative & varied

### ✅ Security Guard (2 layers)

**Layer 1 — Keyword blocklist** (no API cost):
- Blocks prompt injection phrases: `"ignore previous instructions"`, `"jailbreak"`, `"DAN mode"`, `"act as"`, `"bypass"`, etc.
- Blocks inputs that are too short (< 3 chars) or too long (> 1000 chars)
- Blocks suspicious characters (`{{{`, `|||||`)

**Layer 2 — Structural guard** (future extension point for LLM-as-judge)

### ✅ LLM API

- Provider: **Groq** (free tier, fast inference)
- Model: `llama-3.3-70b-versatile`
- Parameters: `temperature` (user-controlled), `max_tokens=1024`

---

## Design decisions

**Why Groq instead of OpenRouter?**  
Groq offers a free tier with no credit card required and significantly faster inference (< 1s typical), making it ideal for interactive practice sessions.

**Why Llama 3.3-70b?**  
Strong reasoning quality, free on Groq, and handles all 5 prompt techniques reliably.

**Temperature default = 0.7**  
Balanced between creative phrasing and accurate technical content. Lower values (0.1–0.3) recommended for Structured Output technique; higher (1.0+) for brainstorming behavioural answers.

---

## Potential improvements

- Add conversation history (multi-turn chat)
- LLM-as-judge security guard (second API call to validate input)
- Export session transcript as PDF
- RAG: load job description to generate role-specific questions
- Track scores across practice sessions
