from evaluation.quality_evaluator import QualityEvaluator


def test_quality_evaluator_accepts_specific_cited_single_source_answer():
    evaluator = QualityEvaluator(threshold=0.5)
    answer = (
        "Check Point Security Gateway ist verwundbar. Admins sollen die betroffenen "
        "Security-Gateway- und Spark-Firewall-Systeme aktualisieren [1]."
    )

    result = evaluator.evaluate(answer, [{"link": "https://example.com/check-point"}])

    assert result["score"] >= 0.5
    assert result["flag"] is False
