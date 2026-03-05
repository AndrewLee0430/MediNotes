"""
api/middleware/guards.py
輸入防護模組 - v1.0

功能：
1. Prompt Injection 防護 — 快速 pattern 掃描，不依賴 LLM
2. 非醫療意圖偵測 — LLM 分類，確保 Vela 只回答臨床問題
"""

import re
from openai import OpenAI

# ============================================================
# 1. Prompt Injection 防護
# ============================================================

# 常見 injection 攻擊模式
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(everything|all|your)\s*(you\s+know|instructions?|rules?)?",
    r"you\s+are\s+now\s+(a|an|DAN|jailbreak)",
    r"(act|pretend|roleplay|behave)\s+as\s+(if\s+)?(you\s+are\s+)?(a|an)?\s*(unrestricted|unfiltered|evil|DAN)",
    r"(new|updated|override)\s+(system\s+)?(prompt|instruction|rule)",
    r"\/\/\s*system",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*(instruction|system|prompt)",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"prompt\s+inject",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def check_prompt_injection(text: str) -> bool:
    """
    回傳 True 代表偵測到 injection 攻擊
    """
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ============================================================
# 2. 非醫療意圖偵測
# ============================================================

INTENT_SYSTEM_PROMPT = """You are a strict input classifier for a clinical medical AI system called Vela.
Vela ONLY handles clinical and pharmaceutical questions from healthcare professionals.

Classify the input as one of:
- "medical": clinical questions, drug queries, pharmacology, patient symptoms, medical procedures, lab values, disease management, prescription questions
- "non_medical": anything else (general knowledge, coding, writing, personal advice, jokes, politics, etc.)

Edge cases to classify as "medical":
- Questions in any language about drugs, symptoms, or clinical decisions
- Mixed-language medical questions (e.g. Chinese + English drug names)
- Abbreviations common in medicine (e.g. HTN, DM, AF, INR, eGFR)
- Questions about medical guidelines, dosing, interactions

Return ONLY valid JSON: {"intent": "medical"} or {"intent": "non_medical", "reason": "brief reason"}"""


async def check_medical_intent(text: str) -> tuple[bool, str]:
    """
    回傳 (is_medical, reason)
    is_medical=True  → 正常繼續
    is_medical=False → 回傳 reason 給用戶
    """
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text[:500]}  # 只看前 500 字元，省成本
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=60
        )
        import json
        result = json.loads(response.choices[0].message.content)
        if result.get("intent") == "medical":
            return True, ""
        else:
            reason = result.get("reason", "non-medical query")
            return False, reason
    except Exception as e:
        # 分類失敗時放行，不阻擋正常使用
        print(f"⚠️ Intent check failed (allowing through): {e}")
        return True, ""


# ============================================================
# 3. 統一入口：run_guards()
# ============================================================

async def run_guards(text: str) -> tuple[bool, str]:
    """
    依序執行所有防護，回傳 (passed, error_message)
    passed=True  → 輸入安全，繼續處理
    passed=False → 輸入被攔截，回傳 error_message 給用戶
    """
    # Step 1：Prompt injection（不需要 LLM，即時）
    if check_prompt_injection(text):
        return False, (
            "⚠️ Your input contains patterns that cannot be processed. "
            "Please rephrase your clinical question."
        )

    # Step 2：非醫療意圖（LLM 分類，~0.1s）
    is_medical, reason = await check_medical_intent(text)
    if not is_medical:
        return False, (
            "Vela is a clinical medical assistant designed for healthcare professionals. "
            "This question appears to be outside our scope. "
            "Please ask a clinical or pharmaceutical question."
        )

    return True, ""