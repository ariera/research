---
name: cir
description: Draft a Change Intent Record for the current implementation session. Use this when the user invokes /cir, asks to "write a CIR", "document decisions", "record what we decided", or wants to capture why implementation choices were made during this session.
version: 1.0.0
argument-hint: [number] [title]
allowed-tools: [Read, Write, Glob, Bash]
---

# Change Intent Record (CIR) Skill

Draft and save a Change Intent Record capturing the implementation decisions made in this session.

## Arguments

The user invoked this with: $ARGUMENTS

Parse arguments as:
- First positional arg (optional): CIR number (e.g. `007`, `42`). If not provided, determine next number from existing CIRs in `docs/cir/`.
- Remaining args (optional): title slug (e.g. `auth-token-refresh`). If not provided, infer from the session context.

## Instructions

### Step 1: Determine CIR number and title

If a number was provided in $ARGUMENTS, use it (zero-padded to 3 digits).

Otherwise:
1. Check if `docs/cir/` exists. If it does, list files and find the highest existing number. Use next number.
2. If `docs/cir/` doesn't exist, start at `CIR-001`.

If a title was provided in $ARGUMENTS, use it (convert to kebab-case). Otherwise infer from what was implemented in this session.

### Step 2: Draft the CIR

Review the conversation history for this session and identify:

**For Intent:** What was the high-level goal? What problem was being solved?

**For Behavior:** What does the implementation do? More importantly, what does it explicitly NOT affect? Enumerate at least one "does not" clause — this is the part most likely to prevent future breakage.

**For Constraints:** What hard boundaries does the implementation respect? Look for: language/framework constraints mentioned, performance requirements, compatibility requirements, conventions the user enforced. Use RFC 2119 keywords (MUST/SHOULD/MAY/MUST NOT/SHOULD NOT) where appropriate.

**For Decisions:** This is the most important section. Build a table of proposals that were considered:
- Include every approach the AI proposed that wasn't chosen
- Include the approach that was chosen
- For each rejected proposal, capture the reason it was rejected
- For each accepted proposal, capture the reason it was preferred

If the session didn't involve explicit alternative proposals, think about what a future AI would naturally suggest and explain why those alternatives don't apply here.

**For Date:** Use today's date in YYYY-MM-DD format.

### Step 3: Check for supersession

If the session involved revisiting or changing a prior decision, ask the user: "Does this supersede an earlier CIR?" If yes, add a `**Supersedes:** CIR-NNN` line to the header.

### Step 4: Save the file

Target path: `docs/cir/CIR-NNN-title-slug.md`

If `docs/cir/` doesn't exist, create it.

Use this exact template:

```markdown
# CIR-NNN: Human-Readable Title

**Date:** YYYY-MM-DD

## Intent

[One paragraph describing the high-level goal of this change.]

## Behavior

- **Given** [context], **when** [trigger], **then** [outcome].
- This change does NOT affect [explicit scope boundary].
- This change does NOT affect [another boundary if applicable].

## Constraints

- [Constraint 1 — use MUST/SHOULD/MAY language where appropriate]
- [Constraint 2]
- [Constraint N]

## Decisions

| Proposal | Status | Reason |
|----------|--------|--------|
| [What was chosen] | Accepted | [Why] |
| [Alternative 1] | Rejected | [Why rejected] |
| [Alternative 2] | Rejected | [Why rejected] |

## Notes

[Anything that didn't fit the sections above. Leave blank or remove section if nothing.]
```

### Step 5: Report back

Tell the user:
- The path where the CIR was saved
- A one-sentence summary of what was captured
- Ask them to review the Decisions table — they know the *actual* judgment calls better than the AI does; the draft is a starting point, not a final record

## Example Output

```
Saved docs/cir/CIR-003-rate-limiting-token-bucket.md

Captured: chose token bucket over leaky bucket for burst tolerance,
rejected in-process state due to multi-instance deployment.

Please review the Decisions table — the "Reason" column is a draft.
You may know things about the rejection rationale that weren't said
explicitly in this session.
```
