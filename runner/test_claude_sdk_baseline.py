from runner.claude_sdk_baseline import (
    ALLOWED_TOOLS,
    DEFAULT_MAX_TOOL_CALLS,
    _answer_text,
    _final_answer_schema,
    _sdk_environment,
    _usage_tokens,
)


def test_allowed_tools_are_only_worksurface_mcp_tools():
    assert len(ALLOWED_TOOLS) == 7
    assert DEFAULT_MAX_TOOL_CALLS == 8
    assert all(name.startswith("mcp__worksurface__") for name in ALLOWED_TOOLS)
    forbidden = ("Bash", "Read", "Write", "Web", "Task", "Skill")
    assert not any(part in name for name in ALLOWED_TOOLS for part in forbidden)


def test_usage_counts_cached_and_uncached_tokens():
    usage = {
        "input_tokens": 19,
        "cache_creation_input_tokens": 11,
        "cache_read_input_tokens": 158,
        "output_tokens": 30,
    }
    assert _usage_tokens(usage) == 218
    assert _usage_tokens(None) == 0


def test_structured_answers_are_canonicalized():
    assert _answer_text(5) == "5"
    assert _answer_text(["a", "b"]) == '["a", "b"]'
    assert _answer_text(None) == "INSUFFICIENT_EVIDENCE"


def test_output_schema_follows_answer_type():
    assert _final_answer_schema({"answer_type": "number"})["properties"][
        "final_answer"
    ] == {"type": "number"}
    assert _final_answer_schema({"answer_type": "list"})["properties"][
        "final_answer"
    ] == {"type": "array"}
    assert _final_answer_schema({"answer_type": "string"})["properties"][
        "final_answer"
    ] == {"type": "string"}


def test_proxy_environment_is_translated(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("WSB_API_BASE", "https://provider.example/v1/")
    monkeypatch.setenv("WSB_API_KEY", "test-key")
    assert _sdk_environment() == {
        "ANTHROPIC_BASE_URL": "https://provider.example",
        "ANTHROPIC_API_KEY": "test-key",
    }
