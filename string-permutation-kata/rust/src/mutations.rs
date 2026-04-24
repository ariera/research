use crate::config::SearchConfig;

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
        out.push(NeighborCandidate {
            candidate,
            likelihood_cost: 2,
        });
    }

    for index in 0..=seed.len() {
        for &byte in config.alphabet.iter() {
            let mut candidate = seed.to_vec();
            candidate.insert(index, byte);
            out.push(NeighborCandidate {
                candidate,
                likelihood_cost: 2,
            });
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
            out.push(NeighborCandidate {
                candidate,
                likelihood_cost,
            });
        }
    }

    for index in 0..seed.len().saturating_sub(1) {
        if seed[index] == seed[index + 1] {
            continue;
        }
        let mut candidate = seed.to_vec();
        candidate.swap(index, index + 1);
        out.push(NeighborCandidate {
            candidate,
            likelihood_cost: 1,
        });
    }

    out
}
