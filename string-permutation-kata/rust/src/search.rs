use crate::config::SearchConfig;
use crate::mutations::one_edit_neighbors;
use rustc_hash::{FxHashMap, FxHashSet};

pub fn enumerate_candidates(config: &SearchConfig) -> Result<Vec<String>, String> {
    let mut visited: FxHashSet<Vec<u8>> = FxHashSet::default();
    let mut current_layer: Vec<(Vec<u8>, u32)> = vec![(config.seed.as_bytes().to_vec(), 0)];
    let mut output: Vec<String> = Vec::new();

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
        next_layer.sort_by(|left, right| left.1.cmp(&right.1).then_with(|| left.0.cmp(&right.0)));

        for (candidate, _) in &next_layer {
            visited.insert(candidate.clone());
        }

        if distance >= config.min_distance {
            for (candidate, _) in &next_layer {
                output.push(
                    String::from_utf8(candidate.clone()).map_err(|err| err.to_string())?,
                );
            }
        }

        current_layer = next_layer;
    }

    Ok(output)
}
