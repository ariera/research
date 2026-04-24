use crate::config::SearchConfig;
use crate::mutations::for_each_one_edit_neighbor;
use rustc_hash::{FxHashMap, FxHashSet};

pub fn enumerate_candidates(config: &SearchConfig) -> Result<Vec<String>, String> {
    let seed_chars: Vec<char> = config.seed_chars.iter().copied().collect();
    let mut visited: FxHashSet<Vec<char>> = FxHashSet::default();
    visited.insert(seed_chars.clone());

    let mut current_layer: Vec<(Vec<char>, u32)> = vec![(seed_chars, 0)];
    let mut output: Vec<String> = Vec::new();

    if config.min_distance == 0 {
        output.push(config.seed.clone());
    }

    for distance in 1..=config.max_distance {
        let mut next_layer_best: FxHashMap<Vec<char>, u32> =
            FxHashMap::with_capacity_and_hasher(current_layer.len() * 16, Default::default());

        for (candidate, accumulated_cost) in &current_layer {
            let accumulated_cost = *accumulated_cost;
            for_each_one_edit_neighbor(candidate, config, |neighbor_chars, cost| {
                if visited.contains(neighbor_chars) {
                    return;
                }
                let total_cost = accumulated_cost + cost;
                match next_layer_best.get_mut(neighbor_chars) {
                    Some(existing) => {
                        if total_cost < *existing {
                            *existing = total_cost;
                        }
                    }
                    None => {
                        next_layer_best.insert(neighbor_chars.to_vec(), total_cost);
                    }
                }
            });
        }

        let mut next_layer: Vec<(Vec<char>, u32)> = next_layer_best.into_iter().collect();
        next_layer.sort_unstable_by(|left, right| {
            left.1.cmp(&right.1).then_with(|| left.0.cmp(&right.0))
        });

        for (candidate, _) in &next_layer {
            visited.insert(candidate.clone());
        }

        if distance >= config.min_distance {
            output.reserve(next_layer.len());
            for (candidate, _) in &next_layer {
                output.push(candidate.iter().collect());
            }
        }

        current_layer = next_layer;
    }

    Ok(output)
}
