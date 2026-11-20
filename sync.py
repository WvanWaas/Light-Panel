"""Authoritative HA state cache, shared by REST refreshes and the event stream."""
import asyncio
from datetime import datetime, timezone

class StateCache:
    def __init__(self, broadcast):
        self.states = {}
        self.versions = {}
        self.revision = 0
        self.lock = asyncio.Lock()
        self.refresh_lock = asyncio.Lock()
        self.broadcast = broadcast
        self.pending = {}
        self.status = {'mode': 'offline', 'last_sync': None}

    def payload(self):
        return {'type': 'states', 'states': dict(self.states),
                'revision': self.revision, 'connection': dict(self.status)}

    async def connection(self, mode):
        async with self.lock:
            self.status['mode'] = mode
            await self.broadcast({'type': 'connection', **self.status})

    async def snapshot(self, values, before):
        async with self.lock:
            fresh = {v['entity_id']: v for v in values}
            # A newer event (including deletion) wins over an in-flight HTTP snapshot.
            for entity in set(self.states) | set(fresh):
                if self.versions.get(entity, 0) != before.get(entity, 0):
                    continue
                if entity in fresh:
                    self.states[entity] = fresh[entity]
                else:
                    self.states.pop(entity, None)
            self.revision += 1
            self.pending.clear()
            self.status['last_sync'] = datetime.now(timezone.utc).isoformat()
            await self.broadcast(self.payload())

    async def event(self, entity, value):
        async with self.lock:
            self.revision += 1
            self.versions[entity] = self.revision
            if value is None:
                self.states.pop(entity, None)
            else:
                self.states[entity] = value
            self.pending[entity] = value
            self.status['last_sync'] = datetime.now(timezone.utc).isoformat()

    async def flush(self):
        async with self.lock:
            if not self.pending:return
            changes=dict(self.pending);self.pending.clear()
            await self.broadcast({'type':'state_delta','changes':changes,
                                  'revision':self.revision,'connection':dict(self.status)})

    async def stream(self):
        while True:
            await asyncio.sleep(.25)
            await self.flush()
