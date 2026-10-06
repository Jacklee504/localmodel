# Dataset

`train.jsonl`, `valid.jsonl` and `test.jsonl` contain 100 original examples (71 train, 15 validation, 14 test). The first 20 were pipeline examples; the added examples cover more implementation, debugging, refactoring and test-writing cases. This remains a small offline pilot set, below the handoff's suggested 500–2,000 examples for the first real experiment. Each line uses MLX-LM chat messages with a user prompt and assistant implementation. New examples have `source: "original"`. Keep external benchmark tasks and solutions out of every split. For sourced examples, record source and license metadata.

Run `scripts/validate_dataset.py` before training. It checks structure, exact duplicates and basic benchmark overlap; it does not prove every target is correct or rule out semantic leakage. Review targets and any future sourced examples before a real training run.
