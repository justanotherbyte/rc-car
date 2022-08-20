import asyncio
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

        def lowest(direction: float):
            return min([1, direction + self.previous_speed])


        if direction:
            lx = direction[0]
            ly = direction[1]
            ly = 0 - ly

            tbot.set_left_speed(ly + lx)
            tbot.set_right_speed(ly - lx)

        stop = message.get("stop")

        if stop is True:
            tbot.stop()

    async def start(self):
        await self.pubsub.subscribe("remotecommands")
        print("Subscribed to channel...")

        print("Receiving messages...")
        await self.receive_messages()

async def launch():
    receiver = AsyncReceiver()
    await receiver.start()

asyncio.run(launch())