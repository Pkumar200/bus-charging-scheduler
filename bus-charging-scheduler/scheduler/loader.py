import json
import os
from typing import List
from scheduler.models import (
    Scenario, Route, Segment, ChargingStation,
    Bus, Weights, Constants
)


def load_scenario(filepath: str) -> Scenario:
    """Load a single scenario from a JSON file and return a Scenario object."""
    with open(filepath, "r") as f:
        data = json.load(f)

    # Parse route
    segments = [
        Segment(
            from_stop=s["from"],
            to_stop=s["to"],
            distance_km=s["distance_km"]
        )
        for s in data["route"]["segments"]
    ]
    route = Route(
        stops=data["route"]["stops"],
        segments=segments
    )

    # Parse constants
    constants = Constants(
        battery_range_km=data["constants"]["battery_range_km"],
        charge_duration_min=data["constants"]["charge_duration_min"],
        speed_kmh=data["constants"]["speed_kmh"]
    )

    # Parse charging stations
    charging_stations = [
        ChargingStation(
            id=s["id"],
            num_chargers=s["num_chargers"]
        )
        for s in data["charging_stations"]
    ]

    # Parse weights
    weights = Weights(
        individual=data["weights"]["individual"],
        operator=data["weights"]["operator"],
        overall=data["weights"]["overall"]
    )

    # Parse buses
    buses = [
        Bus(
            id=b["id"],
            operator=b["operator"],
            direction=b["direction"],
            origin=b["origin"],
            destination=b["destination"],
            departure_time=b["departure_time"]
        )
        for b in data["buses"]
    ]

    return Scenario(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        route=route,
        constants=constants,
        charging_stations=charging_stations,
        weights=weights,
        buses=buses
    )


def load_all_scenarios(scenarios_dir: str = "scenarios") -> List[Scenario]:
    """
    Load all scenario JSON files from the scenarios/ folder.
    Returns list sorted by scenario id.
    """
    files = sorted([
        f for f in os.listdir(scenarios_dir)
        if f.endswith(".json")
    ])

    return [
        load_scenario(os.path.join(scenarios_dir, f))
        for f in files
    ]
