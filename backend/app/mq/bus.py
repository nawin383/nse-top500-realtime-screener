"""Message bus with in-memory + optional RabbitMQ/Kafka."""
from __future__ import annotations
import asyncio, os, json, logging
from collections import deque, defaultdict
from typing import Callable, Dict, List

logger=logging.getLogger(__name__)

class InMemoryBus:
    def __init__(self, max_burst: int=1000):
        self.subs: Dict[str, List[Callable]] = defaultdict(list)
        self.queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_burst))
        self.retry=3
        self._burst_buffer: Dict[str, deque]= defaultdict(lambda: deque(maxlen=max_burst))

    async def publish(self, topic: str, payload: dict):
        # try external first
        ext=os.getenv("MQ_URL") or os.getenv("RABBITMQ_URL") or os.getenv("KAFKA_BROKERS")
        if ext: 
            try: await self._publish_external(topic,payload)
            except Exception as e: logger.debug(f"ext publish failed {e}")
        # in-memory fanout
        self.queues[topic].append(payload)
        for cb in list(self.subs[topic]):
            for attempt in range(self.retry):
                try:
                    if asyncio.iscoroutinefunction(cb): await cb(payload)
                    else: cb(payload)
                    break
                except Exception as e:
                    if attempt==self.retry-1: 
                        self._burst_buffer[topic].append(payload)
                        logger.warning(f"bus cb failed {e}")

    async def subscribe(self, topic: str, callback: Callable):
        self.subs[topic].append(callback)
        # drain buffered
        while self._burst_buffer[topic]:
            item=self._burst_buffer[topic].popleft()
            try:
                if asyncio.iscoroutinefunction(callback): await callback(item)
                else: callback(item)
            except: pass

    async def _publish_external(self, topic, payload):
        url=os.getenv("RABBITMQ_URL") or os.getenv("MQ_URL")
        brokers=os.getenv("KAFKA_BROKERS")
        if brokers:
            try:
                from aiokafka import AIOKafkaProducer  # type: ignore
                prod=AIOKafkaProducer(bootstrap_servers=brokers)
                await prod.start()
                await prod.send_and_wait(topic, json.dumps(payload).encode())
                await prod.stop()
                return
            except: pass
        if url:
            try:
                import aio_pika  # type: ignore
                conn=await aio_pika.connect_robust(url)
                ch=await conn.channel()
                await ch.default_exchange.publish(aio_pika.Message(json.dumps(payload).encode()), routing_key=topic)
                await conn.close()
            except: pass

    def pending(self, topic:str)->int: return len(self.queues[topic])
    def buffered(self, topic:str)->int: return len(self._burst_buffer[topic])

bus = InMemoryBus()
publish = bus.publish
subscribe = bus.subscribe
