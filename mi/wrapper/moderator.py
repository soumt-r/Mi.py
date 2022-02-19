from typing import Optional

from mi.framework.http import HTTPSession, Route


class AdminModeratorManager:
    def __init__(self, user_id: Optional[str] = None):
        self.__user_id: Optional[str] = user_id

    async def add(self, user_id: Optional[str] = None) -> bool:
        user_id = user_id or self.__user_id
        data = {'userId': user_id}
        res = await HTTPSession.request(Route('POST', '/api/moderators/add'), json=data, auth=True, lower=True)
        return bool(res)

    async def remove(self, user_id: Optional[str] = None) -> bool:
        user_id = user_id or self.__user_id
        data = {'userId': user_id}
        res = await HTTPSession.request(Route('POST', '/api/moderators/remove'), json=data, auth=True, lower=True)
        return bool(res)
