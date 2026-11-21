from sklearn.linear_model import Ridge
import numpy as np

def forecast_next_hour(energy):
    """Lag-1 baseline trained on the provided synthetic time series."""
    values=energy.sort_values('timestamp')['consumption_kwh'].to_numpy()
    if len(values)<8:raise ValueError('At least 8 readings required')
    X=np.column_stack([values[:-1],np.arange(len(values)-1)])
    model=Ridge(alpha=1.0).fit(X,values[1:])
    return round(float(max(0,model.predict([[values[-1],len(values)-1]])[0])),2)
