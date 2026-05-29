# Architecture

## Scheduling approach

The scheduler uses an **event-driven simulation** with a **weighted priority queue**.

Each bus is processed in departure-time order. At each charging station,
the scheduler computes a priority score for the bus using three weighted
components — individual wait, operator fairness, and overall network
efficiency. The bus with the lowest score gets the charger first.

Why event-driven simulation?
- The problem is inherently time-ordered: buses arrive at stations at
  specific times and the charger state changes with each assignment
- A constraint solver (e.g. OR-Tools) would work but is harder to extend
  with new soft rules and harder to explain live
- A greedy heuristic without weights would ignore the operator and overall
  dimensions entirely
- Event-driven simulation gives full control over priority logic, is easy
  to extend, and produces a traceable timeline for every bus

## Data structure design

Each scenario is a self-contained JSON file with six sections:

- `route` — stops and segment distances. Adding a new stop means adding
  one entry to `stops` and one to `segments`. No code changes.
- `constants` — battery range, charge duration, speed. All physics lives
  here. Changing speed or range is one value in one place.
- `charging_stations` — list of stations with `num_chargers`. Adding a
  second charger at station B means changing `num_chargers` from 1 to 2.
  No code changes.
- `weights` — three floats. Tuning priority is one value in one file.
- `buses` — list of buses with operator, direction, departure time.
  Adding buses or operators means adding rows. No code changes.

The scheduler reads everything from the scenario object. It has no
hardcoded station names, no hardcoded route, no hardcoded operator list.

## Future changes anticipated — and how the design handles each

| Change | How the design handles it |
|---|---|
| Add a new charging station | Add one entry to `route.segments` and one to `charging_stations` in the JSON. Planner and engine are route-agnostic. |
| Double the chargers at a station | Change `num_chargers` in the JSON. Engine already supports multiple charger slots per station. |
| Add a new operator | Add buses with the new operator name in the JSON. Engine uses operator as a string key — no enum, no hardcoding. |
| Change segment distance | Edit `distance_km` in the JSON. All travel times recompute automatically. |
| Change speed | Edit `speed_kmh` in constants. One value, one place. |
| Change battery range | Edit `battery_range_km` in constants. Planner recomputes valid plans automatically. |
| Add a new route | Create a new scenario JSON with a different `route` block. Engine is route-agnostic. |
| Multiple routes sharing a station | Extend `charging_stations` to include a `route_id` filter. Engine queries by station_id already. |
| Priority buses | Add a `priority` field to the bus schema. Add one term to `compute_bus_score`. No engine rewrite. |
| Time-of-day electricity costs | Add a `cost_schedule` block to constants. Add one term to `compute_bus_score`. |
| Driver shift constraints | Add `driver_available_from` and `driver_available_until` to each bus. Add one check in `run_scheduler` before assigning charge_start. |
| Add a 6th scenario | Create `scenario_6.json`. App loads all JSON files in the folder automatically. |
| Tune weights in production | Edit the three floats in the scenario JSON. One place, no code. |
| Add a new soft rule | Add one scored term to `compute_bus_score` in engine.py. No other changes. |
| Add a new hard rule | Add one condition block in `run_scheduler` after charge_start is computed. No other changes. |

## How to change a weight

In any scenario JSON:

```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```

That is the only change needed. The engine reads weights from the
scenario object at runtime.

## How to add a new soft rule — example

Suppose we want to penalise buses that have already waited more than
30 minutes total (to prevent starvation).

In `scheduler/engine.py`, add one parameter and one line to
`compute_bus_score`:

```python
def compute_bus_score(
    bus, arrive_time, charger_free_at,
    weights, operator_last_charged,
    global_total_wait,
    prior_total_wait  # NEW
) -> float:
    individual_score = arrive_time * weights.individual
    operator_score   = operator_last_charged.get(bus.operator, arrive_time) * weights.operator
    overall_score    = global_total_wait * weights.overall
    starvation_penalty = max(0, prior_total_wait - 30) * weights.individual  # NEW
    return individual_score + operator_score + overall_score + starvation_penalty
```

Pass `prior_total_wait` from `run_scheduler` when calling the function.
No other changes to the engine.

## Assumptions made

- All buses start with a full charge (240 km range) at their origin
- Speed is constant at 60 km/h with no traffic variation
- Charging always fills to full and always takes exactly 25 minutes
- The planner picks the charging plan with the fewest stops, breaking
  ties by most even spacing — this minimises idle time by default
- Buses are processed in departure-time order; ties broken by bus ID
- The endpoints (Bengaluru and Kochi) have slow chargers and are not
  part of the scheduling problem
- `num_chargers` per station is respected — the engine supports more
  than 1 charger per station already
- Weights are applied additively in the priority score — multiplying
  them scales the influence of each dimension linearly
- No authentication, no database, no persistent state — in-memory
  simulation per page load is sufficient for this problem size
