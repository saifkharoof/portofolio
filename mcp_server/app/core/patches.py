"""
Monkey patches for third-party library compatibility.

NeMo Guardrails internally passes `max_tokens` to LangChain's ChatGoogleGenerativeAI,
but langchain-google-genai >= 2.0 renamed this parameter to `max_output_tokens`.
We patch `_generate` and `_agenerate` to translate the parameter name.

This module must be imported BEFORE any NeMo Guardrails initialization.
"""

import langchain_google_genai.chat_models

_original_generate = langchain_google_genai.chat_models.ChatGoogleGenerativeAI._generate


def _patched_generate(self, messages, stop=None, run_manager=None, **kwargs):
    if "max_tokens" in kwargs:
        kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
    return _original_generate(self, messages, stop, run_manager, **kwargs)


langchain_google_genai.chat_models.ChatGoogleGenerativeAI._generate = _patched_generate

_original_agenerate = langchain_google_genai.chat_models.ChatGoogleGenerativeAI._agenerate


async def _patched_agenerate(self, messages, stop=None, run_manager=None, **kwargs):
    if "max_tokens" in kwargs:
        kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
    return await _original_agenerate(self, messages, stop, run_manager, **kwargs)


langchain_google_genai.chat_models.ChatGoogleGenerativeAI._agenerate = _patched_agenerate
