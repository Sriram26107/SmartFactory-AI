"""Optional read-only Modbus TCP poller. Requires `pip install pymodbus`.

Use only approved read-only registers and known engineering unit scaling.
"""
import argparse
import json
import time
from smartfactory.live.telemetry import save_reading
from smartfactory.workflows import process_telemetry

def poll(host,port,unit,machine_id,temp_register,vibration_register,temp_scale,vibration_scale,interval):
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError as exc:
        raise SystemExit('Install optional dependency: pip install pymodbus') from exc
    client=ModbusTcpClient(host,port=port,timeout=5)
    if not client.connect(): raise ConnectionError('Modbus TCP connection failed')
    try:
        while True:
            t=client.read_holding_registers(temp_register,count=1,device_id=unit)
            v=client.read_holding_registers(vibration_register,count=1,device_id=unit)
            if t.isError() or v.isError(): raise RuntimeError('Register read failed')
            payload={'machine_id':machine_id,
                     'temperature_c':t.registers[0]*temp_scale,
                     'vibration_mm_s':v.registers[0]*vibration_scale}
            save_reading(payload,source='modbus')
            process_telemetry(payload,source='modbus')
            print(json.dumps(payload),flush=True)
            time.sleep(interval)
    finally: client.close()

def main():
    parser=argparse.ArgumentParser(description='Read-only Modbus TCP poller')
    parser.add_argument('--host',required=True)
    parser.add_argument('--port',type=int,default=502)
    parser.add_argument('--unit',type=int,default=1)
    parser.add_argument('--machine-id',required=True)
    parser.add_argument('--temp-register',type=int,required=True)
    parser.add_argument('--vibration-register',type=int,required=True)
    parser.add_argument('--temp-scale',type=float,required=True)
    parser.add_argument('--vibration-scale',type=float,required=True)
    parser.add_argument('--interval',type=float,default=3)
    args=parser.parse_args()
    if args.interval < 1: parser.error('Interval must be >= 1 second')
    poll(args.host,args.port,args.unit,args.machine_id,args.temp_register,args.vibration_register,args.temp_scale,args.vibration_scale,args.interval)

if __name__=='__main__': main()
