# Practical task suite

`core.json` defines ten small, self-contained repository tasks. Fixtures are sanitized and contain no model weights or credentials. The suite is separate from the frozen 30-task benchmark in `benchmarks/`.

Each task has a prompt, an allowlist of files a model may change, and explicit validation commands. Repository mode copies the fixture to a temporary directory, applies only allowlisted full-file replacements from the model's JSON response, executes validation there, and saves the diff and output. The temporary copy is removed afterward. Tests are visible to the model; passing them is useful evidence, not a complete correctness judgement. Review requirement adherence manually.

`source` describes the development workflow or sanitized pattern that motivated a task. Several tasks come from this repository's configuration, result scoring, and task loading workflows. The remaining fixtures are compact stand-ins for report caching, HTTP retries, web search, Java collections, and API boundaries. They contain no copied private repository content.
