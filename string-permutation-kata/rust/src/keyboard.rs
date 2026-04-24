use rustc_hash::FxHashMap;

#[derive(Clone, Debug, Default)]
pub struct KeyboardNeighbors {
    by_key: FxHashMap<u8, Box<[u8]>>,
}

impl KeyboardNeighbors {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn from_pairs(pairs: &[(u8, &[u8])]) -> Self {
        let mut by_key = FxHashMap::default();
        for (key, neighbors) in pairs {
            by_key.insert(*key, neighbors.to_vec().into_boxed_slice());
        }
        Self { by_key }
    }

    pub fn contains_neighbor(&self, source: u8, target: u8) -> bool {
        self.by_key
            .get(&source)
            .map(|neighbors| neighbors.contains(&target))
            .unwrap_or(false)
    }
}
