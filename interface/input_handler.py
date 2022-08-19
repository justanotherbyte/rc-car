import json
from typing import (
    Optional,
    Callable,
    Tuple
)
from queue import Queue, Empty
from threading import Thread

import redis
from kivy.uix.slider import Slider
from kivy.clock import Clock


def read_redis_config() -> Tuple[str, int, str]:
    with open("redis.json", "r") as f:
        data = json.load(f)

    host = data["host"]
    port = data["port"]
    password = data["password"]

    return (host, port, password)

class Message:
    def __init__(
        self,
        *,
        direction: Optional[Tuple[float, float]] = None,
        stop: bool = False,
        speed: Optional[float] = None,
        distance: Optional[float] = None
    ):
        self.direction = direction
        self.stop = stop
        self.speed = speed
        self.distance = distance

    def to_str(self) -> str:
        data = {
            "direction": self.direction,
            "stop": self.stop,
            "speed": self.speed,
            "distance": self.distance
        }
        return json.dumps(data)

    @classmethod
    def from_raw(cls, payload: dict):
        t = payload.get("type")
        data = payload.get("data")
        if data is None:
            raise ValueError("No data")

        if t != "message":
            raise ValueError("Not a message payload")

        data = json.loads(data)
        return cls(**data)
        

class InputHandler:
    INTERVAL = 0.15
    CHANNEL = "remotecommands"

    def __init__(self):
        host, port, password = read_redis_config()
        self._redis = redis.Redis(
            host=host,
            port=port,
            password=password
        )
        self.pubsub = self._redis.pubsub()
        self.pubsub.subscribe(self.CHANNEL)

        self.message_queue: Queue[Message] = Queue(maxsize=-1)

        self._previous_slider_value = None
        self._listen_callbacks = []

        # start threads
        Thread(target=self.handle_listen, daemon=True).start()
        Clock.schedule_interval(self.handle_publish, 0.01)

    def handle_publish(self, _):
        try:
            item = self.message_queue.get_nowait()
            print("item found, sending")
            try:
                self._redis.publish(self.CHANNEL, item.to_str())
            except redis.exceptions.ConnectionError:
                host, port, password = read_redis_config()
                self._redis = redis.Redis(host=host, port=port, password=password)
        except Empty:
            pass

    def queue_message(self, message: Message):
        self.message_queue.put_nowait(message)
            
    def handle_listen(self):
        print("listening")
        for message in self.pubsub.listen():
            print(message)
            try:
                message = Message.from_raw(message)
            except Exception as exc:
                print(exc)
                continue

            for listener in self._listen_callbacks:
                try:
                    listener(message)
                except Exception as exc:
                    print(exc)
                    pass
            
    def add_listen_callback(self, callback: Callable[[Message], None]):
        self._listen_callbacks.append(callback)

    def force_send(self, data: Message):
        """
        Clears the message queue completely, and placing
        the data at the first slot, essentially forcing a message to be sent
        quickly
        """
        inner = self.message_queue.queue
        with self.message_queue.mutex: # mutex might be undocumented and unsafe?
            inner.clear()

        self.queue_message(data)

    def handle_speed_slider(self, slider: Slider):
        normalized = slider.value_normalized
        if normalized != self._previous_slider_value:
            print("New slider value", normalized)
            
            message = Message(speed=normalized)
            self.queue_message(message)

        self._previous_slider_value = normalized
        