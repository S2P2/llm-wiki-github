import json
import os
from unittest.mock import MagicMock, patch

import pytest

from llm_wiki.compile import call_llm


def test_call_llm_openai():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "ok"}'

    with (
        patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_MODEL": "test-model"}),
        patch("llm_wiki.compile.OpenAI") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create.return_value = mock_response

        result = call_llm("system prompt", "user content")

    assert result == '{"result": "ok"}'
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "test-model"
    assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}


def test_call_llm_anthropic():
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = {"result": "ok"}

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "test-model"}):
        with patch("llm_wiki.compile.anthropic") as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_client.messages.create.return_value = mock_response

            result = call_llm("system prompt", "user content")

    assert json.loads(result) == {"result": "ok"}


def test_call_llm_anthropic_no_tool_use_raises():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "I cannot comply"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "test-model"}):
        with patch("llm_wiki.compile.anthropic") as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_client.messages.create.return_value = mock_response

            with pytest.raises(RuntimeError, match="No tool_use block"):
                call_llm("system prompt", "user content")
