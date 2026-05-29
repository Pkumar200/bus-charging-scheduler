from typing import List
from scheduler.models import Bus, Route, Constants, ChargingStation

def get_ordered_stations(bus: Bus, route: Route, 
                         stations: List[ChargingStation]) -> List[str]:
    """
    Return the list of charging station IDs in the order
    this bus will pass through them, based on its direction.

    BK (Bengaluru→Kochi): stations in order A, B, C, D
    KB (Kochi→Bengaluru): stations in reverse order D, C, B, A
    """
    station_ids = [s.id for s in stations]
    # Station order along the route from Bengaluru→Kochi is A,B,C,D
    # For KB direction, bus travels in reverse so reverse the list
    if bus.direction == "KB":
        return list(reversed(station_ids))
    return list(station_ids)


def find_valid_charging_plans(bus: Bus, route: Route,
                               constants: Constants,
                               stations: List[ChargingStation]) -> List[List[str]]:
    """
    Return ALL valid charging plans for this bus.
    A plan is a list of station IDs the bus will charge at.

    A plan is valid if:
    - No consecutive segment (start→first charge, charge→charge, last charge→end)
      exceeds battery_range_km (240 km)
    - Stations are visited in route order for this bus's direction
    """
    ordered_stations = get_ordered_stations(bus, route, stations)
    origin = bus.origin
    destination = bus.destination
    battery = constants.battery_range_km

    valid_plans = []

    # Try all subsets of stations (at least 1 station required)
    from itertools import combinations
    for r in range(1, len(ordered_stations) + 1):
        for combo in combinations(ordered_stations, r):
            # combo must be in the correct direction order
            combo_ordered = [s for s in ordered_stations if s in combo]

            # Build the sequence of stops: origin → stations → destination
            stop_sequence = [origin] + combo_ordered + [destination]

            # Check every consecutive pair does not exceed battery range
            valid = True
            for i in range(len(stop_sequence) - 1):
                dist = route.distance_between(
                    stop_sequence[i], stop_sequence[i + 1]
                )
                if dist > battery:
                    valid = False
                    break

            if valid:
                valid_plans.append(combo_ordered)

    return valid_plans


def choose_charging_plan(bus: Bus, route: Route,
                          constants: Constants,
                          stations: List[ChargingStation]) -> List[str]:
    """
    From all valid plans, pick the one with the fewest stops
    (minimum charging stops = minimum idle time by default).
    If tie, prefer stops that are more evenly spaced.
    This is the default plan — the engine can override this
    later with weight-aware selection.
    """
    valid_plans = find_valid_charging_plans(bus, route, constants, stations)

    if not valid_plans:
        raise ValueError(f"No valid charging plan found for bus {bus.id}")

    # Sort by: fewest stops first, then by spacing evenness
    def plan_score(plan: List[str]) -> tuple:
        stop_sequence = [bus.origin] + plan + [bus.destination]
        distances = [
            route.distance_between(stop_sequence[i], stop_sequence[i + 1])
            for i in range(len(stop_sequence) - 1)
        ]
        max_gap = max(distances)
        return (len(plan), max_gap)

    valid_plans.sort(key=plan_score)
    return valid_plans[0]
