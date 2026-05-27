"""Tests for llm_client module: retry logic, JSON parsing."""
import pytest
from unittest.mock import patch, MagicMock
from llm_client import parse_json_response, llm


class TestParseJsonResponse:
    """Test robust JSON parsing from LLM output."""

    def test_valid_json_object(self):
        assert parse_json_response('{"key": "value"}') == {"key": "value"}

    def test_valid_json_array(self):
        assert parse_json_response('["a", "b", "c"]') == ["a", "b", "c"]

    def test_markdown_code_block(self):
        raw = '```json\n{"key": "value"}\n```'
        assert parse_json_response(raw) == {"key": "value"}

    def test_json_with_surrounding_text(self):
        raw = 'Here is the result: {"key": "value"} hope this helps'
        assert parse_json_response(raw) == {"key": "value"}

    def test_array_with_surrounding_text(self):
        raw = 'The queries are: ["query1", "query2"]'
        result = parse_json_response(raw)
        assert result == ["query1", "query2"]

    def test_invalid_json_returns_none(self):
        assert parse_json_response("not json at all") is None

    def test_empty_string(self):
        assert parse_json_response("") is None

    def test_nested_json(self):
        raw = '{"verified_claims": [{"claim": "x", "source_id": "y"}], "logic_ok": true}'
        result = parse_json_response(raw)
        assert result["logic_ok"] is True
        assert len(result["verified_claims"]) == 1


class TestLLMRetry:
    """Test retry logic in llm() function."""

    @patch("llm_client._get_client")
    def test_success_on_first_try(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="hello"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = llm("system", "user")
        assert result == "hello"
        assert mock_client.chat.completions.create.call_count == 1

    @patch("llm_client._get_client")
    def test_retry_on_rate_limit(self, mock_get_client):
        mock_client = MagicMock()
        # First call raises rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="success"))]
        mock_client.chat.completions.create.side_effect = [
            Exception("429 rate limit exceeded"),
            mock_response,
        ]
        mock_get_client.return_value = mock_client

        result = llm("system", "user")
        assert result == "success"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("llm_client._get_client")
    def test_raises_after_max_retries(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("permanent error")
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed"):
            llm("system", "user")
