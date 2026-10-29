"""Central settings for ProbateOfficer.

Every tunable value and every file path lives here, so the rest of the code
imports from one place and nothing hard-codes a model name or a folder.
"""

from pathlib import Path

# The project root is the folder this file sits in. Paths below are built from it,
# so the project works wherever it is cloned.
ROOT = Path(__file__).resolve().parent

# The only model used at runtime and in evals (including the LLM judge).
MODEL = "claude-haiku-5-5"
MAX_TOKENS = 1024
# Stops the agent loop from running forever if the model never finishes.
MAX_TURNS = 8

# Prices in USD per million tokens for claude-haiku-5-5, prompts up to 100K tokens.
# Source: https://claude.com/pricing ("Prompts ≤ 100K tokens": $0.10 input, $0.50 output).
# Prompts over 100K tokens cost more ($0.50 input, $2.50 output). Our prompts are a few thousand tokens.
PRICE_IN_PER_M = 0.10
PRICE_OUT_PER_M = 0.50

# Only these case states can be processed. Anything else is refused in code, before any API call.
IN_SCOPE_STATES = {"issued", "stopped"}

DATA_DIR = ROOT / "data"
CASES_DIR = DATA_DIR / "cases"
GOLDEN_DIR = DATA_DIR / "golden"
RULES_PATH = DATA_DIR / "rules.yaml"
TEMPLATES_DIR = DATA_DIR / "templates"
OUTBOX_DIR = DATA_DIR / "outbox"
PREFS_PATH = DATA_DIR / "preferences.jsonl"
LOG_PATH = ROOT / "logs" / "trace.jsonl"
RESULTS_DIR = ROOT / "evals" / "results"

# Number of repeated runs per case in evals, and the random seed used everywhere.
EVAL_K = 3
SEED = 42
