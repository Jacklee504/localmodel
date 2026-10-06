# Dataset

`train.jsonl`, `valid.jsonl` and `test.jsonl` contain small, original pipeline examples. These check the data path, not model quality. Each line uses MLX-LM chat messages with a user prompt and assistant implementation. Keep external benchmark tasks and solutions out of every split. For sourced examples, record source and license in a `source` field.

Run `scripts/validate_dataset.py` before training. Grow the dataset only after the baseline has been frozen and scored.
