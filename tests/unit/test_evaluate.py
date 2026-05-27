"""Tests for evaluate.py: key_facts_coverage normalization."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from evaluate import key_facts_coverage, has_citation


class TestKeyFactsCoverage:
    """Test the flexible matching logic."""

    def test_exact_match(self):
        answer = "The rate is 34%."
        facts = ["The rate is 34%."]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_percent_normalization(self):
        answer = "The rate is 34 percent."
        facts = ["The rate is 34%."]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_prosenttia_normalization(self):
        answer = "The rate is 34%."
        facts = ["34 prosenttia"]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_thousands_separator(self):
        answer = "The threshold is 30000 euros."
        facts = ["30,000 euros"]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_space_thousands(self):
        answer = "The threshold is 30000 euros."
        facts = ["30 000 euros"]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_trailing_zero(self):
        answer = "Maximum is 60 percent."
        facts = ["60.0 percent"]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_decimal_comma_to_dot(self):
        answer = "The rate is 0.27 euros per km."
        facts = ["0,27 euroa"]
        assert key_facts_coverage(answer, facts) == 1.0

    def test_empty_facts(self):
        assert key_facts_coverage("any answer", []) == 1.0

    def test_no_match(self):
        answer = "I don't know."
        facts = ["The rate is 34%."]
        assert key_facts_coverage(answer, facts) == 0.0

    def test_partial_match(self):
        answer = "The rate is 34%. Some other info."
        facts = ["The rate is 34%.", "The threshold is 30000 euros."]
        assert key_facts_coverage(answer, facts) == 0.5

    def test_multiple_numbers_in_fact(self):
        answer = "Capital income up to 30000 euros is taxed at 30%."
        facts = ["Capital income up to 30,000 euros is taxed at the lower rate of 30%."]
        assert key_facts_coverage(answer, facts) >= 0.5


class TestHasCitation:
    """Test citation detection."""

    def test_vero_citation(self):
        assert has_citation("[vero::doc::5] some text") is True

    def test_finlex_citation(self):
        assert has_citation("[finlex::Tuloverolaki::14] text") is True

    def test_statute_reference(self):
        assert has_citation("According to TVL 124 § the rate is") is True

    def test_statute_number(self):
        assert has_citation("Under act 1551/1995") is True

    def test_no_citation(self):
        assert has_citation("The rate is 34 percent.") is False

    def test_verohallinto_parenthetical(self):
        assert has_citation("(Verohallinto, guidance doc)") is True
