# arc-sub-agent-template

Template repo for building **out-of-tree arc sub-agents**: pip-installable
Python packages that arc auto-discovers via entry points and that contribute
a `SubAgentSpec` callable as a scoped child agent from any parent session.

Use this template when you want to ship a sub-agent that's NOT part of arc's
main repo — because it pins a specific provider/model (e.g., Gemini for
video, Sonnet for reasoning-heavy reverse engineering), wraps a domain-
specific tool set, or just packages a long, opinionated system prompt as a
reusable unit.

## What's in the box

```
arc-sub-agent-template/
├── pyproject.toml                       hatch build + arc.subagents entry point
├── src/arc_sub_agent_example/
│   ├── spec.py                          SubAgentSpec + build() entry point
│   └── prompts/system.md                system prompt as an external file
├── tests/
│   ├── conftest.py                      StubBuildContext fixture
│   └── test_spec.py                     build() returns expected spec, fields validate
└── docs/SUBAGENT_API.md                 Pinned v0.1 public-API surface
```

The example demonstrates a realistic spec — `example_log_grepper`, an
Anthropic-backed log analyst using core `bash` + `read` tools, returning
structured JSON. It exercises every field of `SubAgentSpec` including the
dispatch guards (`max_dispatches_per_session`, `max_consecutive_failures`,
`max_transient_retries`) and `expected_output`.

## Sub-agent vs plugin — which template do I want?

| | Plugin (`arc-plugin-template`) | Sub-agent (this) |
|---|---|---|
| What it ships | Hook implementations + optional tools | A `SubAgentSpec` declaration |
| Lives where | Parent session's hook chain + tool registry | Spawned as a scoped child runtime |
| LLM | Doesn't call the LLM directly | Owns its own provider/model, runs an agent loop |
| State | Session-scoped via `on_session_start`/`on_session_end` | Per-dispatch micro-session, no cross-dispatch state |
| Tools | Can ship tools | Doesn't ship tools — references existing ones by name |
| Discovery | `[project.entry-points."arc.plugins"]` | `[project.entry-points."arc.subagents"]` |
| Public API | `arc.plugin_api` | `arc.subagent_api` |

**If your sub-agent needs custom tools** (e.g., `extract_frames` for video),
ship a sibling plugin package — typically named in parallel:
`arc-plugin-video` (the tools) and `arc-sub-agent-video` (the spec that
uses them). The user installs both.

## Forking workflow

1. **Use the template on GitHub** (or clone + push to a fresh repo).

2. **Rename the package.** Pick a name like `arc-sub-agent-<thing>`:

   ```bash
   git mv src/arc_sub_agent_example src/arc_sub_agent_<thing>

   # In pyproject.toml: name, packages, entry-point key + path
   #   name = "arc-sub-agent-<thing>"
   #   [project.entry-points."arc.subagents"]
   #   <thing> = "arc_sub_agent_<thing>.spec:build"
   #   [tool.hatch.build.targets.wheel]
   #   packages = ["src/arc_sub_agent_<thing>"]
   #   [tool.hatch.build.targets.wheel.force-include]
   #   "src/arc_sub_agent_<thing>/prompts" = "arc_sub_agent_<thing>/prompts"
   ```

   Then update imports in `spec.py` and `tests/`.

3. **Replace the example.** Gut `example_log_grepper` and write your real
   spec. Keep the structural patterns:
   - System prompt lives in `prompts/system.md`, loaded at module import
     via `(_HERE / "prompts" / "system.md").read_text()`. Put long-form
     instructions, output-format examples, and methodology there.
   - `build(config, build_ctx) -> SubAgentSpec` is the entry-point contract.
   - **Do not read `config` inside `build()`** to apply user overrides.
     The Registry merges field-level overrides from the `subagents:` block
     in arc's config.yml AFTER `build()` runs. Putting override logic in
     `build()` will fight the Registry. `config` is reserved for future
     plugin-style options.
   - Declare every dispatch guard explicitly even if you take the default —
     it documents your intent (this spec is cheap → high quota; this spec
     is expensive → low quota).
   - List `tools` as a tight allowlist. The narrower the better.
   - Set `expected_output` to a JSON sketch the child should follow.

4. **Run tests:**

   ```bash
   pip install -e ".[dev]"
   pytest
   ```

   With the `arc` source checked out next to your sub-agent, install it as
   editable too so `from arc.subagent_api import ...` resolves:

   ```bash
   pip install -e ../arc/v2
   ```

5. **Install into arc.** Once your spec works in isolation, point arc at it:

   ```bash
   pip install -e /path/to/arc-sub-agent-<thing>
   ```

   arc's entry-point loader will discover it on next start. The parent
   session sees a new tool named `subagent_<thing>`. Users can override
   any spec field in `~/.arc/config.yml`:

   ```yaml
   subagents:
     <thing>:
       model: claude-sonnet-4-6      # override the model the plugin shipped
       timeout_s: 600                # override the timeout
       max_dispatches_per_session: 3 # tighten the quota
   ```

   Enable/disable via the TUI menu: `arc subagents`.

## Why a sub-agent, not a plugin or a tool?

Reach for a sub-agent when:

- The work **needs a different provider/model** than the parent session.
  Video analysis pins Gemini; deep reasoning pins Sonnet; cheap classification
  pins Haiku. A sub-agent encapsulates "use THIS model for THIS work."
- The work **generates large intermediate context** (disassembly listings,
  transcripts, per-frame detections) the parent agent doesn't need to see.
  Context isolation is the whole point — the parent gets the final structured
  result, not the working transcript.
- The work **follows a domain methodology** worth packaging (e.g.,
  reverse-engineering passes, log triage steps). A long system prompt with
  embedded methodology is a sub-agent's signature artifact.

If you just need a single function the parent can call, write a tool. If you
need to react to lifecycle events or contribute many tools as a unit, write
a plugin. Sub-agents are for "spawn a focused mini-runtime, get a structured
answer back."

## Compatibility

This template targets the arc sub-agent API at version **0.1**
(`arc.subagent_api` shim, entry-point discovery via `arc.subagents`,
`SubAgentSpec` dataclass). See `docs/SUBAGENT_API.md` for the pinned surface
and breakage policy.

## License

MIT — see `LICENSE`. Forks may relicense.
