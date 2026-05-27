"""Tests for the Planner agent."""
import pytest
from unittest.mock import patch


class TestPlanner:
    """Test Planner's query decomposition and JSON parsing."""

    @patch("llm_client.llm")
    def test_valid_json_array(self, mock_llm):
        mock_llm.return_value = '["pääomatulovero TVL 124", "30000 euroa korotettu"]'
        from agent import plan
        result = plan("What is the capital income tax rate?")
        assert len(result) >= 2
        assert "pääomatulovero" in result[0]

    @patch("llm_client.llm")
    def test_missing_opening_bracket(self, mock_llm):
        mock_llm.return_value = '"pääomatulovero TVL 124", "30000 euroa korotettu"]'
        from agent import plan
        result = plan("What is the capital income tax rate?")
        # Should still extract quoted strings
        assert len(result) >= 1

    @patch("llm_client.llm")
    def test_markdown_code_block(self, mock_llm):
        mock_llm.return_value = '```json\n["query1", "query2"]\n```'
        from agent import plan
        result = plan("test question")
        assert result == ["query1", "query2"]

    @patch("llm_client.llm")
    def test_fallback_to_original_question(self, mock_llm):
        mock_llm.return_value = "I cannot parse this into queries"
        from agent import plan
        result = plan("original question here")
        assert "original question here" in result

    @patch("llm_client.llm")
    def test_filters_short_strings(self, mock_llm):
        mock_llm.return_value = '["ok query here", "ab", "another good one"]'
        from agent import plan
        result = plan("test")
        # "ab" should be filtered (len <= 3)
        assert all(len(q) > 3 for q in result)
