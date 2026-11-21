import json
from smartfactory.data.demo import load_data

def simulated_messages(count=10):
    """Offline MQTT-compatible JSON payloads; no broker required."""
    for _,r in load_data()['sensors'].head(count).iterrows():
        yield json.dumps({'topic':f'factory/machines/{r.machine_id}/telemetry',
                          'machine_id':r.machine_id,'temperature_c':round(float(r.temperature_c),2),
                          'vibration_mm_s':round(float(r.vibration_mm_s),2)})

def publish_to_broker(host='localhost',port=1883,count=10):
    """Optional local Mosquitto broker; explicitly invoked only by user."""
    import paho.mqtt.client as mqtt
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host,port,60)
    try:
        for message in simulated_messages(count):
            data=json.loads(message)
            info=client.publish(data['topic'],message,qos=1)
            info.wait_for_publish()
    finally:client.disconnect()
