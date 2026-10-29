"""The approval gate: the only place where the agent's proposed writes can change a case.

The agent calls WRITE tools, and those become proposals here. Nothing changes until
a human calls `decide(..., approved=True)`. Then the action is checked against
ALLOWED_TRANSITIONS and applied to the case file.
"""

import json
from datetime import datetime

import config
from officer import audit, store

# The only state changes allowed. Any other move raises an error.
ALLOWED_TRANSITIONS = {
    "issued": {"stopped", "ready_for_examiner", "escalated"},
    "stopped": {"stopped", "ready_for_examiner", "escalated"},
}

# Which state each state-changing action moves the case to.
TARGET_STATE = {"stop_case": "stopped", "route_to_examiner": "ready_for_examiner", "escalate": "escalated"}


class Gate:
    """Holds the proposals for one agent run, and applies the ones a human approves."""

    def __init__(self, case_id, run_id):
        self.case_id = case_id
        self.run_id = run_id
        self.proposals = []

    def propose(self, action, args):
        """Queue a proposal. Changes nothing in the case."""
        proposal = {"id": len(self.proposals), "action": action, "args": args, "status": "pending"}
        self.proposals.append(proposal)
        audit.log(self.run_id, self.case_id, "proposal", proposal_id=proposal["id"], action=action, args=args)
        return {"status": "proposed", "proposal_id": proposal["id"], "message": "Queued for human approval."}

    def decide(self, proposal_id, approved, note=""):
        """A human approves or rejects one proposal. Approval applies it. Each proposal can be decided once."""
        proposal = self.proposals[proposal_id]
        if proposal["status"] != "pending":
            raise ValueError(f"proposal {proposal_id} is already {proposal['status']}")
        proposal["status"] = "approved" if approved else "rejected"
        audit.log(self.run_id, self.case_id, "human_decision", proposal_id=proposal_id, approved=approved, note=note)
        self._record_preference(proposal, approved, note)
        if approved:
            self._apply(proposal)
        return proposal

    def _record_preference(self, proposal, approved, note):
        # One line per decision, so the owner's choices can train a model later (spec Section 5.6).
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "case_id": self.case_id,
            "proposal_id": proposal["id"],
            "action": proposal["action"],
            "args": proposal["args"],
            "approved": approved,
            "note": note,
        }
        config.PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with config.PREFS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def _apply(self, proposal):
        case = store.load_case(self.case_id)
        action, args = proposal["action"], proposal["args"]

        if action == "request_document":
            # The letter goes to the outbox. It is not sent anywhere.
            config.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
            path = config.OUTBOX_DIR / f"{self.case_id}_{proposal['id']}.txt"
            path.write_text(args.get("letter_text", ""), encoding="utf-8")
            return

        if action in TARGET_STATE:
            target = TARGET_STATE[action]
            if target not in ALLOWED_TRANSITIONS.get(case.state, set()):
                raise ValueError(f"cannot move case {self.case_id} from {case.state} to {target}")
            case = case.model_copy(update={"state": target})

        if action == "stop_case":
            case.notes.append(f"{args.get('note', '')} Reasons: {', '.join(args.get('stop_reasons', []))}".strip())
        elif action == "add_case_note":
            case.notes.append(args.get("note", ""))

        store.save_case(case)
