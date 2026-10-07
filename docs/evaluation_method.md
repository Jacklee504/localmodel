# Local model evaluation

Training is paused pending comparison of existing local models. The previous 30-task baseline and training artifacts remain available.

The new suite asks each model to handle the same ten fixture repositories. Response mode records its proposal and generation timing. Repository mode asks for complete replacement contents for changed files as JSON, applies allowed changes to a temporary fixture copy, runs the task's listed commands, and records their status, output, and a unified diff. A failed response parse is recorded as an execution error. No response is treated as a successful code change until it has been applied and validated.

Manual review supplies a 0/1/2 score, requirement failures, notes, and correction count. A score of 2 means the task and its stated constraints are met, 1 means useful but incomplete, and 0 means failed. Review unrelated changes and unnecessary complexity even if validation passes. Correction count is entered by the reviewer; this harness runs one model attempt per task and does not conduct an automatic repair loop. A first-pass success has score 2 and zero corrections. Unscored records stay unscored in reports.

The comparison command requires identical task IDs, mode, generation settings, and hashes of the task definition plus fixtures. It reports objective repository validation separately from manual success. Model timing is approximate. MLX token count is calculated from the response; endpoint token count uses provider usage when supplied. Time to first token and peak memory remain null where unavailable. A nonstreaming endpoint response cannot give a reliable first-token time.

Models are configured in `config/models.json`. MLX models require an existing local path. OpenAI-compatible models require a running local server and a served model ID; optional `api_key_env` names an environment variable. Configuration does not download weights or start servers. Paths and endpoints in the candidate entries are placeholders to edit after installing the models.
