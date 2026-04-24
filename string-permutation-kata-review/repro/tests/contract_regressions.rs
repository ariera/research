use string_neighborhood_kata::{enumerate_candidates, KeyboardNeighbors, SearchConfig};

#[test]
fn unicode_seed_does_not_break_candidate_enumeration() {
    let config = SearchConfig::new(
        "é",
        "é".as_bytes().to_vec(),
        1,
        1,
        KeyboardNeighbors::empty(),
    )
    .unwrap();

    let result = enumerate_candidates(&config);

    assert!(
        result.is_ok(),
        "valid string inputs should not make enumeration fail with invalid UTF-8: {result:?}",
    );
}

#[test]
fn invalid_utf8_alphabet_is_rejected_before_search() {
    let result = SearchConfig::new("a", vec![b'a', 0xff], 1, 1, KeyboardNeighbors::empty());

    assert!(
        result.is_err(),
        "configuration should reject alphabet bytes that cannot produce valid strings",
    );
}
