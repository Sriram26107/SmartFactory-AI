from smartfactory.data.demo import load_data
from smartfactory.services.operations import risk_scores,kpis,schedule,reorder,energy_kpis,simulate,trace

def test_factory_workflows():
    d=load_data();assert len(d['machines'])==8
    assert len(risk_scores(d['sensors']))==8
    assert 0<=kpis(d['orders'],d['quality'])['pass_rate_percent']<=100
    assert len(schedule(d['orders']))==4
    assert 'reorder' in reorder(d['inventory']).columns
    assert energy_kpis(d['energy'])['consumption_kwh']>0
    assert simulate(5,80,10)['units_per_shift']>0
    assert trace('SN-0001',d)['work_order']['work_order']=='WO-1001'
