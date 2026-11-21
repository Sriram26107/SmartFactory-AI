import io
import numpy as np
from PIL import Image
from sqlalchemy import create_engine
from smartfactory.data.demo import load_data
from smartfactory.services.ml import train_demo_model,predict_machine_risk
from smartfactory.services.vision import image_features,train_image_classifier,classify_image
from smartfactory.services.rag import search_documents
from smartfactory.services.storage import initialize_db,add_event,list_events
from smartfactory.services.mqtt import simulated_messages
from smartfactory.services.optimization import choose_production_mix
from smartfactory.services.energy_forecast import forecast_next_hour

def test_ml():
    model,report,matrix=train_demo_model()
    p=predict_machine_risk(model,load_data()['sensors'])
    assert len(p)==8 and p.failure_probability.between(0,1).all()
    assert 'accuracy' in report and len(matrix)==2

def test_vision():
    imgs=[];labels=[]
    for i in range(8):
        arr=np.full((20,20,3),40 if i<4 else 220,dtype=np.uint8)
        b=io.BytesIO();Image.fromarray(arr).save(b,format='PNG');imgs.append(b.getvalue());labels.append('ok' if i<4 else 'defect')
    m=train_image_classifier(imgs,labels)
    assert classify_image(m,imgs[0])['predicted_class'] in ('ok','defect')

def test_rag():
    assert search_documents('vibration temperature maintenance',folder='knowledge')

def test_storage():
    e=create_engine('sqlite:///:memory:');initialize_db(e);add_event(e,'M-01','inspection','demo');assert list_events(e)[0]['machine_id']=='M-01'

def test_mqtt():assert len(list(simulated_messages(3)))==3

def test_optimization():
    x=choose_production_mix([{'product':'A','hours':2,'profit':5,'max_units':5},{'product':'B','hours':3,'profit':9,'max_units':4}],10)
    assert sum(i['units'] for i in x)>0

def test_energy():assert forecast_next_hour(load_data()['energy'])>=0
