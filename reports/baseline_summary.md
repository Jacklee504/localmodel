# V1 baseline summary

Benchmark SHA-256: `da6167e89cbc333b23a21b90164db7d91337703831f9f726b270e7ad2d6067f6`
Model: `/Users/jacklee/Other/Me/Projects/local-coder/models/qwen2.5-coder-7b-instruct-4bit`
Generation: `{"chat_template": "tokenizer default", "max_tokens": 512, "sampler": "greedy"}`

| Category | Tasks | Correct | Correct rate | Mean score | Constraints met | Code correct |
|---|---:|---:|---:|---:|---:|---:|
| overall | 30 | 11 | 36.7% | 1.07 | 36.7% | 36.7% |
| java | 3 | 1 | 33.3% | 0.67 | 33.3% | 33.3% |
| multi_file_reasoning | 4 | 3 | 75.0% | 1.75 | 75.0% | 75.0% |
| python_debugging | 5 | 2 | 40.0% | 1.00 | 40.0% | 40.0% |
| python_implementation | 6 | 2 | 33.3% | 1.00 | 33.3% | 33.3% |
| refactoring | 3 | 2 | 66.7% | 1.67 | 66.7% | 66.7% |
| typescript_javascript | 5 | 1 | 20.0% | 1.00 | 20.0% | 20.0% |
| unit_test_generation | 4 | 0 | 0.0% | 0.50 | 0.0% | 0.0% |

## Review method and limits

The 30 saved responses were manually reviewed against the frozen task prompts. A score of 2 means the supplied code meets the stated behavior; 1 means useful but incomplete; 0 means unusable or fundamentally incorrect. Notes for every decision are in `benchmarks/baseline/baseline/scores.jsonl`. The raw responses were not changed. No hidden test suite was run against the generated code, so these figures are a manual baseline rather than a verified execution pass rate.

Several failures are clear from the response itself: `pyi-03` calls `fsync` after closing the file, `pyd-05` calls `len` on a one-shot iterable, `test-02` checks the wrong sleep function, `js-04` accepts partial numeric strings, and `java-01` uses a nonexistent `HashSet` constructor. The `java-03` response is truncated at the 512-token generation limit and contains compilation and Unicode handling errors before the truncation. These failures should remain in the frozen baseline when later comparing the adapter.
