use string_neighborhood_kata::{enumerate_candidates, KeyboardNeighbors, SearchConfig};

#[test]
fn unicode_seed_does_not_break_candidate_enumeration() {
    let config = SearchConfig::new(
        "é",
        vec!['é', 'a'],
        1,
        1,
        KeyboardNeighbors::empty(),
    )
    .unwrap();

    let result = enumerate_candidates(&config);

    assert!(
        result.is_ok(),
        "valid string inputs should not make enumeration fail: {result:?}",
    );
    let emitted = result.unwrap();
    assert!(emitted.iter().any(|candidate| candidate == "a"));
    assert!(emitted.iter().any(|candidate| candidate == "aé"));
}

#[test]
fn alphabet_is_typed_as_unicode_characters() {
    let config = SearchConfig::new(
        "a",
        vec!['a', 'é'],
        0,
        1,
        KeyboardNeighbors::empty(),
    );

    assert!(
        config.is_ok(),
        "character-typed alphabets should be accepted: {config:?}",
    );
}
