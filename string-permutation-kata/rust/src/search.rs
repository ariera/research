use crate::config::SearchConfig;
use crate::mutations::for_each_one_edit_neighbor;
use rustc_hash::{FxHashMap, FxHashSet};

pub fn enumerate_candidates(config: &SearchConfig) -> Result<Vec<String>, String> {
    let seed_bytes = config.seed.as_bytes().to_vec();
    let mut visited: FxHashSet<Vec<u8>> = FxHashSet::default();
    visited.insert(seed_bytes.clone());

    let mut current_layer: Vec<(Vec<u8>, u32)> = vec![(seed_bytes, 0)];
    let mut output: Vec<String> = Vec::new();

    if config.min_distance == 0 {
        output.push(config.seed.clone());
    }

    for distance in 1..=config.max_distance {
        let mut next_layer_best: FxHashMap<Vec<u8>, u32> =
            FxHashMap::with_capacity_and_hasher(current_layer.len() * 16, Default::default());

        for (candidate, accumulated_cost) in &current_layer {
            let accumulated_cost = *accumulated_cost;
            for_each_one_edit_neighbor(candidate, config, |neighbor_bytes, cost| {
                if visited.contains(neighbor_bytes) {
                    return;
                }
                let total_cost = accumulated_cost + cost;
                match next_layer_best.get_mut(neighbor_bytes) {
                    Some(existing) => {
                        if total_cost < *existing {
                            *existing = total_cost;
                        }
                    }
                    None => {
                        next_layer_best.insert(neighbor_bytes.to_vec(), total_cost);
                    }
                }
            });
        }

        let mut next_layer: Vec<(Vec<u8>, u32)> = next_layer_best.into_iter().collect();
        next_layer.sort_unstable_by(|left, right| {
            left.1.cmp(&right.1).then_with(|| left.0.cmp(&right.0))
        });

        for (candidate, _) in &next_layer {
            visited.insert(candidate.clone());
        }

        if distance >= config.min_distance {
            output.reserve(next_layer.len());
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
