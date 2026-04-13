# Change Intent Records: Research Notes

## Origin

Concept from Bryan Liles' article: https://blog.bryanl.dev/posts/change-intent-records/

Prompted by the observation that AI-assisted development sessions produce good decisions in the moment that are invisible to the codebase — the commit message says *what* changed, but not *why this approach over the alternatives the agent proposed*.

## The Problem CIRs Solve

During an AI-assisted session:
- The agent proposes several approaches
- You pick one and reject others for good reasons (performance, project conventions, risk)
- The code lands, commit message says "add rate limiting"
- Three weeks later: nobody knows why the token bucket algorithm was chosen over leaky bucket, or why Redis was used instead of in-process state
- Future AI sessions may propose the same rejected alternatives again

ADRs (Architecture Decision Records) cover architecture-level decisions. CIRs cover implementation-level decisions that happen *within* a session.

## The 5-Section Template

```markdown
# CIR-NNN: Short Title

**Date:** YYYY-MM-DD  
**Supersedes:** CIR-NNN (if applicable)

## Intent
One paragraph: what was the high-level goal of this change?

## Behavior
Given/when/then scenarios — what does this change do, and critically,
what does it NOT affect? (The "not" is as important as the "does".)

## Constraints
Specific boundaries, patterns, or requirements the implementation MUST
respect. Good place for RFC 2119 keywords (MUST/SHOULD/MAY) that are
grep-friendly.

## Decisions
| Proposal | Accepted/Rejected | Reason |
|----------|------------------|--------|
| Use token bucket | Accepted | Fits burst traffic pattern; existing infra already has Redis |
| Use leaky bucket | Rejected | Smooth output not needed; adds complexity |
| In-process state | Rejected | Multi-instance deployment makes this wrong |

## Notes
Anything that didn't fit above.
```

## Key Design Choices in the Format

**"What it does NOT affect"** — Explicitly stating scope boundaries prevents future maintainers from cargo-culting a solution into the wrong context.

**Decisions table** — The agent-proposal / human-judgment workflow maps directly onto this. The agent suggests options; the human decides; the table captures the conversation that happened.

**RFC 2119 keywords** — Makes CIRs grep-friendly. `grep -r "MUST NOT" docs/cir/` surfaces hard constraints.

**Supersedes chain** — When a decision changes, old CIRs stay in place. New CIR references old one. Audit trail preserved.

**Sequential naming** — `CIR-001-rate-limiting.md`, `CIR-002-auth-refactor.md`. Easy to sort, easy to reference.

## Storage Convention

```
docs/
  cir/
    CIR-001-rate-limiting.md
    CIR-002-auth-refactor.md
    CIR-003-...
```

Or `DECISIONS/`, `decisions/`, wherever the project already puts ADRs.

## Comparison to ADRs

| | ADR | CIR |
|---|---|---|
| Scope | Architecture | Implementation detail |
| Trigger | Major structural decision | Any AI-assisted session with alternatives considered |
| Author | Human | Agent drafts, human reviews |
| Lifespan | Long-lived, rarely superseded | Shorter-lived, more frequently superseded |
| Audience | Future architects | Future maintainers (and future AI sessions) |

CIRs complement ADRs — they operate at different levels. A single ADR ("use event sourcing") might spawn many CIRs over time ("chose this specific event schema because...").

## When to Write One

Bryan's test: "Would you be surprised if someone re-proposed the rejected alternative in six months?"

If yes — write the CIR. If the alternative was obviously bad and would never be re-proposed, skip it.

Specifically:
- You rejected a reasonable-looking alternative for non-obvious reasons
- The implementation has gotchas that look like mistakes but are intentional
- The agent proposed 3+ options and the choice among them wasn't obvious

## Agent Workflow

1. Agent implements something
2. Agent drafts a CIR stub (captures proposals it made and which was chosen)
3. Human fills in the "Reason" column with the actual judgment calls
4. Human commits the CIR alongside the implementation

The agent is better positioned to enumerate the proposals; the human is better positioned to articulate why one was chosen.

## Research Observations

The format is deceptively simple. The value is in the Decisions table — specifically in forcing enumeration of what was *rejected*. This is what gets lost in commit messages and what future AI sessions most need to avoid re-litigating.

The "does NOT affect" clause in Behavior is also underrated. Scope boundaries are where implementations break when someone tries to extend them.
