# Copyright 2022-2024 XProbe Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import queue
from collections import defaultdict
from enum import Enum
from typing import Dict, List, TypedDict

import xoscar as xo

MAX_EVENT_COUNT_PER_MODEL = 100


class EventType(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3


class Event(TypedDict):
    event_type: EventType
    event_ts: int
    event_content: str


class FIFOQueue(asyncio.Queue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize)

    async def put(self, item):
        if self.full():
            await self.get()  # 丢弃最旧的项目
        await super().put(item)


class EventCollectorActor(xo.StatelessActor):
    def __init__(self):
        super().__init__()
        self._model_uid_to_events: Dict[str, asyncio.Queue] = defaultdict(  # type: ignore
            lambda: FIFOQueue(maxsize=MAX_EVENT_COUNT_PER_MODEL)
        )

    @classmethod
    def uid(cls) -> str:
        return "event_collector"

    def get_model_events(self, model_uid: str) -> List[Dict]:
        event_queue = self._model_uid_to_events.get(model_uid)
        if event_queue is None:
            return []
        else:
            return [dict(e, event_type=e["event_type"].name) for e in event_queue._queue]

    async def report_event(self, model_uid: str, event: Event):
        await self._model_uid_to_events[model_uid].put(event)
