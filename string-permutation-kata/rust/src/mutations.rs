use crate::config::SearchConfig;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NeighborCandidate {
    pub candidate: Vec<u8>,
    pub likelihood_cost: u32,
}

pub fn for_each_one_edit_neighbor<F>(seed: &[u8], config: &SearchConfig, mut emit: F)
where
    F: FnMut(&[u8], u32),
{
    let mut scratch: Vec<u8> = Vec::with_capacity(seed.len() + 1);

    for index in 0..seed.len() {
        scratch.clear();
        scratch.extend_from_slice(&seed[..index]);
        scratch.extend_from_slice(&seed[index + 1..]);
        emit(&scratch, 2);
    }

    for index in 0..=seed.len() {
        for &byte in config.alphabet.iter() {
            scratch.clear();
            scratch.extend_from_slice(&seed[..index]);
            scratch.push(byte);
            scratch.extend_from_slice(&seed[index..]);
            emit(&scratch, 2);
        }
    }

    for index in 0..seed.len() {
        let original = seed[index];
        for &byte in config.alphabet.iter() {
            if byte == original {
                continue;
            }
            scratch.clear();
            scratch.extend_from_slice(seed);
            scratch[index] = byte;
            let likelihood_cost = if config.keyboard_neighbors.contains_neighbor(original, byte) {
                1
            } else {
                3
            };
            emit(&scratch, likelihood_cost);
        }
    }

    for index in 0..seed.len().saturating_sub(1) {
        if seed[index] == seed[index + 1] {
            continue;
        }
        scratch.clear();
        scratch.extend_from_slice(seed);
        scratch.swap(index, index + 1);
        emit(&scratch, 1);
    }
}

pub fn one_edit_neighbors(seed: &[u8], config: &SearchConfig) -> Vec<NeighborCandidate> {
    let mut out = Vec::new();
    for_each_one_edit_neighbor(seed, config, |bytes, cost| {
        out.push(NeighborCandidate {
            candidate: bytes.to_vec(),
            likelihood_cost: cost,
        });
    });
    out
}
