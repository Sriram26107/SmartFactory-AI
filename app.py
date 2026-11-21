"""SmartFactory AI: integrated simulation / connected industrial data dashboard."""
import pandas as pd
import plotly.express as px
import streamlit as st
from smartfactory.integration import SCHEMAS, load_factory, import_csv, clear_dataset, connection_summary, connected_latest
from smartfactory.industrial import production_metrics, machine_conditions, production_trace, energy_summary, assistant_answer
from smartfactory.services.operations import schedule, reorder, route_priorities, simulate
from smartfactory.services.ml import train_demo_model, predict_machine_risk
from smartfactory.services.vision import image_features, train_image_classifier, classify_image
from smartfactory.services.rag import search_documents
from smartfactory.services.optimization import choose_production_mix
from smartfactory.services.energy_forecast import forecast_next_hour
from smartfactory.services.storage import get_engine, initialize_db, add_event, list_events
from smartfactory.live.telemetry import recent_readings
from smartfactory.workflows import (list_incidents, list_tasks, resolve_incident,
    add_production_event, production_summary, production_impact)

st.set_page_config(page_title='SmartFactory AI',page_icon='🏭',layout='wide')
st.title('🏭 SmartFactory AI — Industrial Intelligence Platform')
st.caption('Integrated manufacturing data, analytics, AI experiments and live machine monitoring')
mode=st.sidebar.radio('Data source mode',['Simulation','Connected'],help='Connected mode never substitutes generated data for missing real sources.')
st.sidebar.caption('Simulation: generated sample records. Connected: actual MQTT readings and imported enterprise-system CSV records.')

def unavailable(*names):
    st.info('Data source unavailable: '+', '.join(names)+'. Connect MQTT or import the required CSV in IoT & Database.')

def show_table(frame, name):
    if frame is None:unavailable(name);return False
    st.dataframe(frame,width='stretch');return True

def show_plot(frame, x,y,color=None,title=None):
    if frame is None or frame.empty or x not in frame.columns or y not in frame.columns:
        unavailable(x+' / '+y);return
    st.plotly_chart(px.line(frame,x=x,y=y,color=color,title=title),width='stretch')

@st.fragment(run_every='3s')
def refresh_panel():
    data,origins=load_factory(mode)
    summary=connection_summary(mode,data,origins)
    connected=sum(s['status']=='Connected' for s in summary)
    a,b,c=st.columns(3)
    a.metric('Data mode',mode)
    b.metric('Connected datasets',connected if mode=='Connected' else 'Demo')
    c.metric('Disconnected datasets',sum(s['status']=='Disconnected' for s in summary) if mode=='Connected' else 0)
    st.dataframe(pd.DataFrame(summary),width='stretch',hide_index=True)

# Each tab loads its data through the same source-aware layer. In Connected mode,
# missing sources remain unavailable rather than falling back to synthetic values.
d,origins=load_factory(mode)
tabs=st.tabs(['Overview','MES & production','Maintenance','Quality & digital thread',
              'Supply chain','Energy & microgrid','Digital twin','Engineering & PLM',
              'AI assistant','ML & CV Lab','IoT & Database','Live monitoring'])

with tabs[0]:
    st.subheader('Factory overview')
    refresh_panel()
    metrics=production_metrics(d['orders'],d['quality'])
    if metrics:
        c1,c2,c3=st.columns(3)
        c1.metric('Work orders',metrics['work_orders'])
        c2.metric('Completed orders',metrics['completed_orders'])
        c3.metric('Inspection pass rate',str(metrics['inspection_pass_rate_percent'])+'%')
    else:unavailable('orders','quality')
    st.subheader('Operational incident overview')
    impact=production_impact()
    st.metric('Open machine incidents',impact['open_incidents'])
    if impact['machines_needing_review']:
        st.warning('Machines requiring review: '+', '.join(impact['machines_needing_review']))
    st.caption('Alerts indicate potential production impact, not verified downtime.')
    st.subheader('Machine temperatures')
    show_plot(d['sensors'],'timestamp','temperature_c','machine_id')
    st.subheader('Machine registry')
    show_table(d['machines'],'machines')

with tabs[1]:
    st.subheader('Production work orders')
    if show_table(d['orders'],'orders'):
        st.subheader('Priority-first scheduling')
        st.dataframe(schedule(d['orders']),width='stretch')
        st.caption('Informational scheduling heuristic; no machine control commands.')
    metrics=production_metrics(d['orders'],d['quality'])
    if metrics:st.json(metrics)
    else:unavailable('orders','quality')
    st.subheader('Measured production events and OEE')
    st.caption('Enter real observed cycle counts and operating time. Simulation mode entries are clearly marked as manually entered.')
    with st.form('production_event'):
        x,y=st.columns(2)
        machine=x.text_input('Machine ID for event',value='M-001')
        order=y.text_input('Work order ID for event',value='WO-001')
        planned=x.number_input('Planned production minutes',min_value=1.0,value=60.0)
        runtime=y.number_input('Actual running minutes',min_value=0.0,value=50.0)
        cycle=x.number_input('Ideal cycle time (seconds per unit)',min_value=0.01,value=30.0)
        units=y.number_input('Total produced units',min_value=0,step=1,value=80)
        good=x.number_input('Good units',min_value=0,step=1,value=76)
        if st.form_submit_button('Save measured production event'):
            try:
                add_production_event(machine,order,planned,runtime,cycle,units,good)
                st.success('Production event recorded')
            except ValueError as exc:st.error(str(exc))
    summary=production_summary()
    if summary['oee']:st.json(summary['oee'])
    else:st.info('OEE unavailable until production measurements are recorded.')
    if summary['events']:st.dataframe(pd.DataFrame(summary['events']),width='stretch')
    st.caption('OEE is computed only from entered observations; missing production data is never fabricated.')

with tabs[2]:
    st.subheader('Machine condition monitoring')
    conditions=machine_conditions(d['sensors'])
    if conditions is None:unavailable('sensors')
    else:
        st.dataframe(conditions,width='stretch')
        st.plotly_chart(px.bar(conditions,x='machine_id',y='temperature_c',color='condition'),width='stretch')
    st.subheader('Automatically generated maintenance tasks')
    incidents=list_incidents()
    if incidents:
        st.dataframe(pd.DataFrame(incidents),width='stretch')
        open_items=[i for i in incidents if i['status']=='Open']
        if open_items:
            with st.form('resolve_incident'):
                choice=st.selectbox('Open incident to resolve', [i['id'] for i in open_items])
                resolution=st.text_input('Technician resolution note')
                if st.form_submit_button('Mark reviewed and resolved'):
                    try:
                        resolve_incident(choice,resolution)
                        st.success('Incident resolved; associated maintenance task closed')
                    except ValueError as exc:st.error(str(exc))
        st.dataframe(pd.DataFrame(list_tasks()),width='stretch')
    else:st.info('No threshold incidents recorded. Run the simulator or connect MQTT telemetry.')
    st.subheader('Service lifecycle')
    show_table(d['service'],'service')
    st.caption('High/Watch/Normal use illustrative thresholds; they are not validated failure predictions.')

with tabs[3]:
    st.subheader('Inspection records and product traceability')
    if show_table(d['quality'],'quality'):
        serial=st.selectbox('Trace serial number',d['quality']['serial_number'].astype(str).tolist())
        st.json(production_trace(serial,d['quality'],d['orders'],d['bom'],d['requirements']))
    st.subheader('Image feature inspection')
    upload=st.file_uploader('Upload a product image',type=['png','jpg','jpeg'],key='metadata')
    if upload:
        st.image(upload,width='content')
        st.json({'image_features':image_features(upload.getvalue()).round(4).tolist()})
    st.caption('Image features alone are not defect detection. Train a labeled classifier in ML & CV Lab.')

with tabs[4]:
    st.subheader('Inventory planning')
    if d['inventory'] is None:unavailable('inventory')
    else:st.dataframe(reorder(d['inventory']),width='stretch')
    st.subheader('Delivery priority')
    if d['deliveries'] is None:unavailable('deliveries')
    else:st.dataframe(route_priorities(d['deliveries']),width='stretch')
    st.caption('Delivery priority is not GPS route optimization.')

with tabs[5]:
    st.subheader('Energy consumption and renewables')
    result=energy_summary(d['energy'])
    if result:
        st.json(result)
        show_plot(d['energy'],'timestamp','consumption_kwh','facility')
    else:unavailable('energy')
    st.caption('Energy readings require an energy-meter/EMS source; MQTT power (kW) is not automatically treated as energy (kWh).')

with tabs[6]:
    st.subheader('Production scenario simulator')
    a,b,c=st.columns(3)
    machines=a.slider('Active machines',1,20,8)
    util=b.slider('Utilization (%)',10,100,75)
    downtime=c.slider('Downtime (%)',0,40,5)
    st.json(simulate(machines,util,downtime))
    if d['machines'] is not None:st.caption(f"Machine registry connected: {len(d['machines'])} machines. Scenario inputs are manually chosen.")
    else:st.caption('Scenario inputs are manually chosen. Machine registry is not connected.')
    st.caption('What-if planning model, not a calibrated physics-based digital twin.')

with tabs[7]:
    st.subheader('Product engineering / bill of materials')
    show_table(d['bom'],'bom')
    st.subheader('Requirements and verification')
    show_table(d['requirements'],'requirements')
    st.caption('Connect BOM and requirements exports from authorized PLM systems; no CAD/PLM writeback.')

with tabs[8]:
    st.subheader('Factory data assistant')
    q=st.text_input('Ask about machine temperatures, maintenance, inventory, quality, energy or production')
    if q:st.write(assistant_answer(q,d))
    st.subheader('Reference document search')
    question=st.text_input('Search local manufacturing reference documents')
    if question:st.json(search_documents(question,'knowledge'))
    st.caption('Rule-based structured answers and TF-IDF document retrieval; not a generative LLM.')

@st.cache_resource
def trained_model():return train_demo_model()

with tabs[9]:
    st.subheader('Predictive-maintenance ML experiment')
    model,report,matrix=trained_model()
    st.json({'held_out_synthetic_test_metrics':report,'confusion_matrix':matrix})
    if mode=='Simulation' and d['sensors'] is not None:
        st.dataframe(predict_machine_risk(model,d['sensors']),width='stretch')
    else:
        st.info('Synthetic model predictions are intentionally disabled for connected machines. Train and validate a model with actual labeled equipment history first.')
    st.subheader('Train an image defect classifier')
    ok=st.file_uploader('OK images (at least 3)',type=['png','jpg','jpeg'],accept_multiple_files=True,key='ok')
    bad=st.file_uploader('Defect images (at least 3)',type=['png','jpg','jpeg'],accept_multiple_files=True,key='bad')
    if len(ok)>=3 and len(bad)>=3:
        try:
            cv=train_image_classifier([f.getvalue() for f in ok+bad],['OK']*len(ok)+['Defect']*len(bad))
            sample=st.file_uploader('Classify image',type=['png','jpg','jpeg'],key='classify')
            if sample:st.json(classify_image(cv,sample.getvalue()))
        except Exception as exc:st.error(str(exc))
    st.subheader('Integer-programming production mix')
    st.json(choose_production_mix([{'product':'Housing-A','hours':2,'profit':5,'max_units':10},
                                   {'product':'Valve-C','hours':3,'profit':9,'max_units':8}],capacity_hours=25))
    if d['energy'] is not None and len(d['energy'])>=5:
        st.metric('Estimated next-hour energy (kWh)',forecast_next_hour(d['energy']))
    else:unavailable('energy')
    st.caption('ML and optimization experiments are illustrative; models require site-specific validation.')

with tabs[10]:
    st.subheader('Connected factory data manager')
    st.write('Import authorized CSV exports from MES, ERP, quality, energy, and PLM systems. Each import replaces that dataset in the local database.')
    selected=st.selectbox('Dataset',list(SCHEMAS))
    st.code(','.join(SCHEMAS[selected]),language='text')
    csv=st.file_uploader('CSV file',type=['csv'],key='csv')
    if csv and st.button('Validate and import dataset'):
        try:
            count=import_csv(selected,csv.getvalue())
            st.success(f'Imported {count} rows into {selected}. Refresh the page to update all tabs.')
        except Exception as exc:st.error(f'Import rejected: {exc}')
    if st.button('Disconnect selected dataset'):
        clear_dataset(selected)
        st.warning(f'{selected} disconnected. Refresh the page to update all tabs.')
    st.subheader('Operational workflow status')
    st.json(production_impact())
    st.caption('Threshold alerts automatically open maintenance tasks; resolution requires operator confirmation.')
    st.subheader('Connected source status')
    st.dataframe(pd.DataFrame(connection_summary(mode,d,origins)),width='stretch',hide_index=True)
    st.subheader('Event log')
    try:
        engine=get_engine();initialize_db(engine)
        with st.form('event_form'):
            mid=st.text_input('Machine ID',value='M-001')
            kind=st.selectbox('Event type',['Inspection','Alert','Maintenance','Other'])
            note=st.text_input('Note')
            if st.form_submit_button('Save event'):
                add_event(engine,mid,kind,note)
                st.success('Event saved')
        st.dataframe(list_events(engine),width='stretch')
    except Exception as exc:st.error(f'Event database unavailable: {exc}')
    st.caption('Connected mode never fills missing enterprise datasets with demo records.')

with tabs[11]:
    st.subheader('Live machine monitoring')
    st.caption('Auto-refreshes every 3 seconds. Connect MQTT, API, OPC UA or Modbus for real devices, or use the local simulator for testing.')
    @st.fragment(run_every='3s')
    def live_panel():
        if mode=='Connected':
            rows=connected_latest(max_age_seconds=60)
            if not rows:
                st.info('No connected readings received. Start a compatible data connector.')
                return
            latest=pd.DataFrame(rows)
            st.dataframe(latest,width='stretch')
            st.metric('Machines currently reporting',int((latest['connection']=='Live').sum()))
            st.metric('Stale machines',int((latest['connection']=='Stale').sum()))
            recent=pd.DataFrame([r for r in recent_readings(1000) if r['source'] in ('mqtt','api','opcua','modbus')])
        else:
            recent=pd.DataFrame(recent_readings(1000))
            recent=recent[recent['source']=='simulator'] if not recent.empty else recent
            if recent.empty:
                st.info('Start: python -m smartfactory.live.simulator --interval 2')
                return
            latest=recent.groupby('machine_id').tail(1)
            st.dataframe(latest,width='stretch')
            st.metric('Simulated machines',len(latest))
        if not recent.empty:
            st.plotly_chart(px.line(recent,x='received_at',y='temperature_c',color='machine_id',title='Temperature (°C)'),width='stretch')
            st.plotly_chart(px.line(recent,x='received_at',y='vibration_mm_s',color='machine_id',title='Vibration (mm/s)'),width='stretch')
    live_panel()

st.divider()
st.caption('SmartFactory AI | AI-Powered Smart Manufacturing & Industrial Intelligence Platform')
