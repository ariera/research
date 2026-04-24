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

#[test]
fn identical_adjacent_swap_does_not_emit_seed() {
    let config = SearchConfig::new("aa", b"a".to_vec(), 1, 1, KeyboardNeighbors::empty()).unwrap();

    let neighbors = string_neighborhood_kata::one_edit_neighbors(config.seed.as_bytes(), &config);

    assert!(!neighbors.iter().any(|item| item.candidate == b"aa".to_vec()));
}
