"""
mock_data.py
Simulates live venue telemetry for the FIFA World Cup 2026 stadium demo.

In a real deployment these values would come from IoT crowd-density sensors,
turnstile counters, and a staff incident-reporting system. For this hackathon
build we simulate realistic, slightly-changing values so the dashboard feels
"live" without needing real hardware.
"""

import random
from datetime import datetime
from typing import Dict, List

GATES = ["Gate 1", "Gate 2", "Gate 3", "Gate 4", "Gate 5", "Gate 6", "Gate 7", "Gate 8"]
ZONES = ["Zone A (North Stand)", "Zone B (South Stand)", "Zone C (East Concourse)", "Zone D (West Concourse)"]

INCIDENT_TYPES = [
    "Medical assistance requested",
    "Lost child reported",
    "Overcrowding at entry point",
    "Minor altercation",
    "Blocked walkway",
    "Suspicious unattended item",
]


def _rand_density() -> int:
    """Return a simulated crowd density percentage (0-100)."""
    return random.randint(10, 98)


def _rand_queue_minutes() -> int:
    return random.randint(1, 30)


def get_gate_status() -> List[Dict]:
    """Simulate live status for every stadium gate."""
    status = []
    for gate in GATES:
        density = _rand_density()
        status.append({
            "gate": gate,
            "density_pct": density,
            "queue_minutes": _rand_queue_minutes(),
            "status": "critical" if density > 85 else "busy" if density > 60 else "normal",
        })
    return status


def get_zone_status() -> List[Dict]:
    """Simulate live status for internal concourse zones."""
    return [
        {
            "zone": zone,
            "density_pct": _rand_density(),
            "temperature_c": round(random.uniform(24, 34), 1),
        }
        for zone in ZONES
    ]


def maybe_generate_incident() -> Dict | None:
    """Randomly simulate an incident report arriving from on-ground staff."""
    if random.random() < 0.35:  # ~35% chance per refresh
        return {
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": random.choice(INCIDENT_TYPES),
            "location": random.choice(GATES + ZONES),
            "severity": random.choice(["low", "medium", "high"]),
        }
    return None


def get_weather() -> Dict:
    """Simulate a simple weather snapshot relevant to crowd flow decisions."""
    return {
        "condition": random.choice(["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Heatwave"]),
        "temperature_c": round(random.uniform(22, 38), 1),
    }


def get_full_snapshot() -> Dict:
    """Bundle all live signals into a single context object for the decision engine."""
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "gates": get_gate_status(),
        "zones": get_zone_status(),
        "weather": get_weather(),
        "incident": maybe_generate_incident(),
    }
