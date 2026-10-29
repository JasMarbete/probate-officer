"""The only module that talks to the Anthropic API.

Every model call in the project goes through `call()`. That gives one place for
retries, usage counting and cost. Tests replace `call()` with a fake, so they
never need an API key.
"""

import sys
import time

import anthropic
from dotenv import load_dotenv

import config

# Read ANTHROPIC_API_KEY from .env, so every entry point (cli, evals, scripts) finds the key.
load_dotenv(config.ROOT / ".env")

# Three attempts in total. Waits of 2s and then 4s go between them.
ATTEMPTS = 3
BACKOFF_SECONDS = (2, 4)
# 429 is a rate limit. 529 means the API is overloaded.
RETRYABLE_STATUS = {429, 529}

# Running totals across calls. `cli.py` resets them before each run.
USAGE = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

# The client is created on first use, so importing this module needs no API key.
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def reset_usage():
    USAGE.update(input_tokens=0, output_tokens=0, calls=0)


def _is_retryable(error):
    # RateLimitError is a subclass of APIStatusError, so one check covers both.
    return isinstance(error, anthropic.APIStatusError) and error.status_code in RETRYABLE_STATUS


def call(system, messages, tools=None, tool_choice=None):
    """Send one request to Haiku and return the SDK response."""
    kwargs = {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "system": system,
        "messages": messages,
    }
    # Only send tool fields when they are set. Sending empty ones would change the request.
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    for attempt in range(ATTEMPTS):
        try:
            response = _get_client().messages.create(**kwargs)
            break
        except anthropic.APIStatusError as error:
            # Only rate limits and overload are retried. Anything else is a real error, so raise it.
            if not _is_retryable(error) or attempt == ATTEMPTS - 1:
                raise
            time.sleep(BACKOFF_SECONDS[attempt])

    USAGE["input_tokens"] += response.usage.input_tokens
    USAGE["output_tokens"] += response.usage.output_tokens
    USAGE["calls"] += 1
    return response


# Set after the first warning, so an eval run prints it once rather than once per case.
_price_warning_shown = False


def cost_usd(usage=USAGE):
    """Cost in USD from token counts and the prices in config.py."""
    global _price_warning_shown
    if config.PRICE_IN_PER_M == 0 and config.PRICE_OUT_PER_M == 0 and not _price_warning_shown:
        print("warning: prices in config.py are 0, so the cost shown is 0. Fill them in from Anthropic's pricing page.", file=sys.stderr)
        _price_warning_shown = True
    return (
        usage["input_tokens"] * config.PRICE_IN_PER_M / 1_000_000
        + usage["output_tokens"] * config.PRICE_OUT_PER_M / 1_000_000
    )
