import json
import time
import paho.mqtt.client as mqtt
from os import getenv

PATH_SEPARATOR = '/'
DEV_ROOT = 'dev'
DEV_REQUEST = 'request'
DEV_PIR_ID = 5
DEV_LED_ID = 6
DEV_LDR_ID = 8


def make_dev_path(*parts) -> str:
    return PATH_SEPARATOR.join(parts)


class DeskLampDirector:
    MOVEMENTS_WINDOW = 1*60  # seconds

    def __init__(self, host: str, port: int, device: str):
        self.device = device
        self.client = mqtt.Client()
        self.client.on_connect = lambda client, userdata, flags, rc: \
            self.on_connect(flags, rc)

        self.client.on_message = lambda client, userdata, msg: \
            self.on_message(msg)

        self.client.connect(host, port, 60)

        self.last_ldr = None
        self.movements = []

    def make_request_topic(self):
        return make_dev_path(DEV_ROOT, DEV_REQUEST, self.device)

    def request_ldr_measurement(self):
        topic = self.make_request_topic()
        payload = json.dumps({
            'select': DEV_LDR_ID,
            'payload': {'read': {}}
        })
        self.client.publish(topic, payload)

    def set_led_strip(self, r, g, b):
        topic = self.make_request_topic()
        payload = json.dumps({
            'select': DEV_LED_ID,
            'payload': {
                'set': {
                    'r': r,
                    'g': g,
                    'b': b
                }
            }
        })
        self.client.publish(topic, payload)

    def on_connect(self, flags, rc):
        print("Connected with result code " + str(rc))
        self.client.subscribe(make_dev_path(DEV_ROOT, '#'))

    def process(self):
        now = time.time()
        self.movements = [(t, s) for (t, s) in self.movements if t >= now - self.MOVEMENTS_WINDOW]
        moved = len([s for (t, s) in self.movements if s])
        if not moved:
            # No movement in the last X minutes
            self.set_led_strip(0, 0, 0)
        elif self.last_ldr < 200:
            # Movement and it is dark
            self.set_led_strip(128, 128, 128)

    def on_message(self, msg):
        path = msg.topic.split(PATH_SEPARATOR)
        if len(path) < 3:
            return
        if path[0] != DEV_ROOT or path[2] != self.device:
            return

        try:
            obj = json.loads(msg.payload.decode('utf-8').rstrip('\x00'))
            dev_id = int(path[3]) if len(path) > 3 else None
            if path[1] == 'response':
                new_ldr = obj.get('value', None)
                if new_ldr is not None:
                    self.last_ldr = new_ldr
                    print('LDR=' + str(new_ldr))
                    self.process()
            elif path[1] == 'update':
                if dev_id == DEV_PIR_ID:
                    state = obj.get('state', None)
                    self.request_ldr_measurement()
                    self.movements.append((time.time(), state))
                    self.process()

        except Exception as e:
            print(e)

    def tick(self):
        self.process()


if __name__ == '__main__':
    host = getenv('MQTT_HOST')
    port = getenv('MQTT_PORT', 1883)
    device = getenv('DALEQ_DEVICE')

    if host is None:
        print('Error: MQTT_HOST is required')
        exit()

    if device is None:
        print('Error: DALEQ_DEVICE is required')
        exit()

    d = DeskLampDirector(host, port, device)
    d.client.loop_start()
    while True:
        time.sleep(1)
        d.tick()
