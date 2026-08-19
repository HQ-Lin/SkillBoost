from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


EVALUATORS = Path(__file__).resolve().parents[1] / "benchmarks" / "evaluators"
sys.path.insert(0, str(EVALUATORS))

from provider import (  # noqa: E402
    ANTHROPIC_DEFAULT_BASE_URL,
    ANTHROPIC_VERSION,
    DASHSCOPE_DEFAULT_BASE_URL,
    normalize_chat_completion_response,
    openai_compatible_api_key,
    openai_compatible_chat_url,
    openai_compatible_provider_label,
    prepare_chat_completion_request,
    provider_model,
)


class ProviderTests(unittest.TestCase):
    def test_primary_openai_compatible_evaluators_use_shared_provider(self) -> None:
        names = (
            "test_alfworld.py",
            "test_bfcl.py",
            "test_docvqa.py",
            "test_livemath.py",
            "test_officeqa.py",
            "test_searchqa.py",
            "test_spreadsheetbench.py",
            "test_swebench.py",
            "test_olympiadbench.py",
        )
        for name in names:
            text = (EVALUATORS / name).read_text(encoding="utf-8")
            self.assertIn("openai_compatible_api_key", text, msg=name)
            expected_transport = (
                "sync_chat_completion" if name == "test_alfworld.py" else "async_chat_completion"
            )
            self.assertIn(expected_transport, text, msg=name)
            self.assertNotIn("openai_compatible.api." + "example.com", text, msg=name)

    def test_anthropic_text_tools_images_and_history_are_converted(self) -> None:
        payload = {
            "model": "default-model",
            "max_tokens": 2048,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": "system skill"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "inspect this"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,ZmFrZQ=="},
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": '{"q":"x"}'},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call-1", "content": "result"},
                {"role": "user", "content": "continue"},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup",
                        "description": "Look up a value",
                        "parameters": {
                            "type": "object",
                            "properties": {"q": {"type": "string"}},
                            "required": ["q"],
                        },
                    },
                }
            ],
            "tool_choice": "auto",
        }
        with patch.dict(
            os.environ,
            {
                "SKILLBOOST_LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-placeholder",
                "SKILLBOOST_MODEL": "claude-test-model",
            },
            clear=True,
        ):
            url, headers, converted = prepare_chat_completion_request(payload)

        self.assertEqual(url, f"{ANTHROPIC_DEFAULT_BASE_URL}/v1/messages")
        self.assertEqual(headers["anthropic-version"], ANTHROPIC_VERSION)
        self.assertEqual(headers["x-api-key"], "test-placeholder")
        self.assertNotIn("Authorization", headers)
        self.assertEqual(converted["model"], "claude-test-model")
        self.assertEqual(converted["system"], "system skill")
        self.assertEqual(converted["tools"][0]["input_schema"]["required"], ["q"])
        self.assertEqual(converted["tool_choice"], {"type": "auto"})
        self.assertEqual(converted["messages"][0]["content"][1]["source"]["type"], "base64")
        self.assertEqual(converted["messages"][1]["content"][0]["type"], "tool_use")
        self.assertEqual(converted["messages"][2]["content"][0]["type"], "tool_result")
        self.assertEqual(converted["messages"][2]["content"][1]["text"], "continue")

    def test_anthropic_response_is_normalized_for_existing_evaluators(self) -> None:
        normalized = normalize_chat_completion_response(
            {
                "id": "msg-1",
                "model": "claude-test-model",
                "stop_reason": "tool_use",
                "content": [
                    {"type": "text", "text": "checking"},
                    {"type": "tool_use", "id": "tool-1", "name": "lookup", "input": {"q": "x"}},
                ],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            }
        )
        message = normalized["choices"][0]["message"]
        self.assertEqual(message["content"], "checking")
        self.assertEqual(message["tool_calls"][0]["function"]["name"], "lookup")
        self.assertEqual(message["tool_calls"][0]["function"]["arguments"], '{"q":"x"}')
        self.assertEqual(normalized["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(normalized["usage"]["total_tokens"], 17)

    def test_anthropic_configuration_uses_environment_only(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SKILLBOOST_LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-placeholder",
                "ANTHROPIC_BASE_URL": "https://anthropic-region.example",
                "SKILLBOOST_MODEL": "claude-test-model",
            },
            clear=True,
        ):
            self.assertEqual(openai_compatible_api_key(), "test-placeholder")
            self.assertEqual(openai_compatible_provider_label(), "anthropic")
            self.assertEqual(provider_model("fallback"), "claude-test-model")
            url, _, _ = prepare_chat_completion_request(
                {"model": "fallback", "messages": [{"role": "user", "content": "hi"}]}
            )
            self.assertEqual(url, "https://anthropic-region.example/v1/messages")

    def test_dashscope_configuration_uses_environment_only(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SKILLBOOST_LLM_PROVIDER": "dashscope",
                "DASHSCOPE_API_KEY": "test-placeholder",
                "DASHSCOPE_BASE_URL": "https://region.example/v1/",
            },
            clear=True,
        ):
            self.assertEqual(openai_compatible_api_key(), "test-placeholder")
            self.assertEqual(openai_compatible_chat_url(), "https://region.example/v1/chat/completions")
            self.assertEqual(openai_compatible_provider_label(), "dashscope")

    def test_dashscope_has_public_non_secret_default_endpoint(self) -> None:
        with patch.dict(
            os.environ,
            {"SKILLBOOST_LLM_PROVIDER": "dashscope", "DASHSCOPE_API_KEY": "test-placeholder"},
            clear=True,
        ):
            self.assertEqual(
                openai_compatible_chat_url(),
                f"{DASHSCOPE_DEFAULT_BASE_URL}/chat/completions",
            )

    def test_generic_provider_requires_explicit_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {"SKILLBOOST_LLM_PROVIDER": "openai-compatible", "LLM_API_KEY": "test-placeholder"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "LLM_BASE_URL"):
                openai_compatible_chat_url()


if __name__ == "__main__":
    unittest.main()
