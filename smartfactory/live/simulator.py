"""Run: python -m smartfactory.live.simulator [--mqtt]"""
import argparse
import json
import math
import random
import time
from smartfactory.live.telemetry import save_reading
from smartfactory.workflows import process_telemetry

def readings(count=4):
    for i in range(count):
        yield {"machine_id": f"M-{i+1:03d}",
               "temperature_c": round(52 + 9 * math.sin(time.time()/25+i) + random.uniform(-3, 3), 2),
               "vibration_mm_s": round(max(0, 2.4 + 1.4 * math.sin(time.time()/18+i) + random.uniform(-0.5, 0.5)), 2),
               "pressure_bar": round(5 + random.uniform(-0.5, 0.5), 2),
               "energy_kw": round(7 + random.uniform(-1.5, 1.5), 2)}

def main():
    parser=argparse.ArgumentParser(description="Local live sensor simulator")
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--machines", type=int, default=4)
    parser.add_argument("--mqtt", action="store_true", help="Publish to local MQTT broker instead of SQLite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    args=parser.parse_args()
    if args.interval <= 0 or not 1 <= args.machines <= 100:
        parser.error("interval must be > 0 and machines must be between 1 and 100")
    client=None
    if args.mqtt:
        import paho.mqtt.client as mqtt
        client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(args.host,args.port,60)
        client.loop_start()
    print("Streaming readings. Ctrl+C to stop.", flush=True)
    try:
        while True:
            for data in readings(args.machines):
                if client:
                    info=client.publish(f"factory/machines/{data['machine_id']}/telemetry",json.dumps(data),qos=1)
                    info.wait_for_publish(timeout=10)
                    if not info.is_published():
                        raise RuntimeError("MQTT publish failed")
                else:
                    save_reading(data,source="simulator")
                    process_telemetry(data,source="simulator")
                print(json.dumps(data),flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        if client:
            client.loop_stop()
            client.disconnect()

if __name__=="__main__":
    main()
