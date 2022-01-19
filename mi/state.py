from __future__ import annotations

import asyncio
import inspect
from typing import Any, AsyncIterator, Callable, Dict, Generator, List, Optional, TYPE_CHECKING, Union

from aiocache import cached
from aiocache.factory import Cache

from mi import Instance, InstanceMeta, User
from mi.api import FavoriteManager
from mi.api.drive import DriveManager, FileManager, FolderManager
from mi.api.follow import FollowManager, FollowRequestManager
from mi.api.reaction import ReactionManager
from mi.chat import Chat
from mi.drive import File
from mi.emoji import Emoji
from mi.exception import ContentRequired, InvalidParameters, NotExistRequiredParameters
from mi.http import Route
from mi.iterators import InstanceIterator
from mi.models.drive import RawFile
from mi.models.note import RawNote
from mi.models.user import RawUser
from mi.note import Note, Poll, Reaction
from mi.user import FollowRequest, Followee
from mi.utils import check_multi_arg, get_cache_key, get_module_logger, key_builder, remove_dict_empty, str_lower, \
    upper_to_lower

if TYPE_CHECKING:
    from mi import HTTPClient, Client
    from mi.types import (Note as NotePayload, Chat as ChatPayload)


class NoteActions:
    def __init__(self, state: 'ConnectionState', http: HTTPClient, loop: asyncio.AbstractEventLoop,
                 note_id: Optional[str] = None):
        self.__state = state
        self.__http = http
        self.__loop = loop
        self.favorite = FavoriteManager(state, http, loop, note_id=note_id)
        self.reaction = ReactionManager(state, http, loop, note_id=note_id)

    async def add_clips(self, clip_id: str, note_id: str) -> bool:
        data = {'noteId': note_id, 'clipId': clip_id}
        return bool(await self.__http.request(Route('POST', '/api/clips/add-note'), json=data, auth=True))

    async def add_reaction_to_note(self, note_id: str, reaction: str) -> bool:
        data = {'noteId': note_id, 'reaction': reaction}
        return bool(await self.__http.request(Route('POST', '/api/reactions/create'), json=data, auth=True))

    async def send(self,
                   content: Optional[str] = None,
                   visibility: str = "public",
                   visible_user_ids: Optional[List[str]] = None,
                   cw: Optional[str] = None,
                   local_only: bool = False,
                   extract_mentions: bool = True,
                   extract_hashtags: bool = True,
                   extract_emojis: bool = True,
                   reply_id: Optional[str] = None,
                   renote_id: Optional[str] = None,
                   channel_id: Optional[str] = None,
                   file_ids=None,
                   poll: Optional[Poll] = None
                   ) -> Note:
        """
        ノートを投稿します。

        Parameters
        ----------
        content : Optional[str], default=None
            投稿する内容
        visibility : str, optional
            公開範囲, by default "public"
        visible_user_ids : Optional[List[str]], optional
            公開するユーザー, by default None
        cw : Optional[str], optional
            閲覧注意の文字, by default None
        local_only : bool, optional
            ローカルにのみ表示するか, by default False
        extract_mentions : bool, optional
            メンションを展開するか, by default False
        extract_hashtags : bool, optional
            ハッシュタグを展開するか, by default False
        extract_emojis : bool, optional
            絵文字を展開するか, by default False
        reply_id : Optional[str], optional
            リプライ先のid, by default None
        renote_id : Optional[str], optional
            リノート先のid, by default None
        channel_id : Optional[str], optional
            チャンネルid, by default None
        file_ids : [type], optional
            添付するファイルのid, by default None
        poll : Optional[Poll], optional
            アンケート, by default None

        Returns
        -------
        Note
            投稿したノート

        Raises
        ------
        ContentRequired
            [description]
        """

        if file_ids is None:
            file_ids = []
        field = {
            "visibility": visibility,
            "visibleUserIds": visible_user_ids,
            "text": content,
            "cw": cw,
            "localOnly": local_only,
            "noExtractMentions": extract_mentions,
            "noExtractHashtags": extract_hashtags,
            "noExtractEmojis": extract_emojis,
            "replyId": reply_id,
            "renoteId": renote_id,
            "channelId": channel_id
        }
        if not check_multi_arg(content, file_ids, renote_id, poll):
            raise ContentRequired("ノートの送信にはcontent, file_ids, renote_id またはpollのいずれか1つが無くてはいけません")

        if poll and type(Poll):
            poll_data = remove_dict_empty({
                'choices': poll.choices,
                'multiple': poll.multiple,
                'expiresAt': poll.expires_at,
                'expiredAfter': poll.expired_after
            })
            field["poll"] = poll_data

        if file_ids:
            field["fileIds"] = file_ids
        field = remove_dict_empty(field)
        res = await self.__http.request(Route('POST', '/api/notes/create'), json=field, auth=True, lower=True)
        return Note(RawNote(res["created_note"]), state=self.__state)

    async def delete(self, note_id: Optional[str]=None):
        data = {"noteId": note_id}
        res = await self.__http.request(Route('POST', '/api/notes/delete'), json=data, auth=True)
        return bool(res)

    async def create_renote(self, note_id: str) -> Note:
        return await self.send(renote_id=note_id)

    async def create_quote(self, note_id: str,
                           content: Optional[str] = None,
                           visibility: str = 'public',
                           visible_user_ids: Optional[List[str]] = None,
                           cw: Optional[str] = None,
                           local_only: bool = False,
                           extract_mentions: bool = True,
                           extract_hashtags: bool = True,
                           extract_emojis: bool = True,
                           file_ids=None,
                           poll: Optional[Poll] = None) -> Note:
        return await self.send(content=content, visibility=visibility, visible_user_ids=visible_user_ids, cw=cw,
                               local_only=local_only, extract_mentions=extract_mentions,
                               extract_hashtags=extract_hashtags,
                               extract_emojis=extract_emojis, renote_id=note_id, file_ids=file_ids, poll=poll)

    async def get_note(self, note_id) -> Note:
        res = await self.__http.request(Route('POST', '/api/notes/show'), json={"noteId": note_id}, auth=True, lower=True)
        return Note(RawNote(res), state=self.__state)

    async def get_replies(self, note_id: str, since_id: Optional[str] = None, until_id: Optional[str] = None,
                          limit: int = 10, ) -> List[Note]:
        res = await self.__http.request(Route('POST', '/api/notes/replies'),
                                      json={"noteId": note_id, "sinceId": since_id, "untilId": until_id, "limit": limit},
                                      auth=True, lower=True)
        return [Note(RawNote(i), state=self.__state) for i in res]

    def get_reaction(self, note_id: str, reaction: str):
        return ReactionManager(self.__state, self.__http, self.__loop, note_id=note_id)


class UserActions:
    def __init__(
            self, client: 'ConnectionState',
            http: HTTPClient,
            loop: asyncio.AbstractEventLoop,
            *,
            user_id: Optional[str] = None
    ):
        self.client = client
        self.http = http
        self.loop = loop
        self.follow = FollowManager(client, http, loop, user_id=user_id)
        self.follow_request = FollowRequestManager(client, http, loop, user_id=user_id)

    def get_follow(self, user_id: str) -> FollowManager:
        return FollowManager(self.client, self.http, self.loop, user_id=user_id)

    def get_follow_request(self, user_id: str) -> FollowRequestManager:
        return FollowRequestManager(self.client, self.http, self.loop, user_id=user_id)


class FolderActions:
    def __init__(
            self, client: 'ConnectionState',
            http: HTTPClient,
            loop: asyncio.AbstractEventLoop,
            *,
            folder_id: Optional[str] = None
    ):
        self.client = client
        self.http = http
        self.loop = loop
        self.action: FolderManager = FolderManager(self.client, self.http, self.loop, folder_id=folder_id)


class DriveActions:
    def __init__(
            self, state: 'ConnectionState',
            http: HTTPClient,
            loop: asyncio.AbstractEventLoop,
    ):
        self.state = state
        self.http = http
        self.loop = loop
        self.action: DriveManager = DriveManager(self.state, self.http, self.loop)
        self.folder: FolderActions = FolderActions(self.state, self.http, self.loop)
        self.files: FileManager = FileManager(state, http, loop)

    def get_folder_instance(self, folder_id: str) -> FolderActions:
        return FolderActions(self.state, self.http, self.loop, folder_id=folder_id)


class ClientActions:
    def __init__(self, client: 'ConnectionState', http: HTTPClient, loop: asyncio.AbstractEventLoop):
        self.__client = client
        self.__http = http
        self.__loop = loop
        self.note = NoteActions(client, http, loop)
        self.user = UserActions(client, http, loop)
        self.drive = DriveActions(client, http, loop)

    def get_user_instance(self, user_id: Optional[str]) -> UserActions:
        return UserActions(self.__client, self.__http, self.__loop, user_id=user_id)

    def get_note_instance(self, note_id: str) -> NoteActions:
        return NoteActions(self.__client, self.__http, self.__loop, note_id=note_id)


class ConnectionState(ClientActions):
    def __init__(self, dispatch: Callable[..., Any], http: HTTPClient, loop: asyncio.AbstractEventLoop, client: Client):
        super().__init__(self, http, loop)
        self.client: Client = client
        self.dispatch = dispatch
        self.http: HTTPClient = http
        self.logger = get_module_logger(__name__)
        self.loop: asyncio.AbstractEventLoop = loop
        self.parsers = parsers = {}
        for attr, func in inspect.getmembers(self):
            if attr.startswith('parse'):
                parsers[attr[6:].upper()] = func

    def get_client_actions(self) -> ClientActions:
        return ClientActions(self, self.http, self.loop)

    def parse_emoji_added(self, message: Dict[str, Any]):
        self.dispatch('emoji_add', Emoji(message['body']['emoji'], state=self))

    def parse_channel(self, message: Dict[str, Any]) -> None:
        """parse_channel is a function to parse channel event

        チャンネルタイプのデータを解析後適切なパーサーに移動させます

        Parameters
        ----------
        message : Dict[str, Any]
            Received message
        """
        base_msg = upper_to_lower(message['body'])
        channel_type = str_lower(base_msg.get('type'))
        self.logger.debug(f'ChannelType: {channel_type}')
        self.logger.debug(f'recv event type: {channel_type}')
        getattr(self, f'parse_{channel_type}')(base_msg['body'])

    def parse_renote(self, message: Dict[str, Any]):
        pass

    def parse_unfollow(self, message: Dict[str, Any]):
        """
        フォローを解除した際のイベントを解析する関数
        """

    def parse_signin(self, message: Dict[str, Any]):
        """
        ログインが発生した際のイベント
        """

    def parse_receive_follow_request(self, message: Dict[str, Any]):
        """
        フォローリクエストを受け取った際のイベントを解析する関数
        """

        self.dispatch('follow_request', FollowRequest(message, state=self))

    def parse_me_updated(self, message: Dict[str, Any]):
        pass

    def parse_read_all_announcements(self, message: Dict[str, Any]) -> None:
        pass  # TODO: 実装

    def parse_reply(self, message: NotePayload) -> None:
        """
        リプライ
        """
        self.dispatch('message', Note(RawNote(message), state=self))

    def parse_follow(self, message: Dict[str, Any]) -> None:
        """
        ユーザーをフォローした際のイベントを解析する関数
        """

        self.dispatch('user_follow', User(RawUser(message), state=self))

    def parse_followed(self, message: Dict[str, Any]) -> None:
        """
        フォローイベントを解析する関数
        """

        self.dispatch('follow', User(RawUser(message), state=self))

    def parse_mention(self, message: Dict[str, Any]) -> None:
        """
        メンションイベントを解析する関数
        """

        self.dispatch('mention', Note(RawNote(message), state=self))

    def parse_drive_file_created(self, message: Dict[str, Any]) -> None:
        pass  # TODO: 実装

    def parse_read_all_unread_mentions(self, message: Dict[str, Any]) -> None:
        pass  # TODO:実装

    def parse_read_all_unread_specified_notes(self, message: Dict[str, Any]) -> None:
        pass  # TODO:実装

    def parse_read_all_channels(self, message: Dict[str, Any]) -> None:
        pass  # TODO:実装

    def parse_read_all_notifications(self, message: Dict[str, Any]) -> None:
        pass  # TODO:実装

    def parse_unread_mention(self, message: Dict[str, Any]) -> None:
        pass

    def parse_unread_specified_note(self, message: Dict[str, Any]) -> None:
        pass

    def parse_read_all_messaging_messages(self, message: Dict[str, Any]) -> None:
        pass

    def parse_messaging_message(self, message: ChatPayload) -> None:
        """
        チャットが来た際のデータを処理する関数
        """
        self.dispatch('message', Chat(message, state=self))

    def parse_unread_messaging_message(self, message: Dict[str, Any]) -> None:
        """
        チャットが既読になっていない場合のデータを処理する関数
        """
        self.dispatch('message', Chat(message, state=self))

    def parse_notification(self, message: Dict[str, Any]) -> None:
        """
        通知イベントを解析する関数

        Parameters
        ----------
        message: Dict[str, Any]
            Received message
        """

        accept_type = ['reaction']
        notification_type = str_lower(message['type'])
        if notification_type in accept_type:
            getattr(self, f'parse_{notification_type}')(message)

    def parse_follow_request_accepted(self, message: Dict[str, Any]) -> None:
        pass

    def parse_poll_vote(self, message: Dict[str, Any]) -> None:
        pass  # TODO: 実装

    def parse_unread_notification(self, message: Dict[str, Any]) -> None:
        """
        未読の通知を解析する関数

        Parameters
        ----------
        message : Dict[str, Any]
            Received message
        """
        # notification_type = str_lower(message['type'])
        # getattr(self, f'parse_{notification_type}')(message)

    def parse_reaction(self, message: Dict[str, Any]) -> None:
        """
        リアクションに関する情報を解析する関数
        """
        self.dispatch('reaction', Reaction(message, state=self))

    def parse_note(self, message: NotePayload) -> None:
        """
        ノートイベントを解析する関数
        """
        note = Note(RawNote(message), state=self)
        # Router(self.http.ws).capture_message(note.id) TODO: capture message
        self.client._on_message(note)

    async def get_i(self) -> User:
        res = await self.http.request(Route('POST', '/api/i'), auth=True, lower=True)
        return User(RawUser(res), state=self)

    def get_users(self,
                  limit: int = 10,
                  *,
                  offset: int = 0,
                  sort: Optional[str] = None,
                  state: str = 'all',
                  origin: str = 'local',
                  username: Optional[str] = None,
                  hostname: Optional[str] = None,
                  get_all: bool = False) -> AsyncIterator[User]:
        return InstanceIterator(self).get_users(limit=limit, offset=offset, sort=sort, state=state, origin=origin,
                                                username=username, hostname=hostname, get_all=get_all)

    @cached(ttl=10, namespace='get_user', key_builder=key_builder)
    async def get_user(self, user_id: Optional[str] = None, username: Optional[str] = None,
                       host: Optional[str] = None) -> User:
        """
        ユーザーのプロフィールを取得します。一度のみサーバーにアクセスしキャッシュをその後は使います。
        fetch_userを使った場合はキャッシュが廃棄され再度サーバーにアクセスします。

        Parameters
        ----------
        user_id : str
            取得したいユーザーのユーザーID
        username : str
            取得したいユーザーのユーザー名
        host : str, default=None
            取得したいユーザーがいるインスタンスのhost

        Returns
        -------
        dict
            ユーザー情報
        """

        field = remove_dict_empty({"userId": user_id, "username": username, "host": host})
        data = await self.http.request(Route('POST', '/api/users/show'), json=field, auth=True, lower=True)
        return User(RawUser(data), state=self)

    async def post_chat(self, content: str, *, user_id: str = None, group_id: str = None, file_id=None) -> Chat:
        """
        チャットを送信します。

        Parameters
        ----------
        content : str
            送信する内容
        user_id : str, optional
            ユーザーid, default=None
        group_id : str, optional
            グループid, default=None
        file_id : str, optional
            添付するファイルid, efault=None

        Returns
        -------
        Chat
            チャットの内容
        """
        args = remove_dict_empty({'userId': user_id, 'groupId': group_id, 'text': content, 'fileId': file_id})
        data = await self.http.request(Route('POST', '/api/messaging/messages/create'), json=args, auth=True, lower=True)
        return Chat(data, state=self)

    async def delete_chat(self, message_id: str) -> bool:
        """
        指定したidのメッセージを削除します。

        Parameters
        ----------
        message_id : str
            メッセージid

        Returns
        -------
        bool
            成功したか否か
        """
        args = {'messageId': f'{message_id}'}
        data = await self.http.request(Route('POST', '/api/messaging/messages/delete'), json=args, auth=True)
        return bool(data)

    @get_cache_key
    async def fetch_user(self, user_id: Optional[str] = None, username: Optional[str] = None,
                         host: Optional[str] = None, **kwargs) -> User:
        """
        サーバーにアクセスし、ユーザーのプロフィールを取得します。基本的には get_userをお使いください。

        Parameters
        ----------
        user_id : str
            取得したいユーザーのユーザーID
        username : str
            取得したいユーザーのユーザー名
        host : str, default=None
            取得したいユーザーがいるインスタンスのhost

        Returns
        -------
        dict
            ユーザー情報
        """
        if not check_multi_arg(user_id, username):
            raise NotExistRequiredParameters("user_id, usernameどちらかは必須です")

        field = remove_dict_empty({"userId": user_id, "username": username, "host": host})
        data = await self.http.request(Route('POST', '/api/users/show'), json=field, auth=True, lower=True)
        old_cache = Cache(namespace='get_user')
        await old_cache.delete(kwargs['cache_key'].format('get_user'))
        return User(RawUser(data), state=self)

    async def get_followers(
            self,
            user_id: Optional[str] = None,
            username: Optional[str] = None,
            host: Optional[str] = None,
            since_id: Optional[str] = None,
            until_id: Optional[str] = None,
            limit: int = 10,
            get_all: bool = False,
    ) -> AsyncIterator[Followee]:
        """
        与えられたユーザーのフォロワーを取得します

        Parameters
        ----------
        user_id : str, default=None
            ユーザーのid
        username : str, default=None
            ユーザー名
        host : str, default=None
            ユーザーがいるインスタンスのhost名
        since_id : str, default=None
        until_id : str, default=None
            前回の最後の値を与える(既に実行し取得しきれない場合に使用)
        limit : int, default=10
            取得する情報の最大数 max: 100
        get_all : bool, default=False
            全てのフォロワーを取得する
        Yields
        ------
        dict
            フォロワーの情報
        Raises
        ------
        InvalidParameters
            limit引数が不正な場合
        """
        if not check_multi_arg(user_id, username):
            raise NotExistRequiredParameters("user_id, usernameどちらかは必須です")

        if limit > 100:
            raise InvalidParameters("limit は100以上を受け付けません")

        data = remove_dict_empty(
            {
                "userId": user_id,
                "username": username,
                "host": host,
                "sinceId": since_id,
                "untilId": until_id,
                "limit": limit,
            }
        )
        if get_all:
            loop = True
            while loop:
                get_data = await self.http.request(Route('POST', '/api/users/followers'), json=data, auth=True, lower=True)
                if len(get_data) > 0:
                    data["untilId"] = get_data[-1]["id"]
                else:
                    break
                for i in [Followee(i, state=self) for i in get_data]:
                    yield i
        else:
            get_data = await self.http.request(Route('POST', '/api/users/followers'), json=data, auth=True, lower=True)
            for i in [Followee(i, state=self) for i in get_data]:
                yield i

    @cached(ttl=10, key_builder=key_builder, key='get_instance')
    async def get_instance(self, host: Optional[str] = None, detail: bool = False) -> Union[InstanceMeta, Instance]:
        if host is None:
            data = await self.http.request(Route('POST', '/api/meta'), json={'detail': detail}, auth=True, lower=True)
            return InstanceMeta(data, state=self)
        data = await self.http.request(Route('POST', '/api/federation/show-instance'), json={'host': host}, auth=True,
                                       lower=True)
        return Instance(data, state=self)

    @get_cache_key
    async def fetch_instance(self, host: Optional[str] = None, **kwargs):
        old_cache = Cache(namespace='get_instance')
        await old_cache.delete(kwargs['cache_key'].format('get_instance'))
        return await self.get_instance(host=host)

    async def remove_emoji(self, emoji_id: str) -> bool:
        return bool(await self.http.request(Route('POST', '/api/admin/emoji/remove'), json={'id': emoji_id}, auth=True))


    async def get_user_notes(
            self,
            user_id: str,
            *,
            since_id: Optional[str] = None,
            include_my_renotes: bool = True,
            include_replies: bool = True,
            with_files: bool = False,
            until_id: Optional[str] = None,
            limit: int = 10,
            get_all: bool = False,
            exclude_nsfw: bool = True,
            file_type: Optional[List[str]] = None,
            since_date: int = 0,
            until_data: int = 0
    ) -> Generator[Note]:
        if limit > 100:
            raise InvalidParameters("limit は100以上を受け付けません")

        args = remove_dict_empty(
            {
                "userId": user_id,
                "includeReplies": include_replies,
                "limit": limit,
                "sinceId": since_id,
                "untilId": until_id,
                "sinceDate": since_date,
                "untilDate": until_data,
                "includeMyRenotes": include_my_renotes,
                "withFiles": with_files,
                "fileType": file_type,
                "excludeNsfw": exclude_nsfw
            }
        )
        if get_all:
            loop = True
            while loop:
                get_data = await self.http.request(Route('POST', '/api/users/notes'), json=args, auth=True, lower=True)
                if len(list(get_data)) <= 0:
                    break
                args["untilId"] = get_data[-1]["id"]
                for data in get_data:
                    yield Note(RawNote(data), state=self)
        else:
            get_data = await self.http.request(Route('POST', '/api/users/notes'), json=args, auth=True, lower=True)
            for data in get_data:
                yield Note(RawNote(**upper_to_lower(data)), state=self)

    async def get_announcements(self, limit: int, with_unreads: bool, since_id: str, until_id: str):
        """
        Parameters
        ----------
        limit: int
            最大取得数
        with_unreads: bool
            既読済みか否か
        since_id: str
        until_id: str
            前回の最後の値を与える(既に実行し取得しきれない場合に使用)
        """

        if limit > 100:
            raise InvalidParameters("limit は100以上を受け付けません")

        args = {
            "limit": limit,
            "withUnreads": with_unreads,
            "sinceId": since_id,
            "untilId": until_id,
        }
        return await self.http.request(Route('POST', '/api/announcements'), json=args, auth=True, lower=True)

    async def file_upload(
            self,
            name: Optional[str] = None,
            to_file: Optional[str] = None,
            to_url: Optional[str] = None,
            *,
            force: bool = False,
            is_sensitive: bool = False,
    ) -> File:

        if to_file and to_url is None:  # ローカルからアップロードする
            with open(to_file, "rb") as f:
                args = remove_dict_empty({"isSensitive": is_sensitive, "force": force, "name": f"{name}", 'file': f})
                res = await self.http.request(Route('POST', '/api/drive/files/create'), data=args, auth=True, lower=True)
        elif to_file is None and to_url:  # URLからアップロードする
            args = {"url": to_url, "force": force, "isSensitive": is_sensitive}
            res = await self.http.request(Route('POST', '/api/drive/files/upload-from-url'), json=args, auth=True, lower=True)
        else:
            raise InvalidParameters("path または url のどちらかは必須です")
        return File(RawFile(res), state=self)
