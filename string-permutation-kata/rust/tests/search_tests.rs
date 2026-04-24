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
