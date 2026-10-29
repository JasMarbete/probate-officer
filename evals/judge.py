"""LLM judge for the letters the agent drafts, plus calibration against the owner's hand scores.

The judge scores each letter on three things: asks for every missing document, asks
for nothing extra, and plain English (1 to 5). Calibration measures how often the
judge agrees with the owner on the same letters. It needs 15 hand-scored letters in
evals/human_scores.jsonl, which is an owner input (spec Section 14). Without them,
calibration reports that it did not run.

Usage:
  python -m evals.judge --run evals/results/<folder>             score the letters in one agent_write run
  python -m evals.judge --calibrate --run evals/results/<folder>  also compare with the owner's scores
  python -m evals.judge --export --run evals/results/<folder>     write the letters for hand scoring
"""

import argparse
import json
import sys
from pathlib import Path

import config
from officer import llm, prompts

HUMAN_SCORES = config.ROOT / "evals" / "human_scores.jsonl"

RECORD_LETTER_SCORE_TOOL = {
    "name": "record_letter_score",
    "description": "Record how well the letter asks for the missing documents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "correct_documents": {"type": "boolean"},
            "nothing_invented": {"type": "boolean"},
            "plain_english": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["correct_documents", "nothing_invented", "plain_english"],
    },
}


def judge_letter(letter_text, missing):
    """Score one letter against the list of documents that are actually missing."""
    response = llm.call(
        prompts.LETTER_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": f"<letter>{letter_text}</letter>\n<missing_documents>{json.dumps(missing)}</missing_documents>"}],
        tools=[RECORD_LETTER_SCORE_TOOL],
        tool_choice={"type": "tool", "name": "record_letter_score"},
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_letter_score":
            score = block.input
            # Keep the scale in range even if the model strays outside it.
            score["plain_english"] = min(5, max(1, int(score["plain_english"])))
            return score
    return {"error": "the judge did not return a score"}


def score_run(rows):
    """Score every letter in an agent_write run. Returns {letter_id: score}."""
    scores = {}
    for row in rows:
        for letter in row.get("letters", []):
            scores[letter["id"]] = judge_letter(letter["text"], letter["missing"])
    return scores


def calibrate(judge_scores, human_path=HUMAN_SCORES):
    """Agreement with the owner's scores. Bools must match exactly, and the 1-to-5 scale must match within 1."""
    if not human_path.exists():
        return None
    human = [json.loads(line) for line in human_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = [(h, judge_scores[h["letter_id"]]) for h in human if h["letter_id"] in judge_scores and "error" not in judge_scores[h["letter_id"]]]
    if not pairs:
        return {"compared": 0}
    bool_match = sum(
        (h["correct_documents"] == j["correct_documents"]) + (h["nothing_invented"] == j["nothing_invented"])
        for h, j in pairs
    )
    scale_match = sum(abs(h["plain_english"] - j["plain_english"]) <= 1 for h, j in pairs)
    return {
        "compared": len(pairs),
        "bool_agreement": bool_match / (2 * len(pairs)),
        "scale_agreement_within_1": scale_match / len(pairs),
    }


def export_letters(rows, out_path):
    """Write every drafted letter to a readable file, with its missing documents and a blank score line to fill in."""
    lines = ["# Letters to score by hand", "",
             "For each letter, copy its score line into evals/human_scores.jsonl and fill in the three values.",
             "correct_documents: true if the letter asks for every missing document.",
             "nothing_invented: true if it asks for nothing beyond the missing list.",
             "plain_english: 1 (confusing) to 5 (clear, polite, plain English).", ""]
    count = 0
    for row in rows:
        for letter in row.get("letters", []):
            count += 1
            lines += [f"## {letter['id']}", "", f"Missing documents: {', '.join(letter['missing']) or 'none'}", "",
                      "> " + letter["text"].replace("\n", "\n> "), "",
                      "```json",
                      json.dumps({"letter_id": letter["id"], "correct_documents": None,
                                  "nothing_invented": None, "plain_english": None}),
                      "```", ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score drafted letters with the LLM judge.")
    parser.add_argument("--run", required=True, help="an agent_write results folder")
    parser.add_argument("--calibrate", action="store_true", help="compare with evals/human_scores.jsonl")
    parser.add_argument("--export", action="store_true", help="write the letters to evals/letters_to_score.md for hand scoring")
    args = parser.parse_args(argv)

    if args.export:
        rows = [json.loads(line) for line in (Path(args.run) / "rows.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        out = config.ROOT / "evals" / "letters_to_score.md"
        count = export_letters(rows, out)
        print(f"Wrote {count} letter(s) to {out.relative_to(config.ROOT)}")
        return 0

    rows = [json.loads(line) for line in (Path(args.run) / "rows.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    scores = score_run(rows)
    (Path(args.run) / "judge_scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    print(f"Scored {len(scores)} letter(s). Written to {Path(args.run) / 'judge_scores.json'}")

    if args.calibrate:
        result = calibrate(scores)
        if result is None:
            print(f"Calibration did not run: {HUMAN_SCORES.relative_to(config.ROOT)} is missing. It needs 15 hand-scored letters (owner input).")
        else:
            print(f"Calibration: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
