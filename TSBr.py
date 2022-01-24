import time, json, signal, subprocess, urllib, hmac, hashlib, http, traceback, os, datetime
import paho.mqtt.client as mqtt
from daemon import Daemon
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import *
from influxdb import InfluxDBClient

# store checkups to post as one block of checkups
class TSBDaemon(Daemon):
    def run(self):
        ts_bridge = TSB()
        my_path = os.path.dirname(os.path.abspath(__file__))
        with open(my_path + "/ts_br_config.json", "r") as config:
            ts_bridge.config = ts_bridge.config.from_json(config.read())

        ts_bridge.run()

class TSB(mqtt.Client):

    @dataclass_json
    @dataclass
    class config:
        pidfile: str
        data_sources: List[str]
        boot_check_list: Dict[str, List[str]]
        influx_server: str
        influx_port: int
        long_checkup_freq: int
        long_checkup_leng: int
        mqtt_broker: str
        mqtt_port: int
        mqtt_timeout: int

    version = 2022
    topics = []
    pings = 0
    
    def on_log(self, client, userdata, level, buff):
        if level != mqtt.MQTT_LOG_DEBUG:
            print (level)
            print(buff)
        if level == mqtt.MQTT_LOG_ERR:
            traceback.print_exc()
            os._exit(1)
    
    def on_connect(self, client, userdata, flags, rc):
        print("MQTT Connected: " + str(rc))
        for data_source in self.config.data_sources:
            topic = data_source + "/#"
            self.topics += topic
            client.subscribe(topic)
            print ("Subscribed to " + topic)
    
    def on_message(self, client, userdata, msg):
        print("Message received: " + msg.topic)
        body = [{
            "measurement": "maglab",
            "tags": {
                "topic": msg.topic
            },
        }]
        try:
            decoded = msg.payload.decode('utf-8')
        except:
            return
        if len(decoded):
            try:
                my_msg = json.loads(decoded)
                try:
                    my_time = float(my_msg['time'])
                    del my_msg['time']
                    body[0]["time"] = int(my_time * 1000000000)
                except:
                    my_time = time.time()
                    body[0]["time"] = int(my_time * 1000000000)
                body[0]["fields"] = self.int_ification(my_msg)
            except:
                try:
                    body[0]["fields"] = {msg.topic : int(decoded)}
                except:
                    if decoded.lower() == "true" or decoded == "1":
                        body[0]["fields"] = {msg.topic : 1}
                    elif decoded.lower() == "false" or decoded == "0":
                        body[0]["fields"] = {msg.topic : 0}
                    else:
                        body[0]["fields"] = {msg.topic : ''}
                        print("Message could not be entered: " + decoded)
                my_time = time.time()
                body[0]["time"] = int(my_time * 1000000000)
        else:
            body[0]["fields"] = {msg.topic: ''}
            my_time = time.time()
            body[0]["time"] = int(my_time * 1000000000)
        print(body)
        try:
            self.influxDBclient.write_points(body)
        except Exception as err:
            traceback.print_exc()
            print(err)
        return
    
    def signal_handler(self, signum, frame):
        print("Caught a deadly signal!")
        self.running = False

    def int_ification(self, data):
        intified = {}
        for d_name, d_val in data.items():
            if (d_name.endswith("Temp") and type(d_val) is not int):
                try:
                    intified[d_name] = int(d_val)
                except:
                    continue
            elif ((d_name.endswith("Switch") or d_name.endswith("Door")) and type(d_val) is not int):
                if type(d_val) is bool:
                    intified[d_name] = int(d_val)
                elif d_val == "1" or d_val.lower() == "true":
                    intified[d_name] = 1
                else:
                    intified[d_name] = 0
            else:
                intified[d_name] = d_val
        return intified


    def bootup(self):
        boot_checks = {}
        for bc_name, bc_cmd in self.config.boot_check_list.items():
            boot_checks[bc_name] = subprocess.check_output(
                bc_cmd,
                shell=True
            ).decode('utf-8')
        intey = self.int_ification(boot_checks)
        body = [{
            "measurement": "maglab",
            "tags": {
                "topic": "TS_Bridge/Bootup"
            },
            "fields": intey,
            "time": time.time_ns(),
        }]
        print(body)
        self.influxDBclient.write_points(body)

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.running = True

        self.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
        self.influxDBclient = InfluxDBClient(host=self.config.influx_server, port=self.config.influx_port)
        self.influxDBclient.switch_database('maglab')
        self.bootup()
        while self.running:
            try: 
                while self.running:
                    self.loop()
            except:
                traceback.print_exc()

        self.influxDBclient.close()
        self.disconnect()
        exit(0)
