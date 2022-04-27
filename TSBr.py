import time, json, signal, subprocess, urllib, hmac, hashlib, http, traceback, os, datetime, atexit, logging
import paho.mqtt.client as mqtt
from daemon import Daemon
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import *
from threading import Event
from influxdb import InfluxDBClient

# daemon inherited class
class TSBDaemon(Daemon):
    def run(self):
        # load configuration
        ts_bridge = TSB()
        my_path = os.path.dirname(os.path.abspath(__file__))
        with open(my_path + "/ts_br_config.json", "r") as config:
            ts_bridge.config = ts_bridge.config.from_json(config.read())

        ts_bridge.run()

# main class, inheriting paho mqtt 
class TSB(mqtt.Client):

    @dataclass_json
    @dataclass
    class config:
        pidfile: str
        data_sources: List[str]
        boot_check_list: Dict[str, List[str]]
        influx_server: str
        influx_port: int
        loglevel: str
        long_checkup_freq: int
        long_checkup_leng: int
        mqtt_broker: str
        mqtt_port: int
        mqtt_timeout: int

    version = 2022
    topics = []
    pings = 0
   
    # paho logging
    def on_log(self, client, userdata, level, buff):
        if level == mqtt.MQTT_LOG_DEBUG:
            logging.debug("PAHQ MQTT DEBUG: " + buff)
        elif level == mqtt.MQTT_LOG_INFO:
            logging.info("PAHO MQTT INFO: " + buff)
        elif level == mqtt.MQTT_LOG_NOTICE:
            logging.info("PAHO MQTT NOTICE: " + buff)
        elif level == mqtt.MQTT_LOG_WARNING:
            logging.warning("PAHO MQTT WARN: " + buff)
        else:
            logging.error("PAHQ MQTT ERROR: " + buff)
    
    # subscribe to topics when connected
    def on_connect(self, client, userdata, flags, rc):
        logging.info("MQTT Connected: " + str(rc))
        for data_source in self.config.data_sources:
            topic = data_source + "/#"
            self.topics += topic
            client.subscribe(topic)
            logging.info("Subscribed to " + topic)
    
    # mqtt message parsing
    # all messages are converted into integers for grafana
    def on_message(self, client, userdata, msg):
        logging.info("Message received: " + msg.topic)
        body = [{
            "measurement": "maglab",
            "tags": {
                "topic": msg.topic
            },
        }]
        # decode as UTF-8
        try:
            decoded = msg.payload.decode('utf-8')
        except:
            return

        # is there a message in the topic
        if len(decoded):
            try:
                # try decoding as json
                my_msg = json.loads(decoded)
                # add the time for tsdb
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
                    # decode int-only messages
                    body[0]["fields"] = {msg.topic : int(decoded)}
                except:
                    # decode true/false messages
                    if decoded.lower() == "true" or decoded == "1":
                        body[0]["fields"] = {msg.topic : 1}
                    elif decoded.lower() == "false" or decoded == "0":
                        body[0]["fields"] = {msg.topic : 0}
                    else:
                        body[0]["fields"] = {msg.topic : ''}
                        logging.warn("Message could not be entered: " + decoded)
                my_time = time.time()
                body[0]["time"] = int(my_time * 1000000000)
        else:
            # add time for tsdb
            body[0]["fields"] = {msg.topic: ''}
            my_time = time.time()
            body[0]["time"] = int(my_time * 1000000000)
        logging.debug(body)

        # insert into db
        try:
            self.influxDBclient.write_points(body)
        except Exception as err:
            logging.error(err)
            logging.error(traceback.format_exc())
        return
    
    def signal_handler(self, signum, frame):
        print("Caught a deadly signal!")
        self.running = False

    # message int conversion helper
    def int_ification(self, data):
        intified = {}
        for d_name, d_val in data.items():
            # within json-type messages, temperatures are integers (/1000)
            if (d_name.endswith("Temp") and type(d_val) is not int):
                try:
                    intified[d_name] = int(d_val)
                except:
                    continue
            # within json-type messages, switches and doors are boolean
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


    def on_disconnect(self, client, userdata, rc):
        logging.info("Disconnected with: " + str(rc))
        if rc != 0:
            logging.error("Unexpected diconnection.  Attempting reconnection.")
            reconnect_count = 0
            while (reconnect_count < 10):
                try:
                    reconnect_count += 1
                    self.reconnect()
                    break
                except OSError:
                    logging.error("Connection error while trying to reconnect.")
                    logging.error(traceback.format_exc())
                    logging.error("Waiting to restart")
                    self.tEvent.wait(30)
            if reconnect_count == 10:
                logging.critical("Too many reconnect tries.  Exiting.")
                os._exit(1)

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
        logging.debug(body)
        self.influxDBclient.write_points(body)

    def run(self):
        self.tEvent = Event()
        self.running = True
        startup_count = 0
        while (startup_count < 10):
            try:
                startup_count += 1
                if self.config.loglevel and type(logging.getLevelName(self.config.loglevel)) is int:
                    logging.basicConfig(level=self.config.loglevel)
                else:
                    logging.warning("Log level not configured.  Defaulting to WARNING.")

                signal.signal(signal.SIGINT, self.signal_handler)
                signal.signal(signal.SIGTERM, self.signal_handler)

                self.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
                atexit.register(self.disconnect)
                self.influxDBclient = InfluxDBClient(host=self.config.influx_server, port=self.config.influx_port)
                atexit.register(self.influxDBclient.close)
                self.influxDBclient.switch_database('maglab')
                self.bootup()
                break
            except OSError:
                logging.error("Error connecting on bootup.")
                logging.error(traceback.format_exc())
                logging.error("Waiting to reconnect.")
                self.tEvent.wait(30)

        if startup_count == 10:
            logging.critical("Too many startup tries.  Exiting.")
            os._exit(1)
        logging.info("Startup success.")
        self.reconnect_me = False
        self.inner_reconnect_try = 0
        while self.running and (self.inner_reconnect_try < 10):
            try:
                if self.reconnect_me == True:
                    self.reconnect()
                    self.reconnect_me = False
                self.loop()
                self.inner_reconnect_try = 0
            except (socket.timeout, TimeoutError, ConnectionError):
                self.inner_reconnect_try += 1
                self.reconnect_me = True
                logging.error("MQTT loop error.  Attempting to reconnect: " + inner_reconnect_try)
            except:
                logging.critical("Exception in mqtt loop.")
                logging.critical(traceback.format_exc())
                logging.critical("Exiting.")
                exit(2)
        if self.inner_reconnect_try == 10:
            exit(1)

        exit(0)
