"""
tests/test_scoring.py
─────────────────────
Unit tests for the ScoringResult Pydantic model.

These tests are pure unit tests — no DB, no HTTP, no Claude API.
They verify that the scoring contract (field types, bounds, validators)
is enforced at the schema boundary.
"""
import pytest
from pydantic import ValidationError

from app.schemas import ScoringResult


class TestScoringResultValid:
    def test_full_valid_payload(self):
        result = ScoringResult(
            score=8.5,
            correct_findings=["Identified SQL injection", "Located vulnerable line"],
            missed_findings=["Did not suggest parameterised queries"],
            explanation="Good identification, missed remediation detail.",
            fix_suggestion="Use conn.execute(query, (param,)) instead.",
        )
        assert result.score == 8.5
        assert len(result.correct_findings) == 2
        assert len(result.missed_findings) == 1

    def test_score_is_rounded_to_one_decimal(self):
        result = ScoringResult(
            score=7.333333,
            correct_findings=[],
            missed_findings=[],
            explanation="Test",
            fix_suggestion="Test fix",
        )
        assert result.score == 7.3

    def test_score_minimum_boundary(self):
        result = ScoringResult(
            score=0.0,
            correct_findings=[],
            missed_findings=["Everything"],
            explanation="Completely wrong.",
            fix_suggestion="Start over.",
        )
        assert result.score == 0.0

    def test_score_maximum_boundary(self):
        result = ScoringResult(
            score=10.0,
            correct_findings=["Perfect answer"],
            missed_findings=[],
            explanation="Excellent.",
            fix_suggestion="No fix needed — code should be rewritten entirely.",
        )
        assert result.score == 10.0

    def test_empty_findings_lists_are_valid(self):
        """A perfect answer may have no missed_findings."""
        result = ScoringResult(
            score=10.0,
            correct_findings=["All correct"],
            missed_findings=[],
            explanation="Perfect.",
            fix_suggestion="N/A",
        )
        assert result.missed_findings == []


class TestScoringResultInvalid:
    def test_score_below_zero_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ScoringResult(
                score=-1.0,
                correct_findings=[],
                missed_findings=[],
                explanation="Test",
                fix_suggestion="Test",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("score",) for e in errors)

    def test_score_above_ten_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ScoringResult(
                score=11.0,
                correct_findings=[],
                missed_findings=[],
                explanation="Test",
                fix_suggestion="Test",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("score",) for e in errors)

    def test_missing_explanation_raises(self):
        with pytest.raises(ValidationError):
            ScoringResult(
                score=5.0,
                correct_findings=[],
                missed_findings=[],
                fix_suggestion="Fix it.",
                # explanation is missing
            )

    def test_missing_fix_suggestion_raises(self):
        with pytest.raises(ValidationError):
            ScoringResult(
                score=5.0,
                correct_findings=[],
                missed_findings=[],
                explanation="Good try.",
                # fix_suggestion is missing
            )

    def test_score_as_non_numeric_string_raises(self):
        with pytest.raises(ValidationError):
            ScoringResult(
                score="excellent",  # type: ignore[arg-type]
                correct_findings=[],
                missed_findings=[],
                explanation="Test",
                fix_suggestion="Test",
            )
