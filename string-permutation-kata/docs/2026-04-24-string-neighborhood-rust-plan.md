# String Neighborhood Kata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-performance Rust library that generates all distinct strings in a bounded edit-distance band around a seed string, ordered by distance first and likelihood second.

**Architecture:** Implement the kata as a small Rust library crate with focused modules for configuration, keyboard-neighbor replacement logic, one-step mutation generation, and layered search. Represent strings internally as ASCII byte vectors for speed, track global deduplication with fast hash sets, and sort each distance layer by `(distance, likelihood_cost, lexicographic_bytes)` before emitting results.

**Tech Stack:** Rust 1.95, Cargo, standard test harness, `rustc_hash` for fast hash maps/sets, `smallvec` for small temporary mutation collections, `criterion` for benchmarks

---

## File Structure

- Create: `string-permutation-kata/rust/Cargo.toml`
- Create: `string-permutation-kata/rust/src/lib.rs`
- Create: `string-permutation-kata/rust/src/config.rs`
- Create: `string-permutation-kata/rust/src/keyboard.rs`
- Create: `string-permutation-kata/rust/src/mutations.rs`
- Create: `string-permutation-kata/rust/src/search.rs`
- Create: `string-permutation-kata/rust/tests/search_tests.rs`
- Create: `string-permutation-kata/rust/benches/search_bench.rs`

Responsibilities:

- `Cargo.toml`: crate metadata and minimal dependencies
- `lib.rs`: public exports only
- `config.rs`: request/response data types and validation
- `keyboard.rs`: neighbor map representation and lookup
- `mutations.rs`: one-edit mutation generation plus likelihood cost contribution
- `search.rs`: breadth-first layered enumeration with deterministic ordering
- `tests/search_tests.rs`: correctness and ordering tests from the kata spec
- `benches/search_bench.rs`: benchmark representative bounded searches

## Language Choice

Recommendation: use Rust.

Reason:

- strongest combination of performance, deterministic behavior, memory control, and safety
- good fit for a search problem with many short-lived candidate values
- easy to package as a reusable library and later expose as a CLI if needed

Best alternative: Go.

Use Go only if implementation speed matters more than peak throughput and allocation control. Go will be simpler to write, but the Rust version is the better long-term fit for a performance-critical generator.

## Task 1: Scaffold The Crate

**Files:**
- Create: `string-permutation-kata/rust/Cargo.toml`
- Create: `string-permutation-kata/rust/src/lib.rs`
- Test: `string-permutation-kata/rust/tests/search_tests.rs`

- [ ] **Step 1: Write the failing smoke test**

```rust
use string_neighborhood_kata::{
    enumerate_candidates, KeyboardNeighbors, SearchConfig,
};

#[test]
fn returns_seed_when_distance_band_is_zero() {
    let config = SearchConfig::new(
        "abc",
        b"abc".to_vec(),
        0,
        0,
        KeyboardNeighbors::empty(),
    )
    .unwrap();

    let result = enumerate_candidates(&config).unwrap();

    assert_eq!(result, vec!["abc".to_string()]);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test returns_seed_when_distance_band_is_zero --test search_tests -q`
Expected: FAIL with unresolved import or missing crate items

- [ ] **Step 3: Write minimal crate scaffold**

```toml
[package]
name = "string-neighborhood-kata"
version = "0.1.0"
edition = "2024"

[dependencies]
rustc-hash = "2"
smallvec = "1"

[dev-dependencies]
criterion = "0.7"
```

```rust
mod config;
mod keyboard;
mod mutations;
mod search;

pub use config::SearchConfig;
pub use keyboard::KeyboardNeighbors;
pub use search::enumerate_candidates;
```

- [ ] **Step 4: Run test to verify it still fails for the right reason**

Run: `cargo test returns_seed_when_distance_band_is_zero --test search_tests -q`
Expected: FAIL because the scaffold now resolves as a crate but Task 1 has not created `config`, `keyboard`, `mutations`, or `search` module files yet. This is acceptable at the end of Task 1; Task 2 creates the first real module files.

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/Cargo.toml string-permutation-kata/rust/src/lib.rs string-permutation-kata/rust/tests/search_tests.rs
git commit -m "feat: scaffold rust kata crate"
```

## Task 2: Define Public Types And Validation

**Files:**
- Create: `string-permutation-kata/rust/src/config.rs`
- Create: `string-permutation-kata/rust/src/keyboard.rs`
- Create: `string-permutation-kata/rust/src/mutations.rs`
- Create: `string-permutation-kata/rust/src/search.rs`
- Modify: `string-permutation-kata/rust/src/lib.rs`
- Test: `string-permutation-kata/rust/tests/search_tests.rs`

- [ ] **Step 1: Write failing validation tests**

```rust
#[test]
fn rejects_min_distance_greater_than_max_distance() {
    let result = SearchConfig::new("abc", b"abc".to_vec(), 2, 1, KeyboardNeighbors::empty());
    assert!(result.is_err());
}

#[test]
fn rejects_seed_with_bytes_outside_alphabet() {
    let result = SearchConfig::new("abd", b"abc".to_vec(), 0, 1, KeyboardNeighbors::empty());
    assert!(result.is_err());
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test rejects_ --test search_tests -q`
Expected: FAIL because the crate still lacks `config`, `keyboard`, `mutations`, and `search` module files before Task 2 creates them. This is the correct red state for Task 2.

- [ ] **Step 3: Implement configuration and keyboard map types**

```rust
use std::sync::Arc;

#[derive(Clone, Debug)]
pub struct SearchConfig {
    pub seed: String,
    pub alphabet: Arc<[u8]>,
    pub min_distance: usize,
    pub max_distance: usize,
    pub keyboard_neighbors: KeyboardNeighbors,
}

impl SearchConfig {
    pub fn new(
        seed: impl Into<String>,
        alphabet: Vec<u8>,
        min_distance: usize,
        max_distance: usize,
        keyboard_neighbors: KeyboardNeighbors,
    ) -> Result<Self, String> {
        let seed = seed.into();
        if min_distance > max_distance {
            return Err("min_distance must be <= max_distance".into());
        }
        if alphabet.is_empty() {
            return Err("alphabet must not be empty".into());
        }
        if !seed.as_bytes().iter().all(|byte| alphabet.contains(byte)) {
            return Err("seed contains bytes outside alphabet".into());
        }

        Ok(Self {
            seed,
            alphabet: Arc::<[u8]>::from(alphabet),
            min_distance,
            max_distance,
            keyboard_neighbors,
        })
    }
}
```

```rust
use rustc_hash::FxHashMap;

#[derive(Clone, Debug, Default)]
pub struct KeyboardNeighbors {
    by_key: FxHashMap<u8, Box<[u8]>>,
}

impl KeyboardNeighbors {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn from_pairs(pairs: &[(u8, &[u8])]) -> Self {
        let mut by_key = FxHashMap::default();
        for (key, neighbors) in pairs {
            by_key.insert(*key, neighbors.to_vec().into_boxed_slice());
        }
        Self { by_key }
    }

    pub fn contains_neighbor(&self, source: u8, target: u8) -> bool {
        self.by_key
            .get(&source)
            .map(|neighbors| neighbors.contains(&target))
            .unwrap_or(false)
    }
}
```

```rust
// src/mutations.rs
// Placeholder module so Task 2 compiles; Task 3 adds real mutation generation.
```

```rust
// src/search.rs
use crate::config::SearchConfig;

pub fn enumerate_candidates(_config: &SearchConfig) -> Result<Vec<String>, String> {
    todo!("implemented in Task 4")
}
```

```rust
// src/lib.rs
mod config;
mod keyboard;
mod mutations;
mod search;

pub use config::SearchConfig;
pub use keyboard::KeyboardNeighbors;
pub use search::enumerate_candidates;
```

- [ ] **Step 4: Run the validation tests**

Run: `cargo test rejects_ --test search_tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/src/config.rs string-permutation-kata/rust/src/keyboard.rs string-permutation-kata/rust/src/mutations.rs string-permutation-kata/rust/src/search.rs string-permutation-kata/rust/src/lib.rs string-permutation-kata/rust/tests/search_tests.rs
git commit -m "feat: add search configuration types"
```

## Task 3: Generate One-Edit Mutations With Costs

**Files:**
- Modify: `string-permutation-kata/rust/src/mutations.rs`
- Modify: `string-permutation-kata/rust/src/lib.rs`
- Test: `string-permutation-kata/rust/tests/search_tests.rs`

- [ ] **Step 1: Write failing mutation tests**

```rust
#[test]
fn generates_insert_delete_replace_and_swap_neighbors() {
    let config = SearchConfig::new(
        "ab",
        b"abc".to_vec(),
        1,
        1,
        KeyboardNeighbors::from_pairs(&[(b'a', b"b"), (b'b', b"a")]),
    )
    .unwrap();

    let neighbors = string_neighborhood_kata::one_edit_neighbors(config.seed.as_bytes(), &config);

    assert!(neighbors.iter().any(|item| item.candidate == b"a".to_vec()));
    assert!(neighbors.iter().any(|item| item.candidate == b"abc".to_vec()));
    assert!(neighbors.iter().any(|item| item.candidate == b"ba".to_vec()));
    assert!(neighbors.iter().any(|item| item.candidate == b"bb".to_vec()));
}

#[test]
fn keyboard_neighbor_replace_costs_less_than_arbitrary_replace() {
    let config = SearchConfig::new(
        "ab",
        b"abc".to_vec(),
        1,
        1,
        KeyboardNeighbors::from_pairs(&[(b'a', b"b")]),
    )
    .unwrap();

    let neighbors = string_neighborhood_kata::one_edit_neighbors(config.seed.as_bytes(), &config);
    let keyboard_cost = neighbors
        .iter()
        .find(|item| item.candidate == b"bb".to_vec())
        .unwrap()
        .likelihood_cost;
    let arbitrary_cost = neighbors
        .iter()
        .find(|item| item.candidate == b"cb".to_vec())
        .unwrap()
        .likelihood_cost;

    assert!(keyboard_cost < arbitrary_cost);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test generates_insert_delete_replace_and_swap_neighbors --test search_tests -q`
Expected: FAIL because `one_edit_neighbors` is missing

- [ ] **Step 3: Implement one-edit mutation generation**

```rust
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NeighborCandidate {
    pub candidate: Vec<u8>,
    pub likelihood_cost: u32,
}

pub fn one_edit_neighbors(seed: &[u8], config: &SearchConfig) -> Vec<NeighborCandidate> {
    let mut out = Vec::new();

    for index in 0..seed.len() {
        let mut candidate = seed.to_vec();
        candidate.remove(index);
        out.push(NeighborCandidate { candidate, likelihood_cost: 2 });
    }

    for index in 0..=seed.len() {
        for &byte in config.alphabet.iter() {
            let mut candidate = seed.to_vec();
            candidate.insert(index, byte);
            out.push(NeighborCandidate { candidate, likelihood_cost: 2 });
        }
    }

    for index in 0..seed.len() {
        for &byte in config.alphabet.iter() {
            if byte == seed[index] {
                continue;
            }
            let mut candidate = seed.to_vec();
            candidate[index] = byte;
            let likelihood_cost = if config.keyboard_neighbors.contains_neighbor(seed[index], byte) {
                1
            } else {
                3
            };
            out.push(NeighborCandidate { candidate, likelihood_cost });
        }
    }

    for index in 0..seed.len().saturating_sub(1) {
        let mut candidate = seed.to_vec();
        candidate.swap(index, index + 1);
        out.push(NeighborCandidate { candidate, likelihood_cost: 1 });
    }

    out
}
```

```rust
// src/lib.rs
mod config;
mod keyboard;
mod mutations;
mod search;

pub use config::SearchConfig;
pub use keyboard::KeyboardNeighbors;
pub use mutations::{one_edit_neighbors, NeighborCandidate};
pub use search::enumerate_candidates;
```

- [ ] **Step 4: Run mutation tests**

Run: `cargo test generates_insert_delete_replace_and_swap_neighbors --test search_tests -q`
Expected: PASS

Run: `cargo test keyboard_neighbor_replace_costs_less_than_arbitrary_replace --test search_tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/src/mutations.rs string-permutation-kata/rust/src/lib.rs string-permutation-kata/rust/tests/search_tests.rs
git commit -m "feat: generate weighted one-edit mutations"
```

## Task 4: Implement Layered Search And Deduplication

**Files:**
- Modify: `string-permutation-kata/rust/src/search.rs`
- Modify: `string-permutation-kata/rust/src/lib.rs`
- Test: `string-permutation-kata/rust/tests/search_tests.rs`

- [ ] **Step 1: Write failing search tests**

```rust
#[test]
fn excludes_seed_when_min_distance_is_one() {
    let config = SearchConfig::new("ab", b"ab".to_vec(), 1, 1, KeyboardNeighbors::empty()).unwrap();
    let result = enumerate_candidates(&config).unwrap();
    assert!(!result.contains(&"ab".to_string()));
}

#[test]
fn orders_distance_before_likelihood() {
    let config = SearchConfig::new(
        "ab",
        b"abc".to_vec(),
        1,
        2,
        KeyboardNeighbors::from_pairs(&[(b'a', b"b")]),
    )
    .unwrap();

    let result = enumerate_candidates(&config).unwrap();
    let one_edit_index = result.iter().position(|item| item == "bb").unwrap();
    let two_edit_index = result.iter().position(|item| item == "cbc").unwrap();

    assert!(one_edit_index < two_edit_index);
}

#[test]
fn deduplicates_candidates_reachable_by_multiple_paths() {
    let config = SearchConfig::new("aa", b"ab".to_vec(), 1, 2, KeyboardNeighbors::empty()).unwrap();
    let result = enumerate_candidates(&config).unwrap();
    let count = result.iter().filter(|item| *item == "a").count();
    assert_eq!(count, 1);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test --test search_tests deduplicates_candidates_reachable_by_multiple_paths -q`
Expected: FAIL because `enumerate_candidates` is not implemented

- [ ] **Step 3: Implement layered search**

```rust
use rustc_hash::FxHashMap;
use rustc_hash::FxHashSet;

pub fn enumerate_candidates(config: &SearchConfig) -> Result<Vec<String>, String> {
    let mut visited: FxHashSet<Vec<u8>> = FxHashSet::default();
    let mut current_layer = vec![(config.seed.as_bytes().to_vec(), 0_u32)];
    let mut output = Vec::new();

    visited.insert(config.seed.as_bytes().to_vec());

    if config.min_distance == 0 {
        output.push(config.seed.clone());
    }

    for distance in 1..=config.max_distance {
        let mut next_layer_best: FxHashMap<Vec<u8>, u32> = FxHashMap::default();

        for (candidate, accumulated_cost) in &current_layer {
            for neighbor in one_edit_neighbors(candidate, config) {
                if visited.contains(&neighbor.candidate) {
                    continue;
                }

                let total_cost = accumulated_cost + neighbor.likelihood_cost;
                next_layer_best
                    .entry(neighbor.candidate)
                    .and_modify(|cost| {
                        if total_cost < *cost {
                            *cost = total_cost;
                        }
                    })
                    .or_insert(total_cost);
            }
        }

        let mut next_layer: Vec<(Vec<u8>, u32)> = next_layer_best.into_iter().collect();
        next_layer.sort_by(|left, right| {
            left.1
                .cmp(&right.1)
                .then_with(|| left.0.cmp(&right.0))
        });

        for (candidate, _) in &next_layer {
            visited.insert(candidate.clone());
        }

        if distance >= config.min_distance {
            for (candidate, _) in &next_layer {
                output.push(String::from_utf8(candidate.clone()).map_err(|err| err.to_string())?);
            }
        }

        current_layer = next_layer;
    }

    Ok(output)
}
```

- [ ] **Step 4: Run search tests**

Run: `cargo test --test search_tests -q`
Expected: PASS for the new search-ordering tests, with any remaining failures isolated to completeness edge cases

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/src/search.rs string-permutation-kata/rust/src/lib.rs string-permutation-kata/rust/tests/search_tests.rs
git commit -m "feat: add layered candidate enumeration"
```

## Task 5: Prove Completeness And Exact-Distance Behavior

**Files:**
- Modify: `string-permutation-kata/rust/tests/search_tests.rs`
- Modify: `string-permutation-kata/rust/src/search.rs`

- [ ] **Step 1: Write failing completeness tests**

```rust
#[test]
fn emits_exact_one_edit_neighborhood_for_small_alphabet() {
    let config = SearchConfig::new("a", b"ab".to_vec(), 1, 1, KeyboardNeighbors::empty()).unwrap();
    let result = enumerate_candidates(&config).unwrap();
    let expected = vec!["", "aa", "ab", "ba", "b"];
    assert_eq!(result, expected);
}

#[test]
fn supports_exact_distance_band() {
    let config = SearchConfig::new("ab", b"ab".to_vec(), 2, 2, KeyboardNeighbors::empty()).unwrap();
    let result = enumerate_candidates(&config).unwrap();
    assert!(result.iter().all(|candidate| candidate != "ab"));
    assert!(!result.is_empty());
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test emits_exact_one_edit_neighborhood_for_small_alphabet --test search_tests -q`
Expected: FAIL if insert/delete/replace/swap combinations produce duplicates or unstable ordering

- [ ] **Step 3: Tighten completeness and ordering behavior**

```rust
fn is_better_cost(candidate: &Vec<u8>, total_cost: u32, best: &mut FxHashMap<Vec<u8>, u32>) {
    best.entry(candidate.clone())
        .and_modify(|cost| {
            if total_cost < *cost {
                *cost = total_cost;
            }
        })
        .or_insert(total_cost);
}

// Use the helper above inside the search loop and keep:
// - global `visited` only at completed layer boundaries
// - best cost per candidate within the next layer
// - final sort by `(cost, bytes)`
```

- [ ] **Step 4: Run full tests**

Run: `cargo test --test search_tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/src/search.rs string-permutation-kata/rust/tests/search_tests.rs
git commit -m "test: verify bounded neighborhood completeness"
```

## Task 6: Benchmark And Optimize Hot Paths

**Files:**
- Create: `string-permutation-kata/rust/benches/search_bench.rs`
- Modify: `string-permutation-kata/rust/src/mutations.rs`
- Modify: `string-permutation-kata/rust/src/search.rs`

- [ ] **Step 1: Write the benchmark**

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use string_neighborhood_kata::{enumerate_candidates, KeyboardNeighbors, SearchConfig};

fn benchmark_medium_search(c: &mut Criterion) {
    let config = SearchConfig::new(
        "password",
        (b'a'..=b'z').collect(),
        1,
        2,
        KeyboardNeighbors::from_pairs(&[
            (b'a', b"sqwz"),
            (b's', b"awedx"),
            (b'p', b"ol"),
        ]),
    )
    .unwrap();

    c.bench_function("enumerate password distance 1..2", |b| {
        b.iter(|| {
            let result = enumerate_candidates(black_box(&config)).unwrap();
            black_box(result.len())
        })
    });
}

criterion_group!(benches, benchmark_medium_search);
criterion_main!(benches);
```

- [ ] **Step 2: Run benchmark to establish baseline**

Run: `cargo bench --bench search_bench`
Expected: benchmark completes and reports a stable baseline for repeated runs

- [ ] **Step 3: Optimize the hot path**

```rust
// Focus optimizations on:
// - preallocating candidate vectors with `Vec::with_capacity`
// - reusing temporary buffers where possible
// - keeping operations on `u8` slices instead of `String`
// - avoiding per-candidate UTF-8 conversion until final emission
// - using `FxHashSet` / `FxHashMap` consistently
```

- [ ] **Step 4: Re-run tests and benchmark**

Run: `cargo test --test search_tests -q && cargo bench --bench search_bench`
Expected: tests PASS and benchmark improves or stays stable with lower allocation churn

- [ ] **Step 5: Commit**

```bash
git add string-permutation-kata/rust/benches/search_bench.rs string-permutation-kata/rust/src/mutations.rs string-permutation-kata/rust/src/search.rs
git commit -m "perf: optimize bounded string search"
```

## Task 7: Document Usage In The Research Folder

**Files:**
- Modify: `string-permutation-kata/README.md`
- Modify: `string-permutation-kata/notes.md`

- [ ] **Step 1: Add implementation notes to the report**

```markdown
## Implementation Direction

The recommended implementation uses Rust with layered breadth-first enumeration over edit-distance bands. Internally it operates on byte vectors for performance and ranks candidates within each layer by cumulative likelihood cost.
```

- [ ] **Step 2: Record benchmark findings in notes**

```markdown
- Implemented Rust library crate under `string-permutation-kata/rust/`.
- Benchmarked bounded search on representative seeds.
- Confirmed byte-oriented search and fast hash sets are the main performance levers.
```

- [ ] **Step 3: Run final verification**

Run: `cargo test --test search_tests -q && cargo bench --bench search_bench`
Expected: tests PASS and benchmark completes

- [ ] **Step 4: Commit**

```bash
git add string-permutation-kata/README.md string-permutation-kata/notes.md
git commit -m "docs: record rust implementation direction"
```
