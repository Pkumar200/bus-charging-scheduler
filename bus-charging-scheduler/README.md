# Bus Charging Scheduler

A Python + Streamlit app that schedules electric bus charging stops
along the Bengaluru → Kochi route.

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## How to change a weight

Open the relevant scenario file in `scenarios/`. For example, to increase
the operator fairness weight in scenario_1.json:

```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```

Save the file and reload the app. No code changes needed.

## How to add a new scenario

1. Create a new JSON file in `scenarios/` following the same schema as
   the existing files
2. Add buses, set weights, set route and constants
3. The app picks it up automatically on next load — no code changes needed

## How to add a new soft rule

Open `scheduler/engine.py` and find the `compute_bus_score` function.
Add your new rule as a new scored component. Example — penalise buses
that have already waited more than 30 minutes total:

```python
penalty = 0.0
if prior_total_wait > 30:
    penalty = prior_total_wait * weights.individual

return individual_score + operator_score + overall_score + penalty
```

Then add the `prior_total_wait` parameter to the function call in
`run_scheduler`. The engine does not need to be rewritten.

## How to add a new hard rule

Open `scheduler/engine.py` inside `run_scheduler`. After the line:

```python
charge_start = max(arrive_time, charger_available)
```

Add your constraint as a condition that adjusts `charge_start` or
raises an error. Example — no charging between 02:00 and 04:00:

```python
NO_CHARGE_START = 2 * 60   # 02:00
NO_CHARGE_END   = 4 * 60   # 04:00
if NO_CHARGE_START <= charge_start < NO_CHARGE_END:
    charge_start = NO_CHARGE_END
```

## Project structure
