"""PyTorch baseline (M8): a linear classifier over TF-IDF text features. It predicts the next action only.

It is not a reasoner. It cannot give stop reasons or cite rules, so its diagnosis
has no stop reasons. It is here to show what a simple learned model gets from the
same case text, to compare with the rules and the LLM.

Run with `python baseline/train_baseline.py` after `python scripts/make_cases.py --train 300`.
"""

import json
import pickle
import sys
from pathlib import Path

import torch
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from officer.models import Case, Diagnosis

HERE = Path(__file__).resolve().parent
TRAIN_DIR = HERE / "train_cases"
MODEL_PATH = HERE / "model.pt"
VECTORIZER_PATH = HERE / "vectorizer.pkl"
ACTIONS = ["stop_case", "route_to_examiner", "escalate", "refuse_out_of_scope"]

_model = None
_vectorizer = None


def case_text(case):
    """All the case text, plus the key fields written as words, so the vectoriser can use them."""
    parts = list(case.notes) + [doc.text for doc in case.documents if doc.text]
    parts += [f"state {case.state}", f"application {case.application_type}", f"domicile {case.deceased.domicile}",
              f"iht {case.estate.iht_route}", f"address {case.applicant.address_given}"]
    parts += [f"document {doc.type} received {doc.received} original {doc.original}" for doc in case.documents]
    return " ".join(parts)


def load_train():
    labels = {}
    with (TRAIN_DIR / "expected.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                labels[row["case_id"]] = row["next_action"]
    cases = [Case.model_validate_json((TRAIN_DIR / f"{case_id}.json").read_text()) for case_id in sorted(labels)]
    return cases, [labels[case.case_id] for case in cases]


def train(epochs=200, learning_rate=1e-2):
    torch.manual_seed(config.SEED)
    cases, actions = load_train()
    # Fit the vocabulary on the training cases only. The golden set must never shape it.
    vectorizer = TfidfVectorizer(max_features=2000)
    features = torch.tensor(vectorizer.fit_transform([case_text(c) for c in cases]).toarray(), dtype=torch.float32)
    targets = torch.tensor([ACTIONS.index(action) for action in actions])

    model = torch.nn.Linear(features.shape[1], len(ACTIONS))
    loss_function = torch.nn.CrossEntropyLoss()
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    for epoch in range(1, epochs + 1):
        optimiser.zero_grad()
        loss = loss_function(model(features), targets)
        loss.backward()
        optimiser.step()
        if epoch % 50 == 0:
            print(f"epoch {epoch:3d}  loss {loss.item():.4f}")

    torch.save(model.state_dict(), MODEL_PATH)
    with VECTORIZER_PATH.open("wb") as handle:
        pickle.dump(vectorizer, handle)
    return model, vectorizer


def _load():
    global _model, _vectorizer
    if _model is None:
        if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
            raise FileNotFoundError("the baseline is not trained yet: run python baseline/train_baseline.py")
        _vectorizer = pickle.loads(VECTORIZER_PATH.read_bytes())
        _model = torch.nn.Linear(len(_vectorizer.vocabulary_), len(ACTIONS))
        _model.load_state_dict(torch.load(MODEL_PATH))
    return _model, _vectorizer


def predict(case):
    """A Diagnosis with the next action only. Stop reasons and rules cited are empty by design."""
    model, vectorizer = _load()
    features = torch.tensor(vectorizer.transform([case_text(case)]).toarray(), dtype=torch.float32)
    with torch.no_grad():
        action = ACTIONS[int(model(features).argmax(dim=1))]
    return Diagnosis(
        case_id=case.case_id,
        summary="Baseline prediction of the next action only. It gives no stop reasons or rules.",
        stop_reasons=[],
        rules_cited=[],
        next_action=action,
        confidence="low",
    )


if __name__ == "__main__":
    train()
    print(f"saved {MODEL_PATH.name} and {VECTORIZER_PATH.name}")
