from __future__ import annotations

from epp_nsv.adjudication import fleiss_kappa
from epp_nsv.models import Verdict


def test_fleiss_kappa_handles_complete_annotation_matrix():
    labels = {
        "p1": [Verdict.EQUIVALENT, Verdict.EQUIVALENT, Verdict.EQUIVALENT],
        "p2": [Verdict.NON_EQUIVALENT, Verdict.NON_EQUIVALENT, Verdict.NON_EQUIVALENT],
        "p3": [Verdict.INDETERMINATE, Verdict.INDETERMINATE, Verdict.INDETERMINATE],
        "p4": [Verdict.EQUIVALENT, Verdict.NON_EQUIVALENT, Verdict.EQUIVALENT],
    }
    value = fleiss_kappa(labels)
    assert value is not None
    assert -1.0 <= value <= 1.0
