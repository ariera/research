use std::sync::Arc;

use crate::keyboard::KeyboardNeighbors;

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
