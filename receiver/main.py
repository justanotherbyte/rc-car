import asyncio
import json
from typing import (
    List,
    Optional,
    TypedDict
)

import aioredis


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

    async def receive_messages(self):
        async for message in self.pubsub.listen():
            type_ = message.get("type")
            if type_ != "message":
                continue

            data = message.get("data")
            if data is None:
                continue

            data = json.loads(data)
            await self.handle_message(data)

    async def handle_message(self, message: Message):
        print(message)

    async def start(self):
        await self.pubsub.subscribe("remotecommands")
        print("Subscribed to channel...")

        print("Receiving messages...")
        await self.receive_messages()

async def launch():
    receiver = AsyncReceiver()
    await receiver.start()

asyncio.run(launch())