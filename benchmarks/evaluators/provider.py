"""Shared model-provider adapter for benchmark evaluators.

Evaluators construct OpenAI-style chat payloads. This module keeps that internal contract
stable while routing requests to DashScope, another OpenAI-compatible service, or the
native Anthropic Messages API. Credentials and endpoint overrides are environment-only.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any


DASHSCOPE_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"


def provider_name() -> str:
    configured = os.environ.get("SKILLBOOST_LLM_PROVIDER", "").strip().lower()
    configured = {
        "openai_compatible": "openai-compatible",
        "claude": "anthropic",
    }.get(configured, configured)
    if configured:
        if configured not in {"dashscope", "openai-compatible", "anthropic"}:
            raise ValueError(
                "SKILLBOOST_LLM_PROVIDER must be 'dashscope', "
                "'openai-compatible', or 'anthropic'"
            )
        return configured
    if os.environ.get("DASHSCOPE_API_KEY"):
        return "dashscope"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai-compatible"


def provider_api_key(legacy_env: str = "LLM_API_KEY") -> str:
    """Resolve the selected task-provider credential."""
    provider = provider_name()
    if provider == "dashscope":
        expected = "DASHSCOPE_API_KEY"
    elif provider == "anthropic":
        expected = "ANTHROPIC_API_KEY"
    else:
        expected = legacy_env
    key = os.environ.get(expected, "")
    if not key:
        raise RuntimeError(f"environment variable {expected} is not set")
    return key


def openai_compatible_api_key(legacy_env: str = "LLM_API_KEY") -> str:
    """Backward-compatible alias for the shared task-provider credential."""
    return provider_api_key(legacy_env)


def openai_compatible_base_url() -> str:
    provider = provider_name()
    if provider == "dashscope":
        base_url = os.environ.get("DASHSCOPE_BASE_URL", DASHSCOPE_DEFAULT_BASE_URL)
    elif provider == "openai-compatible":
        base_url = os.environ.get("LLM_BASE_URL", "")
        if not base_url:
            raise RuntimeError(
                "LLM_BASE_URL is required when SKILLBOOST_LLM_PROVIDER=openai-compatible"
            )
    else:
        raise RuntimeError("Anthropic uses the Messages API, not /chat/completions")
    return base_url.rstrip("/")


def openai_compatible_chat_url() -> str:
    return f"{openai_compatible_base_url()}/chat/completions"


def anthropic_messages_url() -> str:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", ANTHROPIC_DEFAULT_BASE_URL)
    return f"{base_url.rstrip('/')}/v1/messages"


def openai_compatible_provider_label() -> str:
    """Backward-compatible provider label helper."""
    return provider_name()


def provider_model(default_model: str) -> str:
    """Apply a provider-independent model override used by every evaluator."""
    return os.environ.get("SKILLBOOST_MODEL", "").strip() or default_model


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    return "\n".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") in {"text", "input_text"}
    )


_DATA_URL = re.compile(r"^data:([^;,]+);base64,(.+)$", re.DOTALL)


def _anthropic_content_blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    if not isinstance(content, list):
        return [{"type": "text", "text": str(content)}] if content is not None else []

    blocks: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            blocks.append({"type": "text", "text": str(block)})
            continue
        block_type = block.get("type")
        if block_type in {"text", "input_text"}:
            blocks.append({"type": "text", "text": str(block.get("text", ""))})
        elif block_type == "image" and isinstance(block.get("source"), dict):
            blocks.append(block)
        elif block_type == "image_url":
            image_url = block.get("image_url", "")
            url = image_url.get("url", "") if isinstance(image_url, dict) else image_url
            match = _DATA_URL.match(str(url))
            if match:
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": match.group(1),
                            "data": match.group(2),
                        },
                    }
                )
            elif url:
                blocks.append(
                    {"type": "image", "source": {"type": "url", "url": str(url)}}
                )
    return blocks


def _tool_input(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    try:
        parsed = json.loads(arguments or "{}")
    except (TypeError, json.JSONDecodeError):
        return {"raw": str(arguments or "")}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _append_anthropic_message(
    messages: list[dict[str, Any]], role: str, blocks: list[dict[str, Any]]
) -> None:
    if not blocks:
        blocks = [{"type": "text", "text": " "}]
    if messages and messages[-1]["role"] == role:
        messages[-1]["content"].extend(blocks)
    else:
        messages.append({"role": role, "content": blocks})


def _to_anthropic_messages(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        if role == "system":
            text = _text_from_content(message.get("content", ""))
            if text:
                system_parts.append(text)
            continue
        if role == "tool":
            _append_anthropic_message(
                converted,
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.get("tool_call_id", ""),
                        "content": _text_from_content(message.get("content", "")),
                    }
                ],
            )
            continue

        target_role = "assistant" if role == "assistant" else "user"
        blocks = _anthropic_content_blocks(message.get("content", ""))
        if target_role == "assistant":
            for tool_call in message.get("tool_calls") or []:
                function = tool_call.get("function", {})
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.get("id", ""),
                        "name": function.get("name", ""),
                        "input": _tool_input(function.get("arguments", "{}")),
                    }
                )
        _append_anthropic_message(converted, target_role, blocks)
    return "\n\n".join(system_parts), converted


def _to_anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted = []
    for tool in tools:
        function = tool.get("function", tool)
        converted.append(
            {
                "name": function.get("name", ""),
                "description": function.get("description", ""),
                "input_schema": function.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        )
    return converted


def _to_anthropic_tool_choice(tool_choice: Any) -> dict[str, Any] | None:
    if tool_choice in (None, "none"):
        return None
    if tool_choice == "auto":
        return {"type": "auto"}
    if tool_choice == "required":
        return {"type": "any"}
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function", {})
        if function.get("name"):
            return {"type": "tool", "name": function["name"]}
    return None


def _to_anthropic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    system, messages = _to_anthropic_messages(payload.get("messages", []))
    converted: dict[str, Any] = {
        "model": payload["model"],
        "max_tokens": payload.get(
            "max_tokens", payload.get("max_completion_tokens", 4096)
        ),
        "messages": messages,
    }
    if system:
        converted["system"] = system
    if payload.get("temperature") is not None:
        converted["temperature"] = payload["temperature"]
    if payload.get("stop"):
        converted["stop_sequences"] = payload["stop"]
    tools = payload.get("tools") or []
    if tools:
        converted["tools"] = _to_anthropic_tools(tools)
        tool_choice = _to_anthropic_tool_choice(payload.get("tool_choice"))
        if tool_choice:
            converted["tool_choice"] = tool_choice
    return converted


def prepare_chat_completion_request(
    payload: dict[str, Any],
    api_key: str | None = None,
    legacy_env: str = "LLM_API_KEY",
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Return URL, headers, and provider-native JSON for a chat payload."""
    provider = provider_name()
    key = api_key or provider_api_key(legacy_env)
    payload = dict(payload)
    payload["model"] = provider_model(str(payload["model"]))
    if provider == "anthropic":
        return (
            anthropic_messages_url(),
            {
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            _to_anthropic_payload(payload),
        )
    return (
        openai_compatible_chat_url(),
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        payload,
    )


def normalize_chat_completion_response(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize Anthropic Messages responses to the evaluators' OpenAI-style shape."""
    if "choices" in data:
        return data

    text_parts: list[str] = []
    thinking_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in data.get("content", []):
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(block.get("text", ""))
        elif block_type in {"thinking", "redacted_thinking"}:
            thinking = block.get("thinking", "")
            if thinking:
                thinking_parts.append(thinking)
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(
                            block.get("input", {}),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    },
                }
            )

    message: dict[str, Any] = {
        "role": "assistant",
        "content": "\n".join(part for part in text_parts if part),
    }
    if thinking_parts:
        message["reasoning_content"] = "\n".join(thinking_parts)
    if tool_calls:
        message["tool_calls"] = tool_calls

    usage = data.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    finish_reason = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
        "max_tokens": "length",
    }.get(data.get("stop_reason"), data.get("stop_reason"))
    return {
        "id": data.get("id", ""),
        "model": data.get("model", ""),
        "choices": [
            {"index": 0, "message": message, "finish_reason": finish_reason}
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


async def async_chat_completion(
    client: Any,
    payload: dict[str, Any],
    api_key: str | None = None,
    legacy_env: str = "LLM_API_KEY",
) -> dict[str, Any]:
    """Send a provider-neutral chat request with an asynchronous HTTP client."""
    url, headers, provider_payload = prepare_chat_completion_request(
        payload, api_key=api_key, legacy_env=legacy_env
    )
    response = await client.post(url, json=provider_payload, headers=headers)
    response.raise_for_status()
    return normalize_chat_completion_response(response.json())


def sync_chat_completion(
    client: Any,
    payload: dict[str, Any],
    api_key: str | None = None,
    legacy_env: str = "LLM_API_KEY",
) -> dict[str, Any]:
    """Send a provider-neutral chat request with a synchronous HTTP client."""
    url, headers, provider_payload = prepare_chat_completion_request(
        payload, api_key=api_key, legacy_env=legacy_env
    )
    response = client.post(url, json=provider_payload, headers=headers)
    response.raise_for_status()
    return normalize_chat_completion_response(response.json())
