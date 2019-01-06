#!/usr/bin/python

import platform
import logging
import paho.mqtt.client as mqtt

TOPIC_ROOT = "lights/nexa"

class MqttDaemon:
    def __init__(self, broker_addr):
        self.log = logging.getLogger("mqtt")
        self.broker_addr = broker_addr
        self.message_callback = None

    def set_message_callback(self, cb):
        self.message_callback = cb

    def run(self):
        client_id = "%s-%s" % ("ook-switch", platform.node())

        client = mqtt.Client(client_id=client_id, clean_session=True)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(self.broker_addr)
        self.log.info("Connected as %s" % client_id)
        
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Connected: %s" % rc)

        client.subscribe("$SYS/broker/version")
        client.subscribe("%s/#" % TOPIC_ROOT)

    def on_message(self, client, userdata, msg):
        self.log.debug("Message: %s %s" % (msg.topic, msg.payload))

        if str(msg.topic).startswith(TOPIC_ROOT):
            t = msg.topic[len(TOPIC_ROOT)+1:].split("/")
            self.log.info("Light message: %s: %s" % (t, msg.payload))
            group = int(t[0], 0)
            switch = int(t[1], 0)
            action = t[2]
            if action == "switch":
                status = msg.payload.decode("ascii")
                try:
                    on = {"ON": True, "OFF": False}[status]
                    self.message_callback(group, switch, on)
                except (KeyError, RuntimeError) as e:
                    self.log.error(e)
                    status = "ERROR"
                client.publish("%s/%s/%s/%s" % (TOPIC_ROOT, t[0], t[1], "status"),
                        status)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    d = MqttDaemon("localhost")
    d.run()
