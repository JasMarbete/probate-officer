"""Send one short message to Haiku to check that the API key and model work.

Run it with `python scripts/ping.py`. It prints the reply and the token usage.
It makes exactly one API call, so it needs no cost-guard confirmation.
"""

import os
import sys
from pathlib import Path

# Make the project root importable, so `import config` works when run from any folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
from dotenv import load_dotenv

import config

# Read ANTHROPIC_API_KEY from the .env file in the project root, if it exists.
load_dotenv(config.ROOT / ".env")


def main():
    # Fail with a clear message instead of a stack trace when the key is missing.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key.")
        return 1

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[{"role": "user", "content": "Reply with OK"}],
    )

    # Print each text block of the reply, then the token counts from the usage field.
    for block in response.content:
        if block.type == "text":
            print("Reply:", block.text)
    print("Model:", response.model)
    print("Input tokens:", response.usage.input_tokens)
    print("Output tokens:", response.usage.output_tokens)
    return 0


if __name__ == "__main__":
    sys.exit(main())
