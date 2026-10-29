"""Pydantic models for cases, findings and diagnoses.

These classes define the shape of every case file and every diagnosis in the
project. Pydantic checks the data when it is loaded, so a bad case fails early
with a clear message rather than causing a confusing error later.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

# Case states. The list is fixed here. Only "issued" and "stopped" are in scope (see config.py).
State = Literal["issued", "stopped", "ready_for_examiner", "escalated", "examining", "granted"]

# The actions the diagnoser can return. "refuse_out_of_scope" is deliberately absent:
# only the code-level scope guard can produce it, never the model.
NextAction = Literal["stop_case", "route_to_examiner", "escalate", "refuse_out_of_scope"]


class Document(BaseModel):
    """One document in the case file, such as a will or a death certificate."""

    type: str
    received: bool
    # None means "not applicable or unknown", for example for a death certificate.
    original: Optional[bool] = None
    text: Optional[str] = None


class Applicant(BaseModel):
    name: str
    role: str
    address_given: bool


class Deceased(BaseModel):
    name: str
    date_of_death: date
    domicile: str


class Estate(BaseModel):
    gross_value: int
    net_value: int
    iht_route: str


class Case(BaseModel):
    """A full probate case, as stored in data/cases/<case_id>.json."""

    case_id: str
    state: State
    application_type: Literal["probate_will", "letters_of_administration"]
    applicant: Applicant
    deceased: Deceased
    estate: Estate
    documents: list[Document]
    notes: list[str]


class Finding(BaseModel):
    """The result of one rule check on one case."""

    rule_id: str
    passed: bool
    stop_reason: Optional[str] = None
    action: Optional[str] = None
    reason: str = ""


class Diagnosis(BaseModel):
    """The output the eval harness scores. One per case run."""

    case_id: str
    summary: str
    stop_reasons: list[str]
    rules_cited: list[str]
    next_action: NextAction
    confidence: Literal["low", "medium", "high"]
