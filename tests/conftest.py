"""Shared test fixtures for the Taxxa GraphRAG test suite."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Mock LLM responses ────────────────────────────────────────────────────────

MOCK_PLANNER_RESPONSE = '["pääomatulovero 30 prosenttia 34 prosenttia TVL 124 §", "30000 euroa korotettu veroprosentti"]'

MOCK_CLARIFIER_RESPONSE = '{"needs_clarification": true, "missing": ["tax year"], "assumption": "Assuming tax year 2026 and Finnish resident individual."}'

MOCK_ANSWER_RESPONSE = "The capital income tax rate for income exceeding 30,000 euros is 34%. Income up to 30,000 euros is taxed at 30%. [vero::test_doc::1]"

MOCK_AUDITOR_RESPONSE = json.dumps({
    "verified_claims": [{"claim": "rate is 34%", "source_id": "vero::test_doc::1", "source_text": "34 prosenttia"}],
    "unverified_claims": [],
    "conflicts": [],
    "logic_ok": True,
    "completeness_ok": True,
    "missing_info": []
})

MOCK_CONFIDENCE_RESPONSE = json.dumps({
    "confidence": 0.85,
    "confidence_label": "high",
    "reasoning": "All claims verified with authoritative sources",
    "should_caveat": False,
    "caveat_text": ""
})


@pytest.fixture
def mock_llm_responses():
    """Return a sequence of mock LLM responses for a full pipeline run."""
    return [
        MOCK_CLARIFIER_RESPONSE,
        MOCK_PLANNER_RESPONSE,
        MOCK_PLANNER_RESPONSE,  # reranker call
        MOCK_ANSWER_RESPONSE,
        MOCK_AUDITOR_RESPONSE,
        MOCK_CONFIDENCE_RESPONSE,
    ]


@pytest.fixture
def mock_llm(mock_llm_responses):
    """Patch llm_client.llm to return canned responses sequentially."""
    call_idx = {"n": 0}

    def fake_llm(system="", user="", model=None, max_tokens=None):
        idx = call_idx["n"] % len(mock_llm_responses)
        call_idx["n"] += 1
        return mock_llm_responses[idx]

    with patch("llm_client.llm", side_effect=fake_llm) as m:
        yield m


@pytest.fixture
def sample_nodes():
    """Return a small set of representative nodes for testing."""
    return [
        {
            "id": "vero::test_doc::0",
            "source": "vero",
            "doc_type": "guidance",
            "doc_title": "Verotettavan tulon laskeminen",
            "section": "5.1 Veron määräytyminen",
            "text": "Pääomatulosta suoritetaan tuloveroa 30 prosenttia. Siltä osin kuin verovelvollisen verotettavan pääomatulon määrä ylittää 30 000 euroa, pääomatulosta suoritetaan veroa 34 prosenttia.",
            "statute_refs": ["TVL 124 §"],
            "links": [],
            "file": "vero/test/doc.html",
        },
        {
            "id": "vero::test_doc::1",
            "source": "vero",
            "doc_type": "guidance",
            "doc_title": "Korkojen vähentäminen",
            "section": "1 Yleistä",
            "text": "Pääomatulon tuloveroprosentti on 30 % ja siltä osin kuin verovelvollisen verotettavan pääomatulon määrä ylittää 30 000 euroa, pääomatulosta suoritetaan veroa 34 prosenttia.",
            "statute_refs": ["TVL 124 §"],
            "links": [],
            "file": "vero/test/korko.html",
        },
        {
            "id": "finlex::tuloverolaki::14",
            "source": "finlex",
            "doc_type": "statute",
            "doc_title": "Tuloverolaki",
            "section": "124 § Veron määräytyminen",
            "text": "Pääomatulosta suoritetaan tuloveroa 30 prosenttia (pääomatulon tuloveroprosentti). Siltä osin kuin verovelvollisen verotettavan pääomatulon määrä ylittää 30 000 euroa, pääomatulosta suoritetaan veroa 34 prosenttia (pääomatulon korotettu tuloveroprosentti).",
            "statute_refs": [],
            "links": [],
            "file": "finlex/Laki/Tuloverolaki.html",
        },
    ]
