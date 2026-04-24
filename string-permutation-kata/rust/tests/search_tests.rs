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
