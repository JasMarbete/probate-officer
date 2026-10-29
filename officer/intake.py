"""A very basic email interpreter: reads one incoming email and plans the CCD tool calls it would make.

This is a dry run. Nothing is sent, and there is no CCD connection yet, so every
planned action has `executed: False`. Writes are PROPOSE actions, which a human
must approve, in line with the spec's "propose, don't act" rule.

The method is plain pattern matching, with no model call. That is deliberate:
it is easy to explain, and it shows what the parser found.
The email text is data. It can change what is planned, but it cannot approve anything.
"""

import re

# "case reference XXXX" with optional colon or hash. Accepts any reasonable reference token.
CASE_REF = re.compile(r"case\s+reference\s*[:#]?\s*([A-Za-z0-9-]{6,})", re.IGNORECASE)
STATUS_WORDS = re.compile(r"\b(update|updates|status|progress|any news|where are we)\b", re.IGNORECASE)
DOCUMENT_WORDS = re.compile(r"\b(attached|attachment|enclosed|document below)\b", re.IGNORECASE)
STATEMENT_WORD = re.compile(r"\bstatement\b", re.IGNORECASE)
# "reserves power", "reserved the power", "power reserved" and similar.
POWER_RESERVED = re.compile(r"\b(reserv\w*\s+(?:the\s+)?power|power\s+(?:is\s+|was\s+)?reserved)\b", re.IGNORECASE)


def _sentences(text):
    # Split on sentence-ending punctuation or line breaks, and drop empty pieces.
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _action(tool, kind, tool_input, expected_output):
    # One planned tool call. It records what would be sent and what should come back, and is never run.
    return {
        "tool": tool,
        "kind": kind,
        "input": tool_input,
        "expected_output": expected_output,
        "executed": False,
        "note": "CCD is not connected. Dry run only.",
    }


def _plan(case_ref, intents, document, facts):
    if case_ref is None:
        # Without a reference, the only safe step is to hand the email to a person.
        return [_action("ccd_flag_for_officer", "PROPOSE",
                        {"reason": "no case reference found in the email"},
                        {"status": "string"})]

    actions = [_action("ccd_lookup_case", "READ",
                       {"case_reference": case_ref},
                       {"case_id": "string", "state": "string", "last_update": "date"})]
    if "document_submitted" in intents:
        actions.append(_action("ccd_record_document", "PROPOSE",
                               {"case_reference": case_ref,
                                "document_type": document["type_guess"] or "unknown",
                                "source": "applicant email",
                                "file_received": document["file_received"]},
                               {"status": "string"}))
    if facts:
        actions.append(_action("ccd_add_note", "PROPOSE",
                               {"case_reference": case_ref,
                                "note": facts[0]["text"] + " (applicant report, not verified)"},
                               {"status": "string"}))
    if "status_enquiry" in intents:
        actions.append(_action("ccd_draft_status_reply", "PROPOSE",
                               {"case_reference": case_ref, "topics": ["case update"]},
                               {"status": "string", "sent": False}))
    if facts:
        # A fact the system cannot check goes to an officer, never decided here.
        actions.append(_action("ccd_flag_for_officer", "PROPOSE",
                               {"case_reference": case_ref,
                                "reason": "applicant reports a fact that needs checking"},
                               {"status": "string"}))
    return actions


def interpret(text):
    """Parse one email and return what it asks for, plus the planned tool calls. Nothing is executed."""
    sentences = _sentences(text)
    match = CASE_REF.search(text)
    case_ref = match.group(1) if match else None

    intents = []
    if STATUS_WORDS.search(text):
        intents.append("status_enquiry")
    if DOCUMENT_WORDS.search(text):
        intents.append("document_submitted")
    # The case-reference clause is not part of the fact, so it is removed from the sentence.
    facts = [{"text": CASE_REF.sub("", s).strip(" ,"), "verified": False} for s in sentences if POWER_RESERVED.search(s)]
    if facts:
        intents.append("reported_fact")

    document_mentioned = bool(DOCUMENT_WORDS.search(text))
    document = {
        "mentioned": document_mentioned,
        "type_guess": "statement" if STATEMENT_WORD.search(text) else None,
        # No attachment comes in with the text, so no file is ever received here.
        "file_received": False,
    }

    warnings = []
    if case_ref is None:
        warnings.append("No case reference found. A person must identify the case before any CCD call.")
    if document_mentioned:
        warnings.append("The email says a document is attached, but no file came with it.")
    if facts:
        warnings.append("The reported fact is not checked against any record. It is flagged for an officer.")

    return {
        "case_reference": case_ref,
        "intents": intents,
        "requests": [s for s in sentences if STATUS_WORDS.search(s)],
        "document": document,
        "reported_facts": facts,
        "warnings": warnings,
        "planned_actions": _plan(case_ref, intents, document, facts),
        "sent": False,
    }
