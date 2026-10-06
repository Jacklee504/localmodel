"""One inference path for base and adapter runs."""

import argparse
import sys

from check_environment import check, model_path

MAX_TOKENS = 512


def load_inference(model_path_value, adapter=None):
    from mlx_lm import load
    return load(model_path_value, adapter_path=adapter)


def respond(model, tokenizer, prompt, max_tokens=MAX_TOKENS):
    from mlx_lm import generate

    chat = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
    )
    return generate(model, tokenizer, chat, max_tokens=max_tokens, verbose=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=model_path())
    parser.add_argument("--adapter")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    args = parser.parse_args()
    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    if not check(args.model):
        sys.exit(1)
    try:
        model, tokenizer = load_inference(args.model, args.adapter)
        print(respond(model, tokenizer, args.prompt, args.max_tokens))
    except Exception as exc:
        parser.exit(1, f"Inference failed: {exc}\n")
