"""Streamlit demo (M9): the case diagnostics showcase and the eval results.

Tab 1, Case diagnosis: pick a showcase scenario (or any case), see the free rules-only
result, run the agent, compare with the expected outcome, approve or reject its
proposals, and read the trace and the cost.
Tab 2, Evals: the ablation table, failure analysis and component results from the
committed snapshot in evals/snapshot/.

Run with:  .venv/bin/streamlit run app.py
Synthetic data only. Not connected to any HMCTS system.
"""

import json

import streamlit as st

import config
from officer import agent, audit, diagnose, llm, store

SNAPSHOT = config.ROOT / "evals" / "snapshot"

st.set_page_config(page_title="ProbateOfficer", layout="wide")
st.title("ProbateOfficer")
st.caption("An AI support officer for probate cases. It checks, reads, proposes, and a person approves.")
st.warning("Synthetic data only — not connected to any HMCTS system.")

state = st.session_state


def _load_showcase():
    path = config.DATA_DIR / "showcase.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _outcome_badge(expected, diagnosis):
    # The expected answer is the scenario's design. A match on the action and the stop reasons is a pass.
    action_ok = diagnosis.next_action == expected["next_action"]
    reasons_ok = set(diagnosis.stop_reasons) == set(expected["stop_reasons"])
    if action_ok and reasons_ok:
        st.success(f"Matches the expected outcome: {expected['next_action']}")
    else:
        st.error(f"Does not match. Expected {expected['next_action']} "
                 f"({', '.join(expected['stop_reasons']) or 'no stop reasons'}).")


def _show_diagnosis(diagnosis):
    st.markdown(f"**Next action:** `{diagnosis.next_action}`  ·  **Confidence:** {diagnosis.confidence}")
    st.markdown(f"**Stop reasons:** {', '.join(diagnosis.stop_reasons) or 'none'}  \n"
                f"**Rules cited:** {', '.join(diagnosis.rules_cited) or 'none'}")
    st.write(diagnosis.summary)


diagnosis_tab, evals_tab = st.tabs(["Case diagnosis", "Evals"])

with diagnosis_tab:
    showcase = _load_showcase()
    by_title = {f"{s['case_id']} · {s['title']}": s for s in showcase}
    show_all = st.sidebar.checkbox("Show all cases, not just the showcase", value=not showcase)
    if show_all:
        case_id = st.sidebar.selectbox("Case", store.list_cases())
        scenario = next((s for s in showcase if s["case_id"] == case_id), None)
    else:
        scenario = by_title[st.sidebar.selectbox("Showcase scenario", list(by_title))]
        case_id = scenario["case_id"]

    if st.sidebar.button("Reset case"):
        try:
            store.reset_case(case_id)
            state.pop("result", None)
            st.sidebar.success(f"{case_id} reset to its clean copy.")
        except FileNotFoundError:
            st.sidebar.error(f"{case_id} has no clean copy to reset from.")

    case = store.load_case(case_id)
    if scenario:
        st.subheader(scenario["title"])
        st.write(scenario["shows"])
        st.markdown(f"**Expected:** `{scenario['expected']['next_action']}` "
                    f"({', '.join(scenario['expected']['stop_reasons']) or 'no stop reasons'})")
    st.markdown(f"**Case** `{case_id}` · state `{case.state}` · {case.application_type}")
    with st.expander("Case record"):
        st.json(case.model_dump(mode="json"))

    rules_col, agent_col = st.columns(2)
    with rules_col:
        st.markdown("#### Rules only (no model, free)")
        _show_diagnosis(diagnose.rules_only(case_id))

    with agent_col:
        st.markdown("#### Agent (Haiku, tools, approval gate)")
        if st.button("Run agent", type="primary"):
            with st.spinner("The agent is working: reading the case, running the checks, proposing actions..."):
                llm.reset_usage()
                diagnosis, gate = agent.run_case(case_id, allow_write=True)
                state["result"] = {
                    "case_id": case_id, "diagnosis": diagnosis, "gate": gate,
                    "run_id": audit.last_run_id(), "tokens": dict(llm.USAGE), "cost": llm.cost_usd(),
                }
        result = state.get("result")
        if result and result["case_id"] == case_id:
            _show_diagnosis(result["diagnosis"])
            if scenario:
                _outcome_badge(scenario["expected"], result["diagnosis"])
        else:
            st.write("Press **Run agent** to see what the agent decides.")

    result = state.get("result")
    if result and result["case_id"] == case_id:
        st.markdown("#### Proposed actions (nothing changes until you approve)")
        gate = result["gate"]
        if gate is None or not gate.proposals:
            st.write("No proposed actions.")
        for proposal in gate.proposals if gate else []:
            st.markdown(f"**#{proposal['id']} {proposal['action']}**  ·  status: `{proposal['status']}`")
            if proposal["action"] == "request_document":
                st.text(proposal["args"].get("letter_text", ""))
            else:
                st.json(proposal["args"])
            if proposal["status"] == "pending":
                note = st.text_input("Note for the record", key=f"note{proposal['id']}")
                approve, reject = st.columns(2)
                try:
                    if approve.button("Approve", key=f"approve{proposal['id']}"):
                        gate.decide(proposal["id"], True, note)
                        st.rerun()
                    if reject.button("Reject", key=f"reject{proposal['id']}"):
                        gate.decide(proposal["id"], False, note)
                        st.rerun()
                except ValueError as error:
                    # An illegal state change is refused. The case is left as it was.
                    st.error(str(error))

        cols = st.columns(3)
        cols[0].metric("Model calls", result["tokens"]["calls"])
        cols[1].metric("Tokens in / out", f"{result['tokens']['input_tokens']} / {result['tokens']['output_tokens']}")
        cols[2].metric("Cost of this run (USD)", f"${result['cost']:.4f}")

        with st.expander("Trace (audit log for this run)"):
            for record in audit.read_run(result["run_id"]):
                st.text(json.dumps(record, default=str)[:400])

with evals_tab:
    st.markdown("Results from the test split (24 synthetic cases). Intervals are 95% bootstrap intervals, "
                "resampled by case. With 24 cases, differences inside overlapping intervals are not meaningful.")
    sections = [
        ("Ablation: every variant on the test split", "ablation.md"),
        ("What the evals caught: six findings, and how each was fixed", "prompt_story.md"),
        ("Judgement rules, tested alone", "component.md"),
        ("Letter quality, scored by the LLM judge", "judge.md"),
        ("Failure analysis", "failure_analysis.md"),
        ("Showcase run (current)", "showcase.md"),
        ("Showcase run before the v4 rule fix (6 of 8)", "showcase_v3.md"),
    ]
    for heading, name in sections:
        path = SNAPSHOT / name
        if path.exists():
            with st.expander(heading, expanded=name in ("ablation.md", "prompt_story.md")):
                st.markdown(path.read_text(encoding="utf-8"))
    if not SNAPSHOT.exists():
        st.info("No eval snapshot yet. Run the evals, then evals.compare.")
