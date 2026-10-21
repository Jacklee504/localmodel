# Local model evaluation

Training is paused pending comparison of existing local models. The previous 30-task baseline and training artifacts remain available.

The new suite asks each model to handle the same ten fixture repositories. Response mode records its proposal and generation timing. Repository mode asks for complete replacement contents for changed files as JSON, applies allowed changes to a temporary fixture copy, runs the task's listed commands, and records their status, output, and a unified diff. Agent mode lets OpenCode edit a temporary copy of the fixture and then applies the same validation. A failed response parse is recorded as a classified failure. No response is treated as a successful code change until it has been applied and validated.

Each task has public validation the model can see and withheld validation it cannot. Withheld tests live in a `hidden` directory inside the fixture. They are excluded from the prompt, excluded from the agent's workspace, and copied in only after the change is applied. They are hashed into the suite identifier, so two suites that differ only in a hidden file are never treated as the same suite.

Every attempt records exactly one failure kind from a closed set: `http_error`, `timeout`, `truncated`, `unparseable`, `protocol_violation`, `disallowed_path`, `validation_failed`, or `none`. A failure kind describes what the harness observed, not how good the model is. A model that times out has not demonstrated poor coding, and `none` does not mean the task was solved well.

Manual review supplies a 0/1/2 score, requirement failures, notes, and correction count. A score of 2 means the task and its stated constraints are met, 1 means useful but incomplete, and 0 means failed. Review unrelated changes and unnecessary complexity even if validation passes. Correction count is entered by the reviewer; this harness runs one model attempt per task and does not conduct an automatic repair loop. A first-pass success has score 2 and zero corrections. Unscored records stay unscored in reports.

The comparison command requires an identical comparison key: protocol version, mode, suite hash, task IDs and order, prompt version, the common generation settings, the required context, and the repair policy. When two runs differ it names the differing field instead of producing a wrong comparison. Runs that predate this key are legacy results and are excluded from current comparisons.

Model timing is approximate. Endpoint token counts come from provider usage and are never estimated. Time to first token is measured from the streaming response. Peak memory is not sampled in the harness; the served context and VRAM are read from the Ollama server and recorded in the run metadata instead.

Models are configured in `config/models.json`. MLX models require an existing local path. OpenAI-compatible models require a running local server and a served model ID; optional `api_key_env` names an environment variable. Configuration does not download weights or start servers. Paths and endpoints in the candidate entries are placeholders to edit after installing the models.
