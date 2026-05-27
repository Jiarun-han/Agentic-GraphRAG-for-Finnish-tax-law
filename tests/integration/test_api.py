"""Integration tests for the FastAPI endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked retriever."""
    with patch("api.Retriever") as MockRetriever:
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {
                "id": "vero::test::0",
                "source": "vero",
                "doc_type": "guidance",
                "doc_title": "Test Document",
                "section": "Section 1",
                "text": "Test content about tax rates.",
                "retrieval_score": 0.9,
                "graph_reason": "direct_vector_hit",
                "graph_hop": 0,
                "file": "vero/test.html",
                "statute_refs": [],
                "links": [],
            }
        ]

        # Patch the global retriever
        import api
        api.retriever = mock_retriever

        from api import app
        yield TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["retriever_loaded"] is True


class TestAskEndpoint:
    @patch("llm_client.llm")
    def test_ask_returns_200(self, mock_llm, client):
        mock_llm.return_value = "The rate is 34%. [vero::test::0]"
        resp = client.post("/ask", json={"question": "What is the tax rate?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert data["question"] == "What is the tax rate?"

    def test_ask_too_short(self, client):
        resp = client.post("/ask", json={"question": "ab"})
        assert resp.status_code == 422  # Pydantic validation

    def test_ask_too_long(self, client):
        resp = client.post("/ask", json={"question": "x" * 2001})
        assert resp.status_code == 422

    def test_ask_empty_body(self, client):
        resp = client.post("/ask", json={})
        assert resp.status_code == 422
