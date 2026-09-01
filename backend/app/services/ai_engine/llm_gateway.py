"""
Multi-Model LLM Gateway.

Connects to Google Gemini, OpenAI, Groq, and Ollama APIs with intelligent
fallback, timeout protection, and strict financial prompt guardrails.
"""
from __future__ import annotations

import logging
from typing import Any
import httpx

from app.config.settings import settings
from app.services.ai_engine.context_builder import FinancialContext

logger = logging.getLogger("wiseguardian.ai_engine")

SYSTEM_PROMPT_TEMPLATE = """You are WiseGuardian's Senior AI Financial Advisor (35+ years of fintech, personal finance & credit analytics expertise).
Your mission is to provide empathetic, highly analytical, mathematically sound, explainable, and actionable financial guidance to students and micro-entrepreneurs.

CRITICAL FINANCIAL SAFETY & PRUDENCE RULES:
1. ONLY reference data present in the user's consented profile below. NEVER hallucinate account balances, transactions, or fake credit scores.
2. In India, currency is Indian Rupees (INR, ₹). Use standard formatted amounts (e.g., ₹25,000).
3. Do NOT provide legal or certified CPA investment advice. Frame advice as financial education, budgeting strategy, and credit readiness guidance.
4. Structure your response in clean, beautiful Markdown with clear section headers (###, ####), bullet points, and strategic bold text.
5. If the user asks about loans or borrowing, evaluate Debt-to-Income (max 20% safe debt ratio) and emergency liquidity.
6. Provide a concise 2-to-3 step actionable roadmap.

{financial_context}
"""


class LLMGateway:
    """Gateway for multi-provider LLM interactions."""

    def __init__(self):
        self.timeout = settings.AI_TIMEOUT_SECONDS

    def generate_response(
        self,
        context: FinancialContext,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str] | None:
        """
        Attempts to generate an LLM response from the configured provider.
        Returns (response_text, provider_model_name) or None if unconfigured / failed.
        """
        # 1. Google Gemini (Preferred / Primary)
        gemini_key = settings.active_gemini_key
        if gemini_key:
            res = self._call_gemini(gemini_key, context, user_message, chat_history)
            if res:
                return res

        # 2. Anthropic Claude (claude-3-5-haiku / claude-sonnet-4-6 etc.)
        if settings.ANTHROPIC_API_KEY:
            res = self._call_anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.AI_MODEL or settings.AI_PROVIDER_MODEL or "claude-3-5-haiku-20241022",
                context=context,
                user_message=user_message,
                chat_history=chat_history,
            )
            if res:
                return res

        # 3. Groq Cloud (Fast inference)
        if settings.GROQ_API_KEY:
            res = self._call_openai_compatible(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY,
                model=settings.AI_MODEL or "llama-3.3-70b-versatile",
                provider_name="groq",
                context=context,
                user_message=user_message,
                chat_history=chat_history,
            )
            if res:
                return res

        # 4. OpenAI
        if settings.OPENAI_API_KEY:
            res = self._call_openai_compatible(
                base_url="https://api.openai.com/v1",
                api_key=settings.OPENAI_API_KEY,
                model=settings.AI_MODEL or "gpt-4o-mini",
                provider_name="openai",
                context=context,
                user_message=user_message,
                chat_history=chat_history,
            )
            if res:
                return res

        # 5. Local Ollama
        if settings.OLLAMA_BASE_URL:
            res = self._call_openai_compatible(
                base_url=f"{settings.OLLAMA_BASE_URL.rstrip('/')}/v1",
                api_key="ollama",
                model=settings.AI_MODEL or "llama3.2",
                provider_name="ollama",
                context=context,
                user_message=user_message,
                chat_history=chat_history,
            )
            if res:
                return res

        return None

    def _call_gemini(
        self,
        api_key: str,
        context: FinancialContext,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str] | None:
        model = settings.AI_MODEL or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            financial_context=context.to_system_prompt_snippet()
        )

        contents = [
            {"role": "user", "parts": [{"text": f"System Context:\n{system_prompt}\n\nUser Question:\n{user_message}"}]}
        ]

        # Add recent conversation turns if available
        if chat_history:
            history_text = "\n".join(
                [f"User: {turn.get('question', '')}\nAdvisor: {turn.get('answer', '')}" for turn in chat_history[-3:]]
            )
            contents = [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                f"System Context:\n{system_prompt}\n\n"
                                f"Conversation History:\n{history_text}\n\n"
                                f"User Question:\n{user_message}"
                            )
                        }
                    ],
                }
            ]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": settings.AI_TEMPERATURE,
                "maxOutputTokens": 1024,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip(), f"gemini/{model}"
                else:
                    logger.warning(f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")

        return None

    def _call_anthropic(
        self,
        api_key: str,
        model: str,
        context: FinancialContext,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str] | None:
        """Call Anthropic Claude via the Messages API."""
        url = "https://api.anthropic.com/v1/messages"
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            financial_context=context.to_system_prompt_snippet()
        )

        messages = []
        if chat_history:
            for turn in chat_history[-3:]:
                if turn.get("question"):
                    messages.append({"role": "user", "content": turn["question"]})
                if turn.get("answer"):
                    messages.append({"role": "assistant", "content": turn["answer"]})

        messages.append({"role": "user", "content": user_message})

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": 1024,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content_blocks = data.get("content", [])
                    if content_blocks and content_blocks[0].get("type") == "text":
                        return content_blocks[0]["text"].strip(), f"anthropic/{model}"
                else:
                    logger.warning(f"Anthropic API returned HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Anthropic API call failed: {e}")

        return None

    def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: str,
        context: FinancialContext,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str] | None:
        url = f"{base_url.rstrip('/')}/chat/completions"
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            financial_context=context.to_system_prompt_snippet()
        )

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for turn in chat_history[-3:]:
                if turn.get("question"):
                    messages.append({"role": "user", "content": turn["question"]})
                if turn.get("answer"):
                    messages.append({"role": "assistant", "content": turn["answer"]})

        messages.append({"role": "user", "content": user_message})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": 1024,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        return choices[0]["message"]["content"].strip(), f"{provider_name}/{model}"
                else:
                    logger.warning(f"{provider_name} API returned HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"{provider_name} API call failed: {e}")

        return None
