import pandas as pd
import pytest
from smartfactory.integration import SCHEMAS,import_frame,import_csv,clear_dataset,source_status,validate_frame,connect
from smartfactory.industrial import production_metrics,machine_conditions,production_trace,assistant_answer

def test_import_roundtrip(tmp_path):
    db=tmp_path/'data.db'
    rows=pd.DataFrame([{'part':'Bearing','on_hand':12,'reorder_point':15,'daily_demand':2,'lead_days':4}])
    assert import_frame('inventory',rows,path=db)==1
    assert source_status(db)['inventory']['row_count']==1
    with connect(db) as conn:
        assert conn.execute('SELECT on_hand FROM dataset_inventory').fetchone()[0]==12
    clear_dataset('inventory',path=db)
    assert 'inventory' not in source_status(db)

def test_invalid_import_does_not_erase_existing(tmp_path):
    db=tmp_path/'data.db'
    good=pd.DataFrame([{'part':'Bearing','on_hand':12,'reorder_point':15,'daily_demand':2,'lead_days':4}])
    import_frame('inventory',good,path=db)
    with pytest.raises(ValueError):
        import_frame('inventory',pd.DataFrame([{'part':'Bearing','on_hand':12}]),path=db)
    with connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM dataset_inventory').fetchone()[0]==1

def test_reject_untrusted_table_name(tmp_path):
    with pytest.raises(ValueError):
        import_frame('orders;DROP TABLE source_status',pd.DataFrame(),path=tmp_path/'x.db')

def test_empty_and_invalid_quality():
    with pytest.raises(ValueError):
        validate_frame('quality',pd.DataFrame(columns=SCHEMAS['quality']))
    with pytest.raises(ValueError):
        validate_frame('quality',pd.DataFrame([{'serial_number':'S1','work_order':'W1','result':'Maybe','defect':'None'}]))

def test_industrial_missing_sources():
    assert production_metrics(None,None) is None
    assert machine_conditions(None) is None
    assert 'not connected' in assistant_answer('inventory',{'inventory':None}).lower()

def test_conditions():
    df=pd.DataFrame([{'machine_id':'M-001','timestamp':'2026-01-01','temperature_c':90,'vibration_mm_s':2}])
    assert machine_conditions(df).iloc[0]['condition']=='High'

def test_trace_missing():
    assert 'Missing source' in production_trace('S1',None,None,None,None)['status']
