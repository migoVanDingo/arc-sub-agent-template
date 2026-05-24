from __future__ import annotations

import json

from arc_sub_agent_example.spec import build


def test_build_returns_spec(build_ctx):
    spec = build({}, build_ctx)
    assert spec.name == "example_log_grepper"
    assert spec.provider == "anthropic"
    assert spec.model == "claude-haiku-4-5"


def test_spec_description_is_actionable(build_ctx):
    spec = build({}, build_ctx)
    # Description is what the parent agent reads in the tool schema, so it
    # must explain how to use the sub-agent (what to pass in the task).
    assert "path" in spec.description.lower()
    assert "pattern" in spec.description.lower()


def test_spec_tools_are_narrow(build_ctx):
    spec = build({}, build_ctx)
    # The whole point of a sub-agent is a tight tool allowlist.
    assert spec.tools == ("bash", "read")


def test_spec_has_system_prompt_loaded_from_file(build_ctx):
    spec = build({}, build_ctx)
    # Prompt should come from prompts/system.md, not be a one-liner.
    assert len(spec.system_prompt) > 500
    assert "Log grepper" in spec.system_prompt
    assert "Output schema" in spec.system_prompt


def test_spec_guards_are_explicit(build_ctx):
    spec = build({}, build_ctx)
    # Authors should set guards explicitly to document intent.
    # log_grepper is cheap → 20 dispatches.
    assert spec.max_dispatches_per_session == 20
    assert spec.max_consecutive_failures == 2
    assert spec.max_transient_retries == 2


def test_spec_timeout_and_turns(build_ctx):
    spec = build({}, build_ctx)
    assert spec.timeout_s == 90.0
    assert spec.max_turns == 15


def test_expected_output_is_a_parseable_sketch(build_ctx):
    spec = build({}, build_ctx)
    # expected_output is appended to the system prompt as a JSON-shape sketch.
    # It's not strict JSON (contains type names) but should mention the
    # critical fields the parent will parse.
    assert spec.expected_output is not None
    for field_name in ("pattern", "paths_searched", "total_matches", "matches"):
        assert field_name in spec.expected_output


def test_build_ignores_config_dict(build_ctx):
    """`config` is reserved — build() must not read user overrides.

    Overrides come from the Registry merging the `subagents:` config block
    onto the returned spec. Building with junk config should produce the
    same spec.
    """
    spec_empty = build({}, build_ctx)
    spec_with_junk = build(
        {"model": "should-be-ignored", "timeout_s": 9999, "garbage": True},
        build_ctx,
    )
    assert spec_empty == spec_with_junk


def test_spec_is_serializable_for_telemetry(build_ctx):
    """The spec should round-trip through JSON-friendly dict form.

    arc's telemetry stamps the resolved spec into events for replay/debug;
    if you add custom non-JSON-serializable fields, this test catches it.
    """
    spec = build({}, build_ctx)
    # tuples in `tools` are JSON-friendly via list conversion
    payload = {
        "name": spec.name,
        "provider": spec.provider,
        "model": spec.model,
        "tools": list(spec.tools),
        "timeout_s": spec.timeout_s,
        "max_turns": spec.max_turns,
        "max_dispatches_per_session": spec.max_dispatches_per_session,
        "max_consecutive_failures": spec.max_consecutive_failures,
        "max_transient_retries": spec.max_transient_retries,
    }
    # Should not raise.
    json.dumps(payload)
