"""ProbateOfficer: an AI support officer for probate cases, built as seven components.

A probate support officer's job, broken into steps, with one component per step:

1. intake      - load and validate a case (and read an incoming email, as a dry run)
2. scope       - refuse out-of-scope cases in code, before any model call
3. checks      - deterministic rules, in plain Python
4. judgement   - judgement rules, one forced model call each
5. decision    - the agent loop and its tools, or a single model call, ending in a Diagnosis
6. gate        - proposals, human approval, and the allowed status changes
7. audit       - every step logged under one run_id

Shared by all components: models.py (the data contract), llm.py (the only door to the
API) and prompts.py (every prompt, under one PROMPT_VERSION). Each component folder has
a README.md stating its contract: inputs, outputs, dependencies, and its tests.
"""
