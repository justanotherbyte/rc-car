import asyncio
import math
import json
from typing import (
    List,
    Optional,
    TypedDict
)

import aioredis
from trilobot import Trilobot


tbot = Trilobot()
tbot.fill_underlighting((0, 0, 255))


def joy_to_diff_drive(joy_x, joy_y):
    left = joy_x * math.sqrt(2.0)/2.0 + joy_y * math.sqrt(2.0)/2.0
    right = -joy_x * math.sqrt(2.0)/2.0 + joy_y * math.sqrt(2.0)/2.0

    return (left, right)

class Message(TypedDict):
    direction: Optional[List[float]]
    stop: bool
    speed: Optional[float]
    distance: Optional[float]

class AsyncReceiver:
    def __init__(self):
        with open("redis.json") as f:
            params = json.load(f)

        self.redis = aioredis.Redis(**params)
        self.pubsub = self.redis.pubsub()

        self.previous_speed = 0.0
        self.message_queue = asyncio.Queue(-1)

    async def receive_messages(self):
        async for message in self.pubsub.listen():
            print(message)
            type_ = message.get("type")
            if type_ != "message":
                continue

            data = message.get("data")
            if data is None:
                continue

            data = json.loads(data)
            await self.handle_message(data)

    async def handle_message(self, message: Message):
        direction = message.get("direction")
        speed = message.get("speed")

        if direction and list(direction) == [0.0, 0.0]:
            tbot.stop()
            return


        if speed and speed != self.previous_speed:
            self.previous_speed = speed

        if direction:
            lx = direction[0]
            ly = direction[1]

            adjust_speed = self.previous_speed

            if ly < 0:
                lx = 0 - lx
                adjust_speed = -adjust_speed
            
            x_speed, y_speed = joy_to_diff_drive(lx, ly)
            print(x_speed, y_speed)
            tbot.set_left_speed(x_speed + adjust_speed)
            tbot.set_right_speed(y_speed + adjust_speed)

        stop = message.get("stop")

        if stop is True:
            tbot.stop()

    def distance_reactions(self):
        while True:
            distance = tbot.read_distance()

            if distance <= 30:
                tbot.fill_underlighting((255, 0, 0))
            else:
                tbot.fill_underlighting((0, 255, 0))

            data = {"distance": distance}
            payload = json.dumps(data)
            self.message_queue.put_nowait(payload)

    async def send_messages(self):
        while True:
            msg = await self.message_queue.get()
            await self.redis.publish("remotecommands", msg)
            await asyncio.sleep(2.5)

    async def start(self):
        await self.pubsub.subscribe("remotecommands")
        print("Subscribed to channel...")

        print("Starting distance task...")

        coro = asyncio.to_thread(self.distance_reactions)
        asyncio.create_task(coro)

        print("Starting send task...")
        asyncio.create_task(self.send_messages())

        print("Receiving messages...")
        await self.receive_messages()

async def launch():
    receiver = AsyncReceiver()
    await receiver.start()

asyncio.run(launch())