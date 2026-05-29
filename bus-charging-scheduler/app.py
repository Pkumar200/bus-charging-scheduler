import streamlit as st
import pandas as pd
from scheduler.loader import load_all_scenarios
from scheduler.engine import run_scheduler, format_time

st.set_page_config(page_title="Bus Charging Scheduler", layout="wide")
st.title("🚌 Bus Charging Scheduler")

# ── Load all scenarios ──────────────────────────────────────────────
scenarios = load_all_scenarios("scenarios")
scenario_map = {s.name: s for s in scenarios}

selected_name = st.selectbox(
    "Select a Scenario",
    options=list(scenario_map.keys())
)
scenario = scenario_map[selected_name]

# ── Scenario Info ───────────────────────────────────────────────────
st.subheader("Scenario Overview")
st.write(scenario.description)

col1, col2, col3 = st.columns(3)
col1.metric("Total Buses", len(scenario.buses))
col2.metric("Charging Stations", len(scenario.charging_stations))
col3.metric(
    "Weights (ind / op / overall)",
    f"{scenario.weights.individual} / {scenario.weights.operator} / {scenario.weights.overall}"
)

# ── Raw Input Table ─────────────────────────────────────────────────
st.subheader("Input — Departure Schedule")
bus_input_df = pd.DataFrame([
    {
        "Bus ID": b.id,
        "Operator": b.operator,
        "Direction": b.direction,
        "Origin": b.origin,
        "Destination": b.destination,
        "Departure": b.departure_time
    }
    for b in scenario.buses
])
st.dataframe(bus_input_df, use_container_width=True)

# ── Run Scheduler ───────────────────────────────────────────────────
st.subheader("Scheduler Output")

with st.spinner("Running scheduler..."):
    results = run_scheduler(scenario)

# ── Per-Bus Timetable ───────────────────────────────────────────────
st.markdown("### Per-Bus Timetable")

bus_rows = []
for r in results:
    for i, cs in enumerate(r.charge_stops):
        bus_rows.append({
            "Bus ID": r.bus_id,
            "Operator": r.operator,
            "Direction": r.direction,
            "Charge Stop #": i + 1,
            "Station": cs.station_id,
            "Arrive": format_time(cs.arrive_time_min),
            "Wait (min)": round(cs.wait_min, 1),
            "Charge Start": format_time(cs.charge_start_min),
            "Charge End": format_time(cs.charge_end_min),
            "Final Arrival": format_time(r.arrival_time_min),
            "Total Wait (min)": round(r.total_wait_min, 1),
            "Total Trip (min)": round(r.total_trip_min, 1)
        })

if bus_rows:
    bus_df = pd.DataFrame(bus_rows)
    st.dataframe(bus_df, use_container_width=True)
else:
    st.warning("No charge stops generated.")

# ── Per-Station View ────────────────────────────────────────────────
st.markdown("### Per-Station Charging Order")

station_ids = [s.id for s in scenario.charging_stations]

for station_id in station_ids:
    st.markdown(f"#### Station {station_id}")

    station_rows = []
    for r in results:
        for cs in r.charge_stops:
            if cs.station_id == station_id:
                station_rows.append({
                    "Bus ID": r.bus_id,
                    "Operator": r.operator,
                    "Direction": r.direction,
                    "Arrive": format_time(cs.arrive_time_min),
                    "Wait (min)": round(cs.wait_min, 1),
                    "Charge Start": format_time(cs.charge_start_min),
                    "Charge End": format_time(cs.charge_end_min)
                })

    if station_rows:
        # Sort by charge start time so order is clear
        station_df = pd.DataFrame(station_rows)
        station_df = station_df.sort_values("Charge Start")
        st.dataframe(station_df, use_container_width=True)
    else:
        st.info(f"No buses charged at Station {station_id} in this scenario.")
