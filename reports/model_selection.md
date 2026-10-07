# Local model selection

Status: pending candidate runs. Training remains paused.

The Qwen3.5-9B, Qwen3.8-27B, and Qwen3-Coder-30B-A3B weights are not installed in this repository. No comparison or recommendation among them is supported yet. Run the response and repository suites for each feasible candidate, manually score requirement adherence, and use `scripts/evaluate.py compare` on matching runs. Record the best overall model, difficult-task model, routine-work model, whether maintaining two is worthwhile, repeated weaknesses, and whether any weakness justifies returning to fine-tuning.

The installed Qwen2.5-Coder-7B is available as a workflow check when Metal is accessible. The attempted run in this execution session stopped before inference because MLX reported no Metal device. It is a reference model rather than one of the three selection candidates.
