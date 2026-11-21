import pandas as pd

def risk_scores(sensors):
    g=sensors.groupby('machine_id').agg(max_temp=('temperature_c','max'),max_vibration=('vibration_mm_s','max'),avg_temp=('temperature_c','mean'),avg_vibration=('vibration_mm_s','mean')).reset_index()
    g['score']=((g.max_temp>82)*40+(g.max_vibration>4.8)*35+(g.avg_temp>75)*10+(g.avg_vibration>3.8)*15).clip(0,100)
    g['risk']=g.score.apply(lambda x:'High' if x>=60 else ('Medium' if x>=30 else 'Low'))
    return g.round(2)

def kpis(orders,quality):
    total=len(quality); passed=int((quality.result=='Pass').sum())
    return {'work_orders':len(orders),'units_ordered':int(orders.quantity.sum()),'completed_orders':int((orders.status=='Completed').sum()),'pass_rate_percent':round(passed/total*100,1) if total else 0}

def schedule(orders):
    x=orders[orders.status!='Completed'].sort_values(['priority','hours']).copy()
    x['sequence']=range(1,len(x)+1);x['cumulative_hours']=x.hours.cumsum()
    return x

def reorder(inventory):
    x=inventory.copy();x['days_of_stock']=(x.on_hand/x.daily_demand).round(1)
    x['reorder']=x.on_hand<=x.reorder_point
    x['suggested_quantity']=(x.daily_demand*x.lead_days*1.25-x.on_hand).clip(lower=0).round().astype(int)
    return x

def route_priorities(deliveries):
    x=deliveries.sort_values(['priority','due_hours','distance_km']).copy();x['sequence']=range(1,len(x)+1)
    return x

def energy_kpis(energy):
    total=float(energy.consumption_kwh.sum());renewable=float(energy.renewable_kwh.sum())
    return {'consumption_kwh':round(total,1),'renewable_kwh':round(renewable,1),'estimated_grid_kwh':round(max(total-renewable,0),1),'renewable_share_percent':round(renewable/total*100,1) if total else 0}

def simulate(machines,utilization,downtime):
    eff=8*utilization/100*(1-downtime/100)
    return {'units_per_shift':round(machines*eff*14),'energy_kwh_per_shift':round(machines*8*(16+12*utilization/100)*(1-downtime/100),1),'effective_hours_per_machine':round(eff,2)}

def trace(serial,data):
    q=data['quality'].loc[data['quality'].serial_number==serial]
    if q.empty:return {'error':'Serial number not found'}
    item=q.iloc[0];wo=data['orders'].loc[data['orders'].work_order==item.work_order]
    order=wo.iloc[0].to_dict() if not wo.empty else {}
    bom=data['bom'].loc[data['bom']['product']==order.get('product','')].to_dict('records')
    req=data['requirements'].loc[data['requirements']['product']==order.get('product','')].to_dict('records')
    return {'serial':serial,'inspection':item.to_dict(),'work_order':order,'bill_of_materials':bom,'requirements':req}

def assistant(question,data,risk):
    q=question.lower()
    if any(w in q for w in ('machine','failure','maintenance','risk')):
        x=risk.sort_values('score').iloc[-1];return f'{x.machine_id} has the highest illustrative risk score ({x.score}/100). Review temperature and vibration. This is not a validated failure prediction.'
    if any(w in q for w in ('inventory','stock','material','supplier')):
        low=reorder(data['inventory']);return 'Reorder candidates: '+', '.join(low.loc[low.reorder,'part'].tolist())
    if any(w in q for w in ('quality','defect','inspection')):
        return f"{int((data['quality'].result=='Fail').sum())} failed inspections in the synthetic sample."
    if 'energy' in q:return str(energy_kpis(data['energy']))
    if any(w in q for w in ('production','order','mes')):return str(kpis(data['orders'],data['quality']))
    return 'Ask about machine risk, inventory, quality, energy, or production.'
