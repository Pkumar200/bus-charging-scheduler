from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Segment:
    from_stop: str
    to_stop: str
    distance_km: float

@dataclass
class Route:
    stops: List[str]
    segments: List[Segment]

    def distance_between(self, stop_a: str, stop_b: str) -> float:
        """Return total distance between two stops in route order."""
        stops = self.stops
        idx_a = stops.index(stop_a)
        idx_b = stops.index(stop_b)
        return sum(s.distance_km for s in self.segments[idx_a:idx_b])

@dataclass
class ChargingStation:
    id: str
    num_chargers: int

@dataclass
class Bus:
    id: str
    operator: str
    direction: str        # "BK" or "KB"
    origin: str
    destination: str
    departure_time: str   # "HH:MM"

@dataclass
class Weights:
    individual: float
    operator: float
    overall: float

@dataclass
class Constants:
    battery_range_km: float
    charge_duration_min: float
    speed_kmh: float

@dataclass
class Scenario:
    id: str
    name: str
    description: str
    route: Route
    constants: Constants
    charging_stations: List[ChargingStation]
    weights: Weights
    buses: List[Bus]

@dataclass
class ChargeStop:
    station_id: str
    arrive_time_min: float    # minutes from midnight
    wait_min: float           # time spent waiting for charger
    charge_start_min: float
    charge_end_min: float

@dataclass
class BusResult:
    bus_id: str
    operator: str
    direction: str
    departure_time_min: float
    charge_stops: List[ChargeStop]
    arrival_time_min: float

    @property
    def total_wait_min(self) -> float:
        return sum(s.wait_min for s in self.charge_stops)

    @property
    def total_trip_min(self) -> float:
        return self.arrival_time_min - self.departure_time_min
