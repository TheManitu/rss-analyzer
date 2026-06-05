from generation.llm_generator import LLMGenerator


class NoopGenerator(LLMGenerator):
    def _call_with_timeout(self, model, messages):
        return None


def test_chatgpt_56_answer_marks_release_and_features_unconfirmed():
    generator = NoopGenerator(timeout_sec=1)
    contexts = [
        {
            "title": "GPT-5.5 in ChatGPT",
            "link": "https://help.openai.com/en/articles/11909943-gpt-55-in-chatgpt",
            "summary": (
                "GPT-5.5 Instant in ChatGPT is the default for all logged-in users. "
                "GPT-5.5 Thinking and Pro are available with different usage limits and context windows."
            ),
        },
        {
            "title": "GPT-5.6 release date leak",
            "link": "https://example.com/gpt-5-6-release-date",
            "summary": (
                "A rumor says GPT-5.6 could launch in June 2026 with a larger context window. "
                "A Codex backend rollout mapping log briefly referenced gpt-5.6 on May 13, 2026 "
                "before it disappeared. Polymarket odds were reported at 80-89% for a public "
                "release by June 30, 2026. Pricing, codenames, benchmarks, agentic workflows, "
                "and token efficiency are discussed, but this is unconfirmed and not published by OpenAI."
            ),
        },
    ]

    answer = generator.generate(
        "Was gibt es Neues zu ChatGPT 5.6, welche Features kann man erwarten und wann kommt es?",
        contexts,
    )

    assert "## Kurzfazit" in answer
    assert "## Gesicherter Stand" in answer
    assert "## Feature-Einschaetzung" in answer
    assert "## Release-Stand" in answer
    assert "## Diskutierte, unbestaetigte Hinweise" in answer
    assert "keine bestaetigte ChatGPT-/GPT-5.6-Ankuendigung" in answer
    assert "Kein offizielles Release-Datum" in answer
    assert "keine bestaetigte Feature-Liste" in answer
    assert "Codex-/Backend-Leak" in answer
    assert "13. Mai 2026" in answer
    assert "80-89%" in answer
    assert "30. Juni 2026" in answer
    assert "Agentic Workflows" in answer
    assert "Token-Effizienz" in answer
    assert "Unbestaetigt" in answer
    assert "Die wichtigsten unbestaetigten Signale" in answer
    assert "\n-" not in answer
    assert "GPT-5.5 in ChatGPT" in answer
    assert "GPT-5.5 Instant in ChatGPT is the default for all logged-in users." not in answer
