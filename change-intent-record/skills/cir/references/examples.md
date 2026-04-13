# CIR Examples

These examples are from Bryan Liles' article [Change Intent Records](https://blog.bryanl.dev/posts/change-intent-records/).

---

## Example 1: Rate Limiting

```markdown
# CIR-001: Add rate limiting to API endpoints

## Intent
Prevent abuse of public API endpoints by implementing per-user rate limiting.

## Behavior
- GIVEN a user within their request quota
- WHEN they make an API request
- THEN the request succeeds

- GIVEN a user who has exceeded their quota
- WHEN they make an API request
- THEN they receive a 429 response with Retry-After header

- GIVEN an existing endpoint without rate limiting configured
- WHEN it is not in the rate-limited endpoint list
- THEN its behavior SHOULD NOT change

## Constraints
- Use existing Redis infrastructure
- Follow the auth middleware pattern
- Limits configurable per endpoint

## Decisions
- Sliding window over fixed window (smoother limiting)
- Rejected token bucket (the agent's initial proposal was too complex for our traffic)

## Date
2026-01-31
```

**What to learn from this example:**
- The Behavior section's third scenario explicitly scopes what is NOT affected — endpoints not in the rate-limited list must be untouched. This is the "does NOT" clause that prevents future cargo-culting.
- Decisions is terse but captures the rejection of the agent's initial proposal with a concrete reason ("too complex for our traffic"). That's the information that gets lost.

---

## Example 2: User Session Cache

```markdown
# CIR-047: User session cache

## Intent
Cache active user sessions to reduce database load on the auth service.

## Behavior
- GIVEN a user with an active session
- WHEN their session is requested
- THEN it returns from cache within 5ms

- GIVEN a user whose session expired
- WHEN their session is requested
- THEN the cache misses and auth service is queried

## Constraints
- Use Redis per ADR-012
- Sliding window expiration (team standard)
- 15-minute TTL to match auth token expiry

## Decisions
- Rejected LRU eviction (expiry-based is simpler for sessions)
- Chose hash storage over string (easier to extend later)

## Date
2026-07-15
```

**What to learn from this example:**
- Constraints reference an ADR (`ADR-012`) — CIRs and ADRs are complementary. The ADR decides "use Redis"; the CIR records "used hash storage because it's easier to extend."
- TTL is tied to a specific reason (match auth token expiry). Without that, someone will change one without the other.
- Two decisions captured: one rejection, one acceptance with forward-looking rationale.

---

## What makes a good Decisions section

The Decisions section is the hardest to write and the most valuable.

**Minimal but useful:**
```markdown
## Decisions
- Rejected token bucket (too complex for our traffic pattern)
- Chose sliding window (smoother limiting, fits burst tolerance)
```

**With more context when the trade-off was close:**
```markdown
## Decisions
| Proposal | Status | Reason |
|----------|--------|--------|
| Token bucket | Rejected | Agent's initial proposal; overkill for our uniform traffic |
| Leaky bucket | Rejected | Smooth output irrelevant here; adds implementation complexity |
| Sliding window | Accepted | Handles burst traffic; Redis ZRANGEBYSCORE makes it cheap |
```

Use the table format when there were 3+ alternatives or the trade-offs need more surface area. Use the bullet format for 1-2 alternatives where the reasoning is self-contained in a phrase.

## What makes a good Behavior section

Every Behavior section should have at least one "does NOT" clause:

```markdown
- GIVEN [an entity NOT covered by this change]
- WHEN [they encounter the new feature]
- THEN its behavior SHOULD NOT change
```

This is Bryan Liles' key insight: explicitly stating what's out of scope is as important as stating what's in scope. Future maintainers (human or AI) will read this and know not to extend the solution to adjacent problems.
