"""example_log_grepper — demonstrates the full sub-agent spec shape.

A sub-agent is pure declarative data: a SubAgentSpec describing the child
runtime's provider/model, system prompt, tool allowlist, dispatch guards,
and expected output shape. There are no lifecycle hooks, no bus binding,
no state — those concerns belong to plugins (`arc-plugin-template`).

The entry-point function `build()` returns ONE spec. arc's Registry merges
any user overrides (from the `subagents:` block in config.yml) on top of
the returned spec — don't read user overrides inside `build()`.

If your package ships multiple specs, register multiple entry points in
pyproject.toml, each pointing at its own builder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Public arc sub-agent API — the one stable import path. See SUBAGENT_API.md.
from arc.subagent_api import SubAgentBuildContext, SubAgentSpec

_HERE = Path(__file__).resolve().parent
_SYSTEM_PROMPT = (_HERE / "prompts" / "system.md").read_text(encoding="utf-8")


# ── Entry point ────────────────────────────────────────────────────────────
# Referenced from pyproject.toml:
#   [project.entry-points."arc.subagents"]
#   example_log_grepper = "arc_sub_agent_example.spec:build"
#
# `config` is reserved (typically {}). Don't read user overrides here —
# Registry merges them onto the returned spec via the `subagents:` config
# block. `build_ctx` is reserved for future use; minimal in v0.1.

def build(config: dict[str, Any], build_ctx: SubAgentBuildContext) -> SubAgentSpec:
    return SubAgentSpec(
        name="example_log_grepper",
        description=(
            "Search log files for a pattern and return structured JSON "
            "with matches, surrounding context, and per-file line numbers. "
            "Pass the path and pattern in the task string; the sub-agent "
            "handles search efficiency, context capture, and output shape."
        ),
        provider="anthropic",
        model="claude-haiku-4-5",
        system_prompt=_SYSTEM_PROMPT,
        tools=("bash", "read"),
        timeout_s=90.0,
        max_turns=15,
        # Dispatch guards — declared explicitly even at defaults to document
        # intent. log_grepper is cheap and fast → higher quota than the
        # runtime default of 5.
        max_dispatches_per_session=20,
        max_consecutive_failures=2,
        max_transient_retries=2,
        # JSON sketch appended to the system prompt by the runner so the
        # child knows exactly what shape its final message should take.
        expected_output=(
            '{"pattern": str, "paths_searched": [str], "total_matches": int, '
            '"matches": [{"file": str, "lines": [int], "context": str}], '
            '"truncated": bool, "notes": str}'
        ),
    )
