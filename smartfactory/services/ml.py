import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from smartfactory.data.demo import load_data
FEATURES=['temperature_c','vibration_mm_s','pressure_bar','runtime_hours','energy_kwh']

def labeled_sensor_samples(seed=123, n=3000):
    """Synthetic, explicitly generated failure labels. Not measured failures."""
    rng=np.random.default_rng(seed)
    temperature=rng.normal(70,12,n)
    vibration=np.maximum(.1,rng.normal(3.3,1.2,n))
    pressure=rng.normal(7,.6,n)
    runtime=rng.uniform(100,6500,n)
    energy=rng.uniform(14,40,n)
    logits=(temperature-83)*.13+(vibration-4.4)*1.15+(runtime-4200)*.00035
    probabilities=1/(1+np.exp(-np.clip(logits,-25,25)))
    labels=rng.binomial(1,probabilities)
    X=np.column_stack([temperature,vibration,pressure,runtime,energy])
    return X,labels

def train_demo_model():
    X,y=labeled_sensor_samples()
    Xtrain,Xtest,ytrain,ytest=train_test_split(X,y,test_size=.25,random_state=42,stratify=y)
    model=RandomForestClassifier(n_estimators=80,max_depth=9,random_state=42,n_jobs=-1)
    model.fit(Xtrain,ytrain)
    pred=model.predict(Xtest)
    return model,classification_report(ytest,pred,output_dict=True,zero_division=0),confusion_matrix(ytest,pred).tolist()

def predict_machine_risk(model,sensors):
    latest=sensors.sort_values('timestamp').groupby('machine_id').tail(1).copy()
    latest['failure_probability']=model.predict_proba(latest[FEATURES].to_numpy())[:,1]
    return latest[['machine_id','timestamp']+FEATURES+['failure_probability']].sort_values('failure_probability',ascending=False)
