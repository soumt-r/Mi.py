from __future__ import annotations

from typing import TYPE_CHECKING, Union

import mi.framework.manager
from mi.framework.models.user import User
from mi.wrapper.models.drive import RawFile, RawFolder, RawProperties
from mi.wrapper.models.user import RawUser

if TYPE_CHECKING:
    from mi.wrapper.drive import FolderManager

__all__ = ['Properties', 'File', 'File', 'Folder']


class Properties:
    def __init__(self, raw_data: RawProperties) -> None:
        self.__raw_data: RawProperties = raw_data

    @property
    def width(self) -> int:
        return self.__raw_data.width

    @property
    def height(self) -> int:
        return self.__raw_data.height

    @property
    def avg_color(self) -> Union[float, None]:
        return self.__raw_data.avg_color


class Folder:
    def __init__(self, raw_data: RawFolder):
        self.__raw_data = raw_data

    @property
    def id(self):
        return self.__raw_data.id

    @property
    def created_at(self):
        return self.__raw_data.created_at

    @property
    def name(self):
        return self.__raw_data.name

    @property
    def folders_count(self):
        return self.__raw_data.folders_count

    @property
    def parent_id(self):
        return self.__raw_data.parent_id

    @property
    def parent(self):
        return self.__raw_data.parent

    @property
    def action(self) -> FolderManager:
        return mi.framework.manager.ClientActions().drive.get_folder_instance(self.id).action


class File:
    def __init__(self, raw_data: RawFile):
        self.__raw_data = raw_data

    @property
    def id(self):
        return self.__raw_data.id

    @property
    def created_at(self):
        return self.__raw_data.created_at

    @property
    def name(self):
        return self.__raw_data.name

    @property
    def type(self):
        return self.__raw_data.type

    @property
    def md5(self):
        return self.__raw_data.md5

    @property
    def size(self):
        return self.__raw_data.size

    @property
    def is_sensitive(self):
        return self.__raw_data.is_sensitive

    @property
    def blurhash(self):
        return self.__raw_data.blurhash

    @property
    def properties(self):
        return self.__raw_data.properties

    @property
    def url(self):
        return self.__raw_data.url

    @property
    def thumbnail_url(self):
        return self.__raw_data.thumbnail_url

    @property
    def comment(self):
        return self.__raw_data.comment

    @property
    def folder_id(self):
        return self.__raw_data.folder_id

    @property
    def folder(self):
        return self.__raw_data.folder

    @property
    def user_id(self):
        return self.__raw_data.user_id

    @property
    def user(self):
        return User(RawUser(self.__raw_data.user))
