# String Neighborhood Kata

## Goal

Define a coding kata for generating all distinct strings that lie within a bounded edit-distance neighborhood of a seed string.

This is inspired by a recovery-style scenario: a user remembers a string very well, but suspects it is slightly wrong. The exercise is to systematically explore the nearby search space so that any target string inside the allowed bounds is guaranteed to be generated.

The kata is framed as a generic offline string-search problem, not as a tool for interacting with real authentication systems.

## Exercise Definition

Given:

- a `seed` string
- an `alphabet`
- a lower bound `min_distance`
- an upper bound `max_distance`
- a set of allowed edit operations

generate all distinct strings whose edit distance from the seed falls within the inclusive band `[min_distance, max_distance]`.

For this kata, distance means the minimum number of allowed edit operations needed to transform `seed` into a candidate string. Each allowed operation counts as one edit step for distance purposes, even when different operations have different likelihood weights.

The algorithm must:

- explore the search space by increasing edit distance from the seed
- rank candidates within each distance layer by likelihood
- produce deterministic output
- avoid duplicates
- guarantee completeness within the requested distance band

## Allowed Operations

The first version of the kata includes these operations:

- insert
- delete
- replace with keyboard-neighbor character
- replace with arbitrary character from the alphabet
- swap adjacent characters

These operations define reachability. Likelihood scoring only affects ordering, not whether a candidate belongs in the result set.

## Contract

### Inputs

- `seed: string`
- `alphabet: set[char]`
- `min_distance: int = 0`
- `max_distance: int`
- enabled operations
- keyboard-neighbor map used to distinguish likely replacements from arbitrary replacements

### Output

An ordered sequence of distinct candidate strings.

### Behavior

- Every emitted string must be reachable from `seed` using only the allowed operations.
- Every reachable string whose distance is in `[min_distance, max_distance]` must appear exactly once.
- Strings below `min_distance` must not be emitted, even if traversal passes through them internally.
- The seed is emitted only when `min_distance = 0`.

## Ordering Rules

Candidates are ordered by:

1. increasing edit distance from the seed
2. increasing cumulative likelihood cost within the same distance layer
3. lexicographic order as a deterministic tie-breaker

This produces complete breadth-first coverage while still surfacing more plausible nearby strings earlier.

## Recommended Approach

The recommended implementation strategy is layered search with weighted ordering:

1. start from the seed
2. generate the next edit-distance layer
3. deduplicate candidates globally
4. score candidates inside the current layer
5. emit only those whose distance is within `[min_distance, max_distance]`
6. continue until `max_distance`

This is preferred over brute-force generation because it preserves a clean completeness argument and uses the seed as a meaningful guide through the search space.

## Likelihood Model

The initial scoring model should be explicit and simple.

Example relative costs:

- adjacent swap: `1`
- keyboard-neighbor replace: `1`
- insert: `2`
- delete: `2`
- arbitrary replace: `3`

Lower total cost means "more plausible" within the same edit-distance layer.

Important constraint:

- distance and likelihood are separate concepts
- every allowed operation contributes `1` to edit distance
- likelihood does not override edit distance ordering
- a candidate at distance `1` must appear before every candidate at distance `2`
- weights only rank candidates against others in the same layer

## Tests

The kata should include tests for:

- completeness across a bounded range
- exact-distance behavior when `min_distance == max_distance`
- uniqueness of generated candidates
- stable deterministic ordering
- multiple mutation paths leading to the same string
- difference between keyboard-neighbor replacement and arbitrary replacement within the same layer

Example test cases:

- `seed="abc", min_distance=0, max_distance=0` returns only `abc`
- `seed="abc", min_distance=1, max_distance=1` returns exactly the 1-edit neighborhood
- `seed="ab", min_distance=2, max_distance=2` validates exact-distance generation
- a case where two distance-1 candidates differ only by replacement type validates ranking
- a case where the same string is reachable by different mutation sequences validates deduplication

## Recommended Kata Outcome

The best version of this exercise is:

"Given a seed string, an alphabet, a keyboard-neighbor map, and a distance band `[min_distance, max_distance]`, generate all distinct strings reachable via insert, delete, replace, and adjacent swap. Emit results in increasing edit distance order, ranking candidates within each distance layer by likelihood."

This gives the kata:

- a clear completeness guarantee
- realistic typo-oriented behavior
- deterministic testability
- room for later extensions without changing the core problem

## Implementation Direction

The recommended implementation uses Rust with layered breadth-first enumeration over edit-distance bands. Internally it operates on character vectors (`Vec<char>`) so edits respect Unicode scalar-value boundaries instead of UTF-8 byte boundaries. Candidates are ranked within each layer by cumulative likelihood cost.

The working crate lives in `string-permutation-kata/rust/`:

- `src/config.rs` — `SearchConfig` plus `EnabledOperations` flags and validation of alphabet and distance bounds.
- `src/keyboard.rs` — `KeyboardNeighbors` lookup over `char` pairs, backed by `FxHashMap`.
- `src/mutations.rs` — `for_each_one_edit_neighbor` (callback-based, scratch `Vec<char>` reuse) and a `one_edit_neighbors` wrapper for tests. Each mutation class is guarded by its `EnabledOperations` flag.
- `src/search.rs` — layered BFS over character vectors with a global `visited` set, per-layer best-cost map, and `(cost, chars)` ordering. Strings are reassembled only when a candidate is emitted.
- `tests/search_tests.rs` — tests covering validation, mutation generation, ordering, deduplication, exact-distance, completeness, Unicode seeds, and per-operation flags.
- `benches/search_bench.rs` — Criterion benchmark for `enumerate_candidates` on `"password"` with distance band `[1, 2]`.

### Configurable operations

`SearchConfig` defaults to all five documented operation classes enabled. Use `with_enabled_operations` to restrict the search:

```rust
let config = SearchConfig::new(seed, alphabet, 1, 2, keyboard_neighbors)?
    .with_enabled_operations(EnabledOperations {
        insert: false,
        delete: true,
        replace: true,
        swap: false,
    });
```

This lets callers match the contract's "enabled operations" input and shape reachability accordingly.
