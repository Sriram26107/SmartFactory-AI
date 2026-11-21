"""Factory metrics. Informational analysis only; never sends control commands."""
import pandas as pd

def production_metrics(orders,quality):
    if orders is None or quality is None:
        return None
    total=len(quality)
    return {'work_orders':int(len(orders)),
            'units_ordered':int(pd.to_numeric(orders['quantity']).sum()),
            'completed_orders':int((orders['status']=='Completed').sum()),
            'inspection_pass_rate_percent':round(100*(quality['result']=='Pass').sum()/total,1) if total else None}

def machine_conditions(sensors):
    if sensors is None or sensors.empty:
        return None
    x=sensors.sort_values('timestamp' if 'timestamp' in sensors.columns else 'received_at').groupby('machine_id').tail(1).copy()
    x['condition']=x.apply(lambda r:'High' if r.temperature_c>=85 or r.vibration_mm_s>=7 else
                            ('Watch' if r.temperature_c>=70 or r.vibration_mm_s>=4.5 else 'Normal'),axis=1)
    return x

def production_trace(serial,quality,orders,bom,requirements):
    if any(x is None for x in (quality,orders,bom,requirements)):
        return {'status':'Missing source: quality, orders, BOM or requirements'}
    matches=quality[quality['serial_number']==serial]
    if matches.empty:
        return {'status':'Serial not found'}
    record=matches.iloc[0].to_dict()
    work=orders[orders['work_order']==record['work_order']]
    if work.empty:
        return {'inspection':record,'status':'Related work order not found'}
    item=work.iloc[0].to_dict()
    return {'inspection':record,'work_order':item,
            'bom':bom[bom['product']==item['product']].to_dict('records'),
            'requirements':requirements[requirements['product']==item['product']].to_dict('records')}

def energy_summary(energy):
    if energy is None or energy.empty:
        return None
    consumed=float(energy['consumption_kwh'].sum())
    renewable=float(energy['renewable_kwh'].sum())
    return {'consumption_kwh':round(consumed,2),'renewable_kwh':round(renewable,2),
            'estimated_grid_kwh':round(max(0,consumed-renewable),2)}

def assistant_answer(question,datasets):
    q=question.lower()
    if any(t in q for t in ('temperature','vibration','machine','maintenance','alert')):
        frame=machine_conditions(datasets.get('sensors'))
        if frame is None:return 'Machine telemetry is not connected.'
        top=frame.sort_values('temperature_c').iloc[-1]
        return f"Highest latest temperature: {top['machine_id']} at {top['temperature_c']:.1f} °C. Condition: {top['condition']} (illustrative thresholds)."
    if any(t in q for t in ('inventory','stock','material','reorder')):
        df=datasets.get('inventory')
        if df is None:return 'Inventory source is not connected.'
        low=df[df['on_hand']<=df['reorder_point']]
        return 'Below reorder point: '+(', '.join(low['part'].astype(str)) if len(low) else 'none')
    if any(t in q for t in ('quality','defect','inspection')):
        df=datasets.get('quality')
        if df is None:return 'Quality source is not connected.'
        return f"Failed inspections: {int((df['result']=='Fail').sum())} of {len(df)}."
    if 'energy' in q:
        return str(energy_summary(datasets.get('energy')) or 'Energy source is not connected.')
    if any(t in q for t in ('production','order','mes')):
        return str(production_metrics(datasets.get('orders'),datasets.get('quality')) or 'Production and/or quality source is not connected.')
    return 'Ask about machine temperature, maintenance, inventory, quality, energy or production.'
