import unittest

from assistant.assistant_api import format_document_answer


def hit(score):
    return {"_score": score, "_source": {
        "document": "politica-cobranza.md", "title": "Política de Cobranza",
        "source": "Política financiera sintética", "date": "2026-02-25",
        "classification": "Confidential", "text": "Cada pago conserva la fecha real de pago.",
    }}


class DocumentAnswerTest(unittest.TestCase):
    def test_accepts_hits_above_the_evidence_threshold(self):
        answer = format_document_answer([hit(0.74)])

        self.assertEqual("sufficient", answer["evidence"])
        self.assertEqual(1, len(answer["citations"]))
        citation = answer["citations"][0]
        self.assertEqual("politica-cobranza.md", citation["document"])
        self.assertEqual("Confidential", citation["classification"])
        self.assertIn("excerpt", citation)

    def test_declares_insufficient_evidence_when_no_hit_passes(self):
        answer = format_document_answer([hit(0.21), hit(0.35)])

        self.assertEqual("insufficient", answer["evidence"])
        self.assertEqual([], answer["citations"])
        self.assertIn("no hay evidencia suficiente", answer["message"].lower())

    def test_filters_low_scores_but_keeps_the_strong_one(self):
        answer = format_document_answer([hit(0.30), hit(0.71)])

        self.assertEqual("sufficient", answer["evidence"])
        self.assertEqual(1, len(answer["citations"]))
        self.assertEqual(0.71, answer["citations"][0]["score"])


if __name__ == "__main__":
    unittest.main()
