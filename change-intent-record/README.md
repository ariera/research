# Change Intent Records

A lightweight documentation pattern for capturing implementation decisions made during AI-assisted development sessions.

> This research is based on Bryan Liles' article [Change Intent Records](https://blog.bryanl.dev/posts/change-intent-records/). All credit for the original concept and format goes to him.

## The Problem

Commit messages record *what* changed. ADRs record *why* a system is structured a certain way. Neither captures the conversation that happened inside an AI-assisted implementation session: what alternatives the agent proposed, which were rejected, and the reasoning that won't survive past the browser tab.

Six months later — or in the next AI session — those alternatives get proposed again. The same analysis repeats. The same constraints get violated by someone who didn't know they were constraints.

## What a CIR Is

A **Change Intent Record** is a short document saved alongside code that captures:

1. **Intent** — the high-level goal of the change
2. **Behavior** — what the change does, and explicitly what it does *not* affect
3. **Constraints** — hard boundaries the implementation must respect (grep-friendly with RFC 2119 keywords)
4. **Decisions** — a table of proposals considered, accepted or rejected, with reasons
5. **Date** — when the decision was made, with a supersedes chain for when decisions change

## Template

```markdown
# CIR-NNN: Short Title

**Date:** YYYY-MM-DD  
**Supersedes:** CIR-NNN (if applicable)

## Intent
One paragraph: what was the high-level goal of this change?

## Behavior
Given/when/then scenarios describing what the change does
and — critically — what it does NOT affect.

## Constraints
Specific boundaries or requirements the implementation MUST respect.
Use RFC 2119 keywords (MUST/SHOULD/MAY) for greppability.

## Decisions
| Proposal | Accepted/Rejected | Reason |
|----------|------------------|--------|
| Option A | Accepted | Reason |
| Option B | Rejected | Reason |

## Notes
Anything that didn't fit above.
```

## When to Write One

Write a CIR when you'd be surprised if someone re-proposed the rejected alternative in six months. Specifically:

- You rejected a reasonable-looking option for non-obvious reasons
- The implementation has intentional gotchas that look like mistakes
- The agent proposed 3+ options and the choice wasn't obvious

Skip it when the alternative was obviously wrong and would never come up again.

## Storage Convention

```
docs/
  cir/
    CIR-001-rate-limiting.md
    CIR-002-auth-refactor.md
```

Or wherever the project already keeps ADRs. Sequential naming, kebab-case title suffix.

## CIRs vs ADRs

| | ADR | CIR |
|---|---|---|
| Scope | Architecture | Implementation detail |
| Trigger | Major structural decision | Any session with non-obvious alternatives |
| Author | Human | Agent drafts, human reviews |
| Superseded? | Rarely | More frequently |

CIRs complement ADRs — they operate at different levels. An ADR says "use event sourcing." A CIR says "chose this specific event schema over the alternative because of these constraints."

## The Skill

`skills/cir/SKILL.md` implements this as a Claude Code slash command: `/cir`.

Usage:

```
/cir                         # draft CIR for the current session
/cir 007 auth-token-refresh  # draft CIR-007 with specific title
```

The skill prompts Claude to enumerate the proposals made in the session, identify which was accepted, draft the five-section template, and save it to `docs/cir/`. The human fills in the judgment calls in the Decisions table.

## Files

| File | Description |
|------|-------------|
| `notes.md` | Research notes: format analysis, design choices, comparison to ADRs |
| `README.md` | This file |
| `skills/cir/SKILL.md` | Claude Code skill implementing `/cir` slash command |
