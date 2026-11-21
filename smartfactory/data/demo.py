import numpy as np
import pandas as pd

def load_data(seed=42):
    rng=np.random.default_rng(seed)
    machines=pd.DataFrame([{'machine_id':f'M-{i:02d}','line':f'LINE-{(i-1)//3+1}','type':'CNC' if i%2 else 'Assembly'} for i in range(1,9)])
    n=360
    sensors=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=n,freq='h'),'machine_id':rng.choice(machines.machine_id,n),'temperature_c':rng.normal(69,9,n),'vibration_mm_s':rng.normal(3.1,.9,n).clip(.2),'pressure_bar':rng.normal(7,.5,n),'runtime_hours':rng.uniform(300,6000,n),'energy_kwh':rng.uniform(15,35,n)})
    sensors.loc[rng.choice(sensors.index,20,replace=False),'temperature_c']+=18
    orders=pd.DataFrame([{'work_order':f'WO-{1000+i}','product':p,'quantity':q,'priority':pr,'hours':h,'status':s,'line':line} for i,(p,q,pr,h,s,line) in enumerate([('Housing-A',120,1,5,'In progress','LINE-1'),('Bracket-B',80,2,3,'Released','LINE-2'),('Valve-C',200,1,7,'Released','LINE-1'),('Housing-A',60,3,2,'Completed','LINE-3'),('Panel-D',90,2,4,'On hold','LINE-2')],1)])
    quality=pd.DataFrame([{'serial_number':f'SN-{i:04d}','work_order':wo,'result':res,'defect':defect} for i,(wo,res,defect) in enumerate([('WO-1001','Pass','None'),('WO-1001','Pass','None'),('WO-1002','Fail','Scratch'),('WO-1003','Pass','None'),('WO-1004','Fail','Dimension'),('WO-1005','Pass','None')],1)])
    inventory=pd.DataFrame([{'part':'Steel blank','on_hand':180,'reorder_point':200,'daily_demand':25,'lead_days':8},{'part':'Bearing','on_hand':420,'reorder_point':150,'daily_demand':8,'lead_days':12},{'part':'Drive motor','on_hand':35,'reorder_point':50,'daily_demand':4,'lead_days':18}])
    deliveries=pd.DataFrame([{'delivery':'DEL-01','destination':'North','distance_km':42,'priority':1,'due_hours':8},{'delivery':'DEL-02','destination':'West','distance_km':28,'priority':2,'due_hours':12},{'delivery':'DEL-03','destination':'East','distance_km':65,'priority':1,'due_hours':10}])
    energy=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=72,freq='h'),'facility':rng.choice(['Production','Warehouse','Office'],72),'consumption_kwh':rng.uniform(25,110,72),'renewable_kwh':rng.uniform(0,35,72)})
    bom=pd.DataFrame([{'product':'Housing-A','component':'Steel blank','units_per_product':2},{'product':'Bracket-B','component':'Steel blank','units_per_product':1},{'product':'Valve-C','component':'Bearing','units_per_product':2},{'product':'Panel-D','component':'Drive motor','units_per_product':1}])
    requirements=pd.DataFrame([{'requirement_id':'REQ-001','product':'Housing-A','requirement':'Surface inspection before release','verification':'Quality record'},{'requirement_id':'REQ-002','product':'Valve-C','requirement':'Component traceability','verification':'Work order and BOM link'}])
    service=pd.DataFrame([{'machine_id':'M-01','service_type':'Preventive inspection','status':'Scheduled'},{'machine_id':'M-03','service_type':'Bearing replacement','status':'Completed'}])
    return dict(machines=machines,sensors=sensors,orders=orders,quality=quality,inventory=inventory,deliveries=deliveries,energy=energy,bom=bom,requirements=requirements,service=service)
