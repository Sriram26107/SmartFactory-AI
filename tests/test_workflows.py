import pytest
from smartfactory.workflows import (process_telemetry, list_incidents, list_tasks,
    resolve_incident, production_impact, add_production_event, production_summary)


def payload(t=90, v=2):
    return {'machine_id':'M-001','temperature_c':t,'vibration_mm_s':v}


def test_alert_creates_task_and_deduplicates(tmp_path):
    db=tmp_path/'workflow.db'
    a=process_telemetry(payload(),path=db)
    assert a['created'] and a['severity']=='High'
    b=process_telemetry(payload(72),path=db)
    assert not b['created'] and b['incident_id']==a['incident_id']
    assert len(list_incidents(db))==1
    assert len(list_tasks(db))==1
    assert production_impact(db)['machines_needing_review']==['M-001']
    assert process_telemetry(payload(50),path=db)['incident_id'] is None
    assert len(list_incidents(db,'Open'))==1
    with pytest.raises(ValueError):resolve_incident(a['incident_id'],'',db)
    resolve_incident(a['incident_id'],'Checked and cleared',db)
    assert list_incidents(db,'Open')==[]
    assert list_tasks(db)[0]['status']=='Closed'
    assert process_telemetry(payload(),path=db)['created']


def test_oee_real_measurements_only(tmp_path):
    db=tmp_path/'oee.db'
    assert production_summary(db)['oee'] is None
    add_production_event('M-001','WO-1',60,50,30,80,76,path=db)
    m=production_summary(db)['oee']
    assert m['availability_percent']==83.33
    assert m['performance_percent']==80
    assert m['quality_percent']==95
    assert m['oee_percent']==63.33
    with pytest.raises(ValueError):
        add_production_event('M-001','WO-1',60,50,30,110,100,path=db)
