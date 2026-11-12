"""Safety-policy and idempotency unit tests."""

from lakeguard.incident import Incident
from lakeguard.policy import Action, evaluate_action


def test_destructive_action_blocked():
    assert not evaluate_action(Action.REWRITE_HISTORY, authorized=True)[0]


def test_retry_bounded():
    assert evaluate_action(Action.RETRY, authorized=True, retry_count=0)[0]
    assert not evaluate_action(Action.RETRY, authorized=True, retry_count=1)[0]


def test_stable_incident_id():
    assert (
        Incident("orders", "run-1", "volume_drop").incident_id
        == Incident("orders", "run-1", "volume_drop").incident_id
    )
