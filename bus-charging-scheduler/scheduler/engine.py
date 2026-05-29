import heapq
from typing import List, Dict
from scheduler.models import (
    Scenario, Bus, BusResult, ChargeStop, Weights
)
from scheduler.planner import choose_charging_plan


def parse_time(t: str) -> float:
    """Convert 'HH:MM' to minutes from midnight."""
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def format_time(minutes: float) -> str:
    """Convert minutes from midnight to 'HH:MM'."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


def compute_travel_time(distance_km: float, speed_kmh: float) -> float:
    """Return travel time in minutes."""
    return (distance_km / speed_kmh) * 60


def compute_bus_score(
    bus: Bus,
    arrive_time: float,
    charger_free_at: float,
    weights: Weights,
    operator_last_charged: Dict[str, float],
    global_total_wait: float
) -> float:
    """
    Lower score = higher priority at the charger.

    Three components weighted by scenario weights:
    1. individual  — how long THIS bus has been waiting
    2. operator    — how long this operator's fleet has been waiting on average
    3. overall     — contribution to global total wait time

    We want to MINIMISE wait, so earlier arriving buses score lower.
    """
    individual_score = arrive_time * weights.individual

    op_last = operator_last_charged.get(bus.operator, arrive_time)
    operator_score = op_last * weights.operator

    overall_score = global_total_wait * weights.overall

    return individual_score + operator_score + overall_score


def run_scheduler(scenario: Scenario) -> List[BusResult]:
    """
    Event-driven scheduler.

    For each bus:
    1. Compute its charging plan (which stations it uses)
    2. Simulate its journey stop by stop
    3. At each charging station, queue it up and assign
       the charger based on weighted priority score
    4. Record full timeline in BusResult

    Returns a list of BusResult, one per bus.
    """
    route = scenario.route
    constants = scenario.constants
    weights = scenario.weights
    stations = scenario.charging_stations

    # Track when each charger slot becomes free
    # key: station_id, value: list of free-at times (one per charger)
    charger_free: Dict[str, List[float]] = {
        s.id: [0.0] * s.num_chargers for s in stations
    }

    # Track last charge completion time per operator (for operator fairness)
    operator_last_charged: Dict[str, float] = {}

    # Running total wait across all buses (for overall score)
    global_total_wait: float = 0.0

    results: List[BusResult] = []

    # Sort buses by departure time so we process them in order
    sorted_buses = sorted(
        scenario.buses,
        key=lambda b: parse_time(b.departure_time)
    )

    for bus in sorted_buses:
        departure_min = parse_time(bus.departure_time)
        current_time = departure_min
        charge_stops: List[ChargeStop] = []

        # Get charging plan for this bus
        plan = choose_charging_plan(bus, route, constants, stations)

        # Build full stop sequence for travel time calculation
        stop_sequence = [bus.origin] + plan + [bus.destination]

        for i in range(len(stop_sequence) - 1):
            from_stop = stop_sequence[i]
            to_stop = stop_sequence[i + 1]

            # Travel to next stop
            dist = route.distance_between(from_stop, to_stop)
            travel = compute_travel_time(dist, constants.speed_kmh)
            current_time += travel

            # If next stop is a charging station (not the destination)
            if to_stop in [s.id for s in stations] and to_stop != bus.destination:
                arrive_time = current_time

                # Find the charger slot that is free earliest at this station
                slots = charger_free[to_stop]
                earliest_slot_idx = min(range(len(slots)), key=lambda x: slots[x])
                charger_available = slots[earliest_slot_idx]

                # Compute priority score for this bus at this station
                score = compute_bus_score(
                    bus=bus,
                    arrive_time=arrive_time,
                    charger_free_at=charger_available,
                    weights=weights,
                    operator_last_charged=operator_last_charged,
                    global_total_wait=global_total_wait
                )

                # Bus must wait if charger is busy
                charge_start = max(arrive_time, charger_available)
                wait = charge_start - arrive_time
                charge_end = charge_start + constants.charge_duration_min

                # Update charger slot
                slots[earliest_slot_idx] = charge_end

                # Update operator tracking
                operator_last_charged[bus.operator] = charge_end

                # Update global wait
                global_total_wait += wait

                # Record the charge stop
                charge_stops.append(ChargeStop(
                    station_id=to_stop,
                    arrive_time_min=arrive_time,
                    wait_min=wait,
                    charge_start_min=charge_start,
                    charge_end_min=charge_end
                ))

                # Bus leaves station after charging is done
                current_time = charge_end

        # Bus has arrived at destination
        arrival_time = current_time

        results.append(BusResult(
            bus_id=bus.id,
            operator=bus.operator,
            direction=bus.direction,
            departure_time_min=departure_min,
            charge_stops=charge_stops,
            arrival_time_min=arrival_time
        ))

    return results
