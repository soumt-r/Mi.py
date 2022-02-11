from __future__ import annotations

from typing import List, Optional

from mi.exception import InvalidParameters
from mi.framework.http import HTTPSession, Route
from mi.framework.models.drive import File, Folder
from mi.utils import remove_dict_empty
from mi.wrapper.models.drive import RawFile, RawFolder

__all__ = ['FolderManager', 'FileManager', 'DriveManager']


class FileManager:
    def __init__(self, file_id: Optional[str] = None):
        self.__file_id = file_id

    async def show_file(self, file_id: Optional[str], url: Optional[str]) -> File:
        """
        ファイルの情報を取得します。

        Parameters
        ----------
        file_id : Optional[str], default=None
            ファイルのID
        url : Optional[str], default=None
            ファイルのURL

        Returns
        -------
        File
            ファイルの情報
        """

        data = remove_dict_empty({"fileId": file_id, "url": url})
        res = await HTTPSession.request(Route('POST', '/api/admin/drive/show-file'), json=data, auth=True, lower=True)
        return File(RawFile(res))

    async def remove_file(self, file_id: Optional[str] = None) -> bool:
        """
        指定したIDのファイルを削除します

        Parameters
        ----------
        file_id : Optional[str], default=None
            削除するファイルのID

        Returns
        -------
        bool
            削除に成功したかどうか
        """

        file_id = file_id or self.__file_id
        return bool(await HTTPSession.request(Route('POST', '/api/drive/files/delete'), json={'fileId': file_id}, auth=True))

    @staticmethod
    async def get_files(
            limit: int = 10,
            since_id: Optional[str] = None,
            until_id: Optional[str] = None,
            folder_id: Optional[str] = None,
            file_type: Optional[str] = None
    ) -> List[File]:
        """
        ファイルを取得します

        Parameters
        ----------
        limit : int, default=10
            取得する上限
        since_id : Optional[str], default=None
            指定すると、そのIDを起点としてより新しいファイルを取得します
        until_id : Optional[str], default=None
            指定すると、そのIDを起点としてより古いファイルを取得します
        folder_id : Optional[str], default=None
            指定すると、そのフォルダーを起点としてファイルを取得します
        file_type : Optional[str], default=None
            取得したいファイルの拡張子
        """
        if limit > 100:
            raise InvalidParameters('limit must be less than 100')

        data = {'limit': limit, 'sinceId': since_id, 'untilId': until_id, 'folderId': folder_id, 'Type': file_type}
        res = await HTTPSession.request(Route('POST', '/api/drive/files'), json=data, auth=True, lower=True)
        return [File(RawFile(i)) for i in res]


class FolderManager:
    def __init__(self, folder_id: Optional[str] = None):
        self.__folder_id = folder_id

    async def create(self, name: str, parent_id: Optional[str] = None) -> bool:
        """
        フォルダーを作成します

        Parameters
        ----------
        name : str, default=None
            フォルダーの名前
        parent_id : Optional[str], default=None
            親フォルダーのID

        Returns
        -------
        bool
            作成に成功したか否か
        """

        parent_id = parent_id or self.__folder_id

        data = {'name': name, 'parent_id': parent_id}
        return bool(await HTTPSession.request(Route('POST', '/api/drive/folders/create'), json=data, lower=True, auth=True))

    async def delete(self, folder_id: Optional[str] = None) -> bool:
        """
        Parameters
        ----------
        folder_id : Optional[str] = None
            削除するノートのID

        Returns
        -------
        bool
            削除に成功したか否か
        """

        folder_id = folder_id or self.__folder_id
        data = {'folderId': folder_id}
        return bool(await HTTPSession.request(Route('POST', '/api/drive/folders/delete'), json=data, lower=True, auth=True))

    async def get_files(self, limit: int = 10, since_id: Optional[str] = None, until_id: Optional[str] = None,
                        folder_id: Optional[str] = None, file_type: Optional[str] = None) -> List[File]:
        """
        ファイルを取得します

        Parameters
        ----------
        limit : int, default=10
            取得する上限
        since_id : Optional[str], default=None
            指定すると、そのIDを起点としてより新しいファイルを取得します
        until_id : Optional[str], default=None
            指定すると、そのIDを起点としてより古いファイルを取得します
        folder_id : Optional[str], default=None
            指定すると、そのフォルダーを起点としてファイルを取得します
        file_type : Optional[str], default=None
            取得したいファイルの拡張子
        """
        if limit > 100:
            raise InvalidParameters('limit must be less than 100')

        folder_id = folder_id or self.__folder_id
        data = {'limit': limit, 'sinceId': since_id, 'untilId': until_id, 'folderId': folder_id, 'Type': file_type}
        res = await HTTPSession.request(Route('POST', '/api/drive/files'), json=data, auth=True, lower=True)
        return [File(RawFile(i)) for i in res]


class DriveManager:
    def __init__(self):
        pass

    async def get_folders(self, limit: int = 100, since_id: Optional[str] = None, until_id: Optional[str] = None,
                          folder_id: Optional[str] = None) -> List[Folder]:
        """
        フォルダーの一覧を取得します

        Parameters
        ----------
        limit : int, default=10
            取得する上限
        since_id : Optional[str], default=None
            指定すると、その投稿を投稿を起点としてより新しい投稿を取得します
        until_id : Optional[str], default=None
            指定すると、その投稿を投稿を起点としてより古い投稿を取得します
        folder_id : Optional[str], default=None
            指定すると、そのフォルダーを起点としてフォルダーを取得します
        """

        data = {
            'limit': limit,
            'sinceId': since_id,
            'untilId': until_id,
            'folderId': folder_id
        }
        data = await HTTPSession.request(Route('POST', '/api/drive/folders'), json=data, lower=True, auth=True)
        return [Folder(RawFolder(i)) for i in data]
