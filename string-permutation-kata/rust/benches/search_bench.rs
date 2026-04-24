use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion};
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
