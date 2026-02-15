"""Tests for the bias-scoring module."""

from llm_guardrails.bias_scorer import BiasScorer


class TestNeutralText:
    def test_neutral_text_low_score(self):
        scorer = BiasScorer()
        report = scorer.score(
            "The weather today is sunny with a high of 75 degrees."
        )
        assert report.score == 0.0
        assert report.flags == []


class TestStereotypingDetection:
    def test_gender_stereotype(self):
        scorer = BiasScorer()
        report = scorer.score("Women are naturally bad at mathematics.")
        assert report.score > 0.0
        assert any("stereotype" in f.lower() or "generalisation" in f.lower() for f in report.flags)

    def test_age_stereotype(self):
        scorer = BiasScorer()
        report = scorer.score("Elderly are always slow and forgetful.")
        assert report.score > 0.0
        assert len(report.flags) > 0


class TestAbsoluteGeneralisation:
    def test_all_group_are(self):
        scorer = BiasScorer()
        report = scorer.score("All women are emotional.")
        assert report.score > 0.0
        assert len(report.flags) >= 1


class TestMultipleFlags:
    def test_compounded_bias(self):
        scorer = BiasScorer()
        report = scorer.score(
            "All men are strong leaders. Women are naturally better at caregiving. "
            "Every women need guidance from men."
        )
        assert report.score > 0.2
        assert len(report.flags) >= 2
