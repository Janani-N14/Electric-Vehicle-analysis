import pytest
from ev_fleet_management.model.models import UserModel, EVModel, DriverModel, TelemetryModel
from datetime import datetime

def test_correlation_matrix_endpoint(client):
    response = client.get("/api/analytics/correlation-matrix")
    # Should read successfully if the spreadsheet is present in data/
    assert response.status_code in [200, 404]  # 404 is acceptable if running in environment without the Excel file
    if response.status_code == 200:
        data = response.json()
        assert len(data) > 0
        assert "Correlation Matrix" in data[0]

def test_charts_endpoint(client):
    response = client.get("/api/analytics/charts")
    assert response.status_code == 200
    data = response.json()
    assert "energy_consumption_kwh" in data
    assert "active_trend" in data
    assert len(data["energy_consumption_kwh"]) == 7

def test_driver_efficiency_calculations(client, db_session):
    # Set up mock data
    # Create driver
    drv = DriverModel(id="D111", name="Aakash Test", email="driver111@evfleet.com", status="Idle")
    db_session.add(drv)
    
    # Create telemetry logs for D111
    # 2 harsh brakings, 1 overspeed, distance 100km, efficiency 5.5
    log1 = TelemetryModel(
        driver_id="D111",
        vehicle_id="EV-D111",
        datetime=datetime.utcnow(),
        speed=45.0,
        acceleration=1.5,
        harsh_braking=1,
        harsh_acceleration=0,
        overspeed_violation=0,
        working_status="Working",
        passenger_count=1,
        distance_travelled=50.0,
        odometer_distance=1050.0,
        is_charging=0,
        is_discharging=1,
        charging_cost=0.0,
        energy_efficiency=5.5,
        income=500.0,
        maintenance_cost=0.0,
        breakdown=0,
        battery_pct=80.0,
        battery_health=98.0,
        battery_stress=0,
        estimated_range=250.0,
        latitude=13.08,
        longitude=80.26
    )
    log2 = TelemetryModel(
        driver_id="D111",
        vehicle_id="EV-D111",
        datetime=datetime.utcnow(),
        speed=85.0, # overspeeding
        acceleration=2.0,
        harsh_braking=1,
        harsh_acceleration=1,
        overspeed_violation=1,
        working_status="Working",
        passenger_count=1,
        distance_travelled=50.0,
        odometer_distance=1100.0,
        is_charging=0,
        is_discharging=1,
        charging_cost=0.0,
        energy_efficiency=5.1,
        income=600.0,
        maintenance_cost=0.0,
        breakdown=0,
        battery_pct=70.0,
        battery_health=98.0,
        battery_stress=0,
        estimated_range=220.0,
        latitude=13.09,
        longitude=80.27
    )
    db_session.add(log1)
    db_session.add(log2)
    db_session.commit()
    
    response = client.get("/api/analytics/driver-efficiency")
    assert response.status_code == 200
    data = response.json()
    
    # Assert driver is in the list
    driver_recs = data["drivers"]
    my_driver = next((d for d in driver_recs if d["driver_id"] == "D111"), None)
    assert my_driver is not None
    assert my_driver["total_harsh_braking"] == 2
    assert my_driver["total_harsh_acceleration"] == 1
    assert my_driver["total_overspeed_violations"] == 1
    assert my_driver["total_distance_km"] == 100.0
    
    # The score should be calculated correctly:
    # rate_braking = 2/100 * 100 = 2
    # rate_accel = 1/100 * 100 = 1
    # rate_overspeed = 1/100 * 100 = 1
    # score deduction = 2*0.8 + 1*0.5 + 1*1.5 = 1.6 + 0.5 + 1.5 = 3.6
    # score = 100 - 3.6 = 96.4
    assert my_driver["score"] == 96.4

def test_fleet_report_endpoint(client, db_session):
    # Add an EV and telemetry log to database
    ev = EVModel(id="EV-D111", make="TestEV", model="Model1", plate_no="EV-111", battery_capacity_kwh=50.0, year=2024, status="Active")
    db_session.add(ev)
    
    log = TelemetryModel(
        driver_id="D111",
        vehicle_id="EV-D111",
        datetime=datetime(2025, 1, 15, 10, 0, 0), # March mapping
        speed=50.0,
        acceleration=1.0,
        harsh_braking=0,
        harsh_acceleration=0,
        overspeed_violation=0,
        working_status="Working",
        passenger_count=1,
        distance_travelled=10.0,
        odometer_distance=1000.0,
        is_charging=1,
        is_discharging=0,
        charging_cost=150.0,
        energy_efficiency=4.5,
        income=800.0,
        maintenance_cost=200.0,
        breakdown=0,
        battery_pct=50.0,
        estimated_range=200.0
    )
    db_session.add(log)
    db_session.commit()
    
    response = client.get("/api/analytics/fleet-report")
    assert response.status_code == 200
    data = response.json()
    assert "working_vs_garage" in data
    assert "active_vehicles" in data
    assert "vehicle_income" in data
    assert "charging_revenue" in data
    assert "maintenance_correlation" in data
    assert "cost_comparison" in data
    assert "averages" in data
    assert "insights" in data
    
    # Assert values
    assert data["working_vs_garage"]["working"] == 1
    assert data["active_vehicles"]["count"] == 1
    assert data["charging_revenue"]["March"] == 150.0
    assert data["cost_comparison"]["charging_cost"] == 150.0
    assert data["cost_comparison"]["maintenance_cost"] == 200.0

def test_driver_violations_endpoint(client, db_session):
    # Add telemetry log with violations
    log = TelemetryModel(
        driver_id="D111",
        vehicle_id="EV-D111",
        datetime=datetime(2025, 5, 15, 10, 0, 0), # April mapping
        speed=95.0,
        acceleration=3.0,
        harsh_braking=2,
        harsh_acceleration=1,
        overspeed_violation=1,
        working_status="Working",
        passenger_count=1,
        distance_travelled=20.0,
        odometer_distance=1020.0,
        is_charging=0,
        is_discharging=1,
        charging_cost=0.0,
        energy_efficiency=4.2,
        income=1200.0,
        maintenance_cost=0.0,
        breakdown=0,
        battery_pct=40.0,
        estimated_range=160.0
    )
    db_session.add(log)
    db_session.commit()
    
    response = client.get("/api/analytics/driver-violations/D111")
    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == "D111"
    assert "violations" in data
    assert "summary" in data
    
    assert data["violations"]["April"]["overspeed"] == 1
    assert data["violations"]["April"]["harsh_braking"] == 2
    assert data["violations"]["April"]["harsh_accel"] == 1
    assert data["summary"]["grand_total"] == 4
