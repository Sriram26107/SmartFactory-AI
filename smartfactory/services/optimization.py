from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np

def choose_production_mix(products,capacity_hours=40):
    """Integer programming: maximize profit under one shared machine-hour capacity."""
    hours=np.array([p['hours'] for p in products],dtype=float)
    profit=np.array([p['profit'] for p in products],dtype=float)
    limits=np.array([p['max_units'] for p in products],dtype=float)
    result=milp(c=-profit,integrality=np.ones(len(products)),bounds=Bounds(np.zeros(len(products)),limits),constraints=LinearConstraint(hours.reshape(1,-1),-np.inf,capacity_hours))
    if not result.success:raise RuntimeError(result.message)
    return [{'product':p['product'],'units':int(round(x))} for p,x in zip(products,result.x)]
