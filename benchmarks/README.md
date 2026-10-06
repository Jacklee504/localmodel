# Frozen benchmark

`tasks.jsonl` is the external evaluation set. Do not edit tasks after seeing model responses. Each task asks for a concrete code change or test. Responses are scored manually on 0, 1, 2, with notes; `constraints_met` and `code_correct` track the two specific V1 questions. Runs save the task SHA-256, model path, adapter, generation settings and raw responses. The comparator rejects mismatched task hashes or generation settings.

Run names must be unique. A generated score template has null fields so missing review cannot be confused with zero. Record final baseline metrics in `reports/baseline_summary.md` when available and commit that summary with the benchmark definition before real training.
