import json
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt



class MQTT:

    def __init__(self, ctx):
        self.ctx = ctx
        self.client = None
        self.__logOn = False
        self.__nextreconnect = datetime.now()
        self.__subscriber = {}
        self.isEnabled = ctx.cfg.mqtt_enable

    @property
    def logOn(self):
        return self.__logOn

    @logOn.setter
    def logOn(self, value):
        self.__logOn = value

    @property
    def reconnectTime(self):
        return self.__nextreconnect

    def start(self):
        if not self.isEnabled:
            return
        log = self.ctx.log
        cfg = self.ctx.cfg
        log.info("[MQTT] Connecting to MQTT Server [%s:%d] as user [%s]" % (cfg.mqtt_server, cfg.mqtt_port,
                                                                            cfg.mqtt_user))

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_subscribe = self.on_subscribe
            if cfg.mqtt_debug:
                self.client.on_log = self.on_log
            self.client.username_pw_set(cfg.mqtt_user, cfg.mqtt_password)
            self.client.connect(cfg.mqtt_server, cfg.mqtt_port, cfg.mqtt_keepAlive)
            if cfg.mqtt_subscribeTopic is not None:
                self.client.subscribe(cfg.mqtt_subscribeTopic)
            # re-establish subscriptions
            for s in self.__subscriber.keys():
                self.client.subscribe(s)
            self.client.loop_start()
        except Exception as e:
            log.error("Exception on Connecting to MQTT %s" % (str(e)))

    def stop(self):
        if self.client is not None:
            self.ctx.log.info("[MQTT] Stopping MQTT Subscriber")
            self.client.loop_stop()
            self.client = None

    def on_connect(self, client, userdata, flags, rc):
        now = datetime.now()
        log = self.ctx.log
        cfg = self.ctx.cfg
        self.__nextreconnect = (now + timedelta(minutes=cfg.mqtt_reconnect))
        if rc == 0:
            log.debug("[MQTT] Connected to %s:%d with result code %d (success)" % (cfg.mqtt_server, cfg.mqtt_port, rc))
            if cfg.mqtt_silent:
                log.debug("[MQTT] Not showing received MQTT messages in log as 'silent=true' is configured.")
        elif rc == 5:
            log.error("[MQTT] Not connected to %s:%d, result code %d (credentials wrong or missing?)"
                      % (cfg.mqtt_server, cfg.mqtt_port, rc))
        else:
            log.warn("[MQTT] Possibly NOT connected to %s:%d, result code %d (expected 0)"
                     % (cfg.mqtt_server, cfg.mqtt_port, rc))

    def on_log(self, client, userdata, level, buf):
        self.ctx.log.debug("[MQTT] log: %s", str(buf))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.ctx.log.debug("[MQTT] Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_message(self, client, userdata, msg):
        if not self.ctx.cfg.mqtt_retainedMsgs and msg.retain == 1:
            return
        if msg.topic in self.__subscriber:
            callback = self.__subscriber[msg.topic]
            callback(msg.topic, msg.payload.decode("UTF-8"))
        if self.ctx.cfg.mqtt_silent:
            return
        self.ctx.log.debug("[MQTT] Message received %s %s %r" % (msg.topic, str(msg.payload), msg.retain))

    def publish(self, topic, payload):
        if not self.isEnabled:
            return
        if self.client is None:
            self.ctx.log.warn("[MQTT] MQTT is not connected or already gone, not going to publish topic <%s>, "
                              "payload <%s>" %
                              (topic, payload))
            return
        if type(payload) is dict:
            payload = json.dumps(payload)
        self.ctx.log.info("[MQTT] Publish: %s %s" % (topic, payload))
        self.client.publish(topic, payload)

    def subscribe(self, subscribeTopic, callback):
        self.__subscriber[subscribeTopic] = callback
        self.client.subscribe(subscribeTopic)

    def unsubscribe(self, subscribeTopic):
        del self.__subscriber[subscribeTopic]

