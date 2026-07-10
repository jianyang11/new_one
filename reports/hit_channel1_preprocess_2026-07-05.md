# HIT Channel-1 Preprocess

Date: 2026-07-05

Source: `https://github.com/HouLeiHIT/HIT-dataset`

The repository README describes these files as Channel 1 example data from an
inter-shaft bearing fault diagnosis dataset. The full dataset is linked through
Google Drive, but the GitHub repository itself contains four train shards,
one test shard, and labels.

Outputs:

- `proc/hit_channel1_train.npz`: (9648, 1, 2048)
- `proc/hit_channel1_test.npz`: (2412, 1, 2048)
- `analysis/hit_channel1_manifest_2026-07-05.csv`

Label counts:

- train: {"0": 3816, "1": 4032, "2": 1800}
- test: {"0": 954, "1": 1008, "2": 450}

Limitation: the README does not define the physical meaning of labels 0/1/2 in
the GitHub channel-1 example. This subset can support classifier plumbing and a
supervised benchmark with anonymous classes, but it cannot support a physical
fault-generation claim until label semantics and full-channel metadata are
verified.
