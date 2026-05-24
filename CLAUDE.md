# arc-sub-agent-template — developer guide

Reference scaffold for building **out-of-tree arc sub-agents**: pip-installable
Python packages that contribute a `SubAgentSpec` arc dispatches as a scoped
child agent. arc auto-discovers via the `arc.subagents` entry-point group at
startup.

Fork this template to build a real sub-agent. The shipped example
(`arc_sub_agent_example`) is a working `example_log_grepper` spec — replace
it with your own.

| | |
|---|---|
| Target API | `arc.subagent_api` v0.1 |
| Spec shape | Pure declarative `SubAgentSpec` dataclass |
| Tests | Plain pytest — `build()` returns the spec, assertions verify fields |

## Read first

- **`README.md`** — user-facing: forking workflow, sub-agent vs plugin
  comparison, "why a sub-agent" guidance.
- **`docs/SUBAGENT_API.md`** — pinned public-API surface.
- **`v2/_design/0020-subagent-dispatch.md`** (in the arc v2 tree) — the
  authoritative design for sub-agents themselves.

## Code map (the shipped example)

```
src/arc_sub_agent_example/
  __init__.py            version stub + fork notes
  spec.py                SubAgentSpec + build() entry-point callable
  prompts/
    system.md            system prompt loaded from disk at module import
tests/
  conftest.py            StubBuildContext fixture
  test_spec.py           build() returns expected spec, fields validate
```

## Sub-agent vs plugin — which template do I want?

| | Plugin (`arc-plugin-template`) | Sub-agent (this) |
|---|---|---|
| What it ships | Hook implementations + optional tools | A `SubAgentSpec` declaration |
| Lives where | Parent's hook chain + tool registry | Scoped child runtime spawned per dispatch |
| LLM | Doesn't call LLM directly | Owns its own provider/model, runs an agent loop |
| State | Session-scoped via lifecycle hooks | Per-dispatch micro-session, no cross-dispatch state |
| Tools | Can ship tools | Doesn't ship tools — references them by name |
| Discovery | `arc.plugins` entry-point group | `arc.subagents` entry-point group |
| Public API | `arc.plugin_api` | `arc.subagent_api` |

**If your sub-agent needs custom tools** (e.g., `extract_frames`), ship a
sibling plugin package — typically named in parallel: `arc-plugin-video`
(the tools) and `arc-sub-agent-video` (the spec that uses them). User
installs both.

## Forking checklist

1. **Rename the package.** `src/arc_sub_agent_example/` → `src/arc_sub_agent_<thing>/`.
   Update `pyproject.toml`: `name`, `[project.entry-points."arc.subagents"]`,
   `[tool.hatch.build.targets.wheel].packages`, AND the force-include path
   for `prompts/`.
2. **Update imports** in `spec.py` and `tests/`.
3. **Replace the example spec.** Gut `example_log_grepper` and write your
   real spec. Keep the structural patterns:
   - System prompt lives in `prompts/system.md`, loaded at module import.
   - `build(config, build_ctx) -> SubAgentSpec` is the entry-point contract.
   - **Do NOT read user overrides from `config`** inside `build()`. arc's
     Registry merges field-level overrides from the `subagents:` config
     block onto your returned spec AFTER `build()` runs. Putting override
     logic in `build()` will fight the Registry.
   - Declare every dispatch guard explicitly even at defaults — documents
     your intent (cheap = high quota; expensive = low quota).
   - Keep `tools` tight. Narrow allowlist = predictable sub-agent.
   - Set `expected_output` to a JSON sketch the child should produce.

## Common patterns

- **System prompt structure.** Aim for 3 sections:
  1. **Methodology** — the steps the sub-agent should follow.
  2. **Output schema** — JSON shape with type annotations.
  3. **Hard limits** — what NOT to do (max iterations, content types
     to skip, destructive ops to refuse).
- **Sibling plugin dependencies.** If your sub-agent needs custom tools,
  document the dependency in your README. arc's runner catches missing
  tools at dispatch time with a clear `ToolError("tool 'X' not available")`,
  but the user needs to know which plugin to install.
- **Provider pinning rationale.** Document in the spec's description WHY
  this sub-agent is pinned to its provider. e.g., "Gemini for native
  video file ingest", "Sonnet for reasoning-heavy reverse engineering",
  "Haiku for cheap classification".
- **Sub-agent vs tool decision.** If the work is "single function with
  clear inputs/outputs", make it a tool. If it's "delegate this whole
  task to a focused agent with its own methodology and provider", make
  it a sub-agent. The cost: sub-agents run a full LLM loop, so they're
  more expensive than a single tool call.

## Testing without arc

The fixture in `tests/conftest.py` provides a minimal `StubBuildContext`.
For tests that import `SubAgentSpec` from `arc.subagent_api`, you need
arc checked out next to your sub-agent:

```bash
pip install -e ".[dev]"
pip install -e ../arc/v2
pytest
```

## Constraints you must honor

1. **No `subagent_*` in your `tools` allowlist.** Recursion is hard-
   prohibited at depth-1. arc's runner refuses to register `SubAgentTool`
   adapters inside a child session; even if you somehow bypassed that,
   the contextvar tripwire raises `SubAgentRecursionError` on dispatch.
2. **Final assistant message is the output.** The Runner extracts whatever
   text content the child emits in its final turn. Train the prompt to
   produce ONLY the structured JSON in that last turn — no prose, no
   markdown fences.
3. **Tools execute in the parent's tool registry context.** Your
   sub-agent's tools run with the parent session's workspace,
   permissions, and tool implementations. The bucket allowlist on
   `arc-plugin-gcs` applies to the sub-agent's `gcs_*` calls too.

## Conventions

- **Use Edit/Write, not bash heredocs.**
- **No multi-paragraph docstrings.** WHY-only.
- **No emojis in code, commit messages, or PR bodies.**
- **Tests after non-trivial changes.**

## Pinned to v0.1

This template targets `arc.subagent_api` v0.1. Plugins that need a
specific feature can assert:

```python
from arc.subagent_api import __api_version__
assert __api_version__ >= (0, 1)
```
