from __future__ import annotations
import asyncio

import json
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, TypeVar

import aiohttp
from mi import config
from mi.exception import ClientConnectorError, WebSocketRecconect
from mi.utils import str_lower

if TYPE_CHECKING:
    from .client import Client

__all__ = ('MisskeyWebSocket', 'MisskeyClientWebSocketResponse')


class MisskeyClientWebSocketResponse(aiohttp.ClientWebSocketResponse):
    async def close(self, *, code: int = 4000, message: bytes = b'') -> bool:
        return await super().close(code=code, message=message)


MS = TypeVar('MS', bound='MisskeyClientWebSocketResponse')


class MisskeyWebSocket:
    def __init__(self, socket: MS, client: Client):
        self.socket: MS = socket
        self._dispatch = lambda *args: None
        self._connection = None
        self.client = client
        self._misskey_parsers: Optional[Dict[str, Callable[..., Any]]] = None

    @classmethod
    async def from_client(cls, client: Client, *, timeout: int = 60, event_name: str = 'ready'):
        try:
            socket = await client.http.ws_connect(f'{client.url}?i={config.i.token}')
            ws = cls(socket, client)
            ws._dispatch = client.dispatch
            ws._connection = client._connection
            ws._misskey_parsers = client._connection.parsers
            client.dispatch(event_name, socket)
            return ws
        except ClientConnectorError:
            while True:
                await asyncio.sleep(3)
                return await cls.from_client(client, timeout=timeout, event_name=event_name)
                
        # await ws.poll_event(timeout=timeout)

    async def received_message(self, msg, /):
        if isinstance(msg, bytes):
            msg = msg.decode()

        self._misskey_parsers[str_lower(msg['type']).upper()](msg)

    async def poll_event(self, *, timeout: int = 60):

        msg = await self.socket.receive(timeout=timeout)

        if msg is aiohttp.http.WS_CLOSED_MESSAGE:
            await asyncio.sleep(3)
            raise WebSocketRecconect()

        elif msg.type is aiohttp.WSMsgType.TEXT:
            await self.received_message(json.loads(msg.data))
