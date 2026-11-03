"""OpenAI-compatible LLM client (OpenAI, OpenRouter, DeepSeek, Gemini proxies)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


async def chat_completion(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.2,
) -> str | None:
    if not settings.llm_enabled:
        return None

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
    if settings.openrouter_http_referer:
        headers["HTTP-Referer"] = settings.openrouter_http_referer
    if settings.openrouter_app_title:
        headers["X-Title"] = settings.openrouter_app_title

    payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        logger.warning("LLM request failed: %s", exc)
        return None


async def analyze_findings_for_remediation(
    settings: Settings,
    target: str,
    selected_parts: list[str],
    findings: list[dict[str, str]],
    fallback: str,
) -> str:
    system_prompt = (
        "You are a principal defensive security engineer at ETHAR LABS UK LTD. "
        "Produce exact, copy-pasteable remediation: Nginx/Cloudflare snippets, Bash hardening, "
        "Docker overrides. No exploitation, no offensive steps. Output plain text only."
    )
    user_prompt = (
        f"Target: {target}\n"
        f"Selected parts: {', '.join(selected_parts)}\n"
        f"Findings JSON:\n{findings[:20]}\n\n"
        "Append tailored fixes (max 100 lines) to complement baseline templates."
    )
    content = await chat_completion(settings, system_prompt, user_prompt)
    if not content:
        return fallback
    return fallback + "\n\n# --- AI Engineering Appendix (ETHAR LABS UK LTD) ---\n" + content
