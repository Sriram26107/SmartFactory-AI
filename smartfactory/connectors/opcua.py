"""Optional read-only OPC UA sensor poller. Requires `pip install asyncua`.

Node IDs and endpoint must be provided by the factory automation team.
Never writes nodes or issues machine commands.
"""
import argparse
import asyncio
import json
from smartfactory.live.telemetry import save_reading
from smartfactory.workflows import process_telemetry

async def poll(endpoint, machine_id, temp_node, vibration_node, interval):
    try:
        from asyncua import Client
    except ImportError as exc:
        raise SystemExit('Install optional dependency: pip install asyncua') from exc
    async with Client(url=endpoint) as client:
        temp=client.get_node(temp_node)
        vibration=client.get_node(vibration_node)
        while True:
            payload={'machine_id':machine_id,
                     'temperature_c':float(await temp.read_value()),
                     'vibration_mm_s':float(await vibration.read_value())}
            save_reading(payload,source='opcua')
            process_telemetry(payload,source='opcua')
            print(json.dumps(payload),flush=True)
            await asyncio.sleep(interval)

def main():
    parser=argparse.ArgumentParser(description='Read-only OPC UA telemetry poller')
    parser.add_argument('--endpoint',required=True)
    parser.add_argument('--machine-id',required=True)
    parser.add_argument('--temp-node',required=True)
    parser.add_argument('--vibration-node',required=True)
    parser.add_argument('--interval',type=float,default=3)
    args=parser.parse_args()
    if args.interval < 1: parser.error('Interval must be >= 1 second')
    asyncio.run(poll(args.endpoint,args.machine_id,args.temp_node,args.vibration_node,args.interval))

if __name__=='__main__': main()
