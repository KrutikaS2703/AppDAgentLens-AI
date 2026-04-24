import warnings
import os
import time
import json
from typing import Optional, Tuple

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+, currently the 'ssl' module is compiled with 'LibreSSL.*",
)

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars

# Groq provider
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def _safe_int(env_name: str, default: int) -> int:
    try:
        return int(os.getenv(env_name, str(default)).strip())
    except ValueError:
        return default


def _safe_bool(env_name: str, default: bool) -> bool:
    raw = os.getenv(env_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _provider_enabled(
    explicit_flag: str,
    default_when_unset: bool,
    configured: bool,
) -> bool:
    """
    Resolve provider enablement.

    - If explicit flag is set, respect it.
    - If flag is unset, enable only when configured.
    """
    raw = os.getenv(explicit_flag)
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    if configured:
        return True

    return default_when_unset


def _ask_groq(prompt: str, timeout_override: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    groq_token = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    max_tokens = _safe_int("GROQ_MAX_TOKENS", 450)
    request_timeout = timeout_override or _safe_int("GROQ_TIMEOUT_SECONDS", 12)
    retries = max(_safe_int("GROQ_RETRIES", 1), 1)

    if not groq_token:
        return None, "GROQ_API_KEY is not set"

    headers = {
        "Authorization": f"Bearer {groq_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }

    try:
        # Retry rate-limit responses with exponential backoff.
        for attempt in range(retries):
            response = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=request_timeout)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "").strip()
                wait_seconds = int(retry_after) if retry_after.isdigit() else min(2 ** attempt, 2)
                time.sleep(wait_seconds)
                continue

            if response.status_code == 401:
                return None, "invalid or expired GROQ_API_KEY"
            if response.status_code == 403:
                return None, f"access denied for model '{model}'"
            if response.status_code == 404:
                return None, f"model '{model}' not found"

            response.raise_for_status()
            data = response.json()

            choices = data.get("choices") or []
            if choices:
                content = str(choices[0].get("message", {}).get("content", "")).strip()
                if content:
                    return content, None

            if data.get("error"):
                return None, f"Groq error: {data['error']}"

            return None, "empty response from Groq"

        return None, "Groq rate limit hit after retries"

    except Exception as e:
        return None, f"Groq error: {e}"


def ask_llm_with_model(prompt: str) -> Tuple[str, str]:
    """
    LLM call with model tracking via Groq.

    Returns tuple of (response, model_name); otherwise (AI-unavailable summary, "Unknown").
    """
    errors = []
    total_budget = max(_safe_int("LLM_TOTAL_TIMEOUT_SECONDS", 20), 1)
    start = time.monotonic()

    has_groq_key = bool(os.getenv("GROQ_API_KEY", "").strip())

    def remaining_seconds() -> int:
        elapsed = time.monotonic() - start
        return max(int(total_budget - elapsed), 0)

    providers = [
        (
            "Groq",
            _ask_groq,
            _provider_enabled("ENABLE_GROQ", True, has_groq_key),
            _safe_int("GROQ_TIMEOUT_SECONDS", 8),
        ),
    ]

    for provider_name, provider_fn, is_enabled, provider_timeout in providers:
        if not is_enabled:
            errors.append(f"{provider_name}: disabled")
            continue

        remaining = remaining_seconds()
        if remaining <= 0:
            errors.append(f"{provider_name}: skipped (time budget exhausted)")
            continue

        timeout_for_call = max(min(provider_timeout, remaining), 1)
        response, error = provider_fn(prompt, timeout_override=timeout_for_call)
        if response:
            model_name = os.getenv(
                f"{provider_name.upper()}_MODEL",
                "llama-3.3-70b-versatile"
            ).strip()
            return response, f"{provider_name} ({model_name})"
        if error:
            errors.append(f"{provider_name}: {error}")

    error_summary = "AI unavailable: all providers failed. " + " | ".join(errors)
    return error_summary, "Unknown"


def ask_llm(prompt: str) -> str:
    """
    LLM call via Groq.

    Returns successful response; otherwise returns AI-unavailable summary.
    """
    response, _ = ask_llm_with_model(prompt)
    return response
