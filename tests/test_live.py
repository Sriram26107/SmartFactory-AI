import pytest
from smartfactory.live.telemetry import save_reading, recent_readings, latest_by_machine, validate, condition_status

def test_live_storage(tmp_path):
    path=tmp_path/"live.db"
    save_reading({"machine_id":"M-001","temperature_c":65,"vibration_mm_s":2.5},path=path)
    save_reading({"machine_id":"M-001","temperature_c":66,"vibration_mm_s":3.0},path=path)
    save_reading({"machine_id":"M-002","temperature_c":86,"vibration_mm_s":7.1},path=path)
    assert len(recent_readings(path=path))==3
    latest=latest_by_machine(path=path)
    assert len(latest)==2
    assert latest[0]["temperature_c"]==66
    assert latest[1]["source"]=="mqtt"

def test_invalid_readings():
    with pytest.raises(ValueError):
        validate({"machine_id":"../bad","temperature_c":65,"vibration_mm_s":3})
    with pytest.raises(ValueError):
        validate({"machine_id":"M-001","temperature_c":float("nan"),"vibration_mm_s":3})
    with pytest.raises(ValueError):
        validate({"machine_id":"M-001","temperature_c":65})

def test_condition_status():
    assert condition_status(60,2)=="Normal"
    assert condition_status(75,2)=="Watch"
    assert condition_status(86,2)=="High"
