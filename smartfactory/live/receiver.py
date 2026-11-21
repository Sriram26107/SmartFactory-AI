"""Read-only MQTT receiver. No machine control or publishing."""
import argparse
import json
import os
import ssl
import paho.mqtt.client as mqtt
from smartfactory.live.telemetry import save_reading
from smartfactory.workflows import process_telemetry

def main():
    parser=argparse.ArgumentParser(description='SmartFactory MQTT telemetry receiver')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=1883)
    parser.add_argument('--topic',default='factory/machines/+/telemetry')
    parser.add_argument('--username',default=os.getenv('MQTT_USERNAME'))
    parser.add_argument('--password-env',default='MQTT_PASSWORD',help='Environment variable containing broker password')
    parser.add_argument('--tls',action='store_true',help='Enable TLS, using trusted CA certificates')
    parser.add_argument('--ca-file',default=None)
    args=parser.parse_args()
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if args.username:
        password=os.getenv(args.password_env)
        if not password:parser.error(f'Environment variable {args.password_env} is required when username is set')
        client.username_pw_set(args.username,password)
    if args.tls:
        client.tls_set(ca_certs=args.ca_file,cert_reqs=ssl.CERT_REQUIRED,tls_version=ssl.PROTOCOL_TLS_CLIENT)
    def on_connect(client,userdata,flags,reason_code,properties):
        if reason_code==0:
            client.subscribe(args.topic,qos=1)
            print('Subscribed:',args.topic,flush=True)
        else:print('Broker connection rejected:',reason_code,flush=True)
    def on_message(client,userdata,msg):
        try:
            payload=json.loads(msg.payload.decode('utf-8'))
            parts=msg.topic.split('/')
            if len(parts)!=4 or parts[:2]!=['factory','machines'] or parts[3]!='telemetry':
                raise ValueError('Unexpected MQTT topic')
            if not isinstance(payload,dict) or payload.get('machine_id')!=parts[2]:
                raise ValueError('Topic machine ID mismatch')
            result=save_reading(payload,source='mqtt')
            workflow=process_telemetry(payload,source='mqtt')
            if workflow['created']:
                print('Maintenance incident opened:',workflow['incident_id'],flush=True)
            print('Received:',result['machine_id'],result['temperature_c'],'C',flush=True)
        except (ValueError,UnicodeDecodeError,TypeError) as exc:
            print('Rejected message:',exc,flush=True)
    client.on_connect=on_connect
    client.on_message=on_message
    print(f'Connecting to {args.host}:{args.port}. Ctrl+C to stop.',flush=True)
    client.connect(args.host,args.port,60)
    try:client.loop_forever()
    except KeyboardInterrupt:print('Stopped')
    finally:client.disconnect()

if __name__=='__main__':main()
