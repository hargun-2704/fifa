"""
tests/test_decision_engine.py
Unit tests for the deterministic (non-GenAI) parts of decision_engine.py.

These tests intentionally avoid calling any real API -- they validate the
safety-critical rule-based triage logic, which must work correctly and
deterministically regardless of GenAI availability.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decision_engine import triage_gates, find_relief_gate, build_context_summary


def make_gate(name, density, queue):
    return {"gate": name, "density_pct": density, "queue_minutes": queue, "status": "normal"}


def test_triage_flags_critical_density():
    gates = [make_gate("Gate 1", 90, 5), make_gate("Gate 2", 20, 2)]
    flagged = triage_gates(gates)
    assert len(flagged) == 1
    assert flagged[0]["gate"] == "Gate 1"
    assert flagged[0]["severity"] == "critical"


def test_triage_flags_long_queue_as_warning():
    gates = [make_gate("Gate 1", 50, 20)]
    flagged = triage_gates(gates)
    assert len(flagged) == 1
    assert flagged[0]["severity"] == "warning"


def test_triage_ignores_normal_gates():
    gates = [make_gate("Gate 1", 40, 5), make_gate("Gate 2", 30, 2)]
    assert triage_gates(gates) == []


def test_triage_sorts_by_density_descending():
    gates = [make_gate("Gate 1", 90, 5), make_gate("Gate 2", 95, 6)]
    flagged = triage_gates(gates)
    assert flagged[0]["gate"] == "Gate 2"
    assert flagged[1]["gate"] == "Gate 1"


def test_find_relief_gate_picks_least_dense():
    gates = [make_gate("Gate 1", 90, 5), make_gate("Gate 2", 10, 1), make_gate("Gate 3", 50, 3)]
    relief = find_relief_gate(gates)
    assert relief["gate"] == "Gate 2"


def test_find_relief_gate_handles_empty_list():
    assert find_relief_gate([]) is None


def test_build_context_summary_structure():
    snapshot = {
        "gates": [make_gate("Gate 1", 90, 5)],
        "zones": [],
        "weather": {"condition": "Clear", "temperature_c": 25},
        "incident": None,
    }
    context = build_context_summary(snapshot)
    assert "flagged_gates" in context
    assert "relief_gate" in context
    assert context["incident"] is None
    assert context["weather"]["condition"] == "Clear"
