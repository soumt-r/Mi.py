from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Dict, TYPE_CHECKING

from mi.framework.models.chat import Chat
from mi.framework.models.emoji import Emoji
from mi.framework.models.note import Note, Reaction
from mi.framework.models.user import FollowRequest, User
from mi.utils import get_module_logger, str_lower, upper_to_lower
from mi.wrapper.models.chat import RawChat
from mi.wrapper.models.note import RawNote
from mi.wrapper.models.user import RawUser

if TYPE_CHECKING:
    from mi.framework.client import Client
    from mi.types import NotePayload, ChatPayload


class ConnectionState:
    def __init__(self, dispatch: Callable[..., Any], loop: asyncio.AbstractEventLoop, client: Client):
        self.client: Client = client
        self.dispatch = dispatch
        self.logger = get_module_logger(__name__)
        self.loop: asyncio.AbstractEventLoop = loop
        self.parsers = parsers = {}
        for attr, func in inspect.getmembers(self):
            if attr.startswith('parse'):
                parsers[attr[6:].upper()] = func

    def parse_emoji_added(self, message: Dict[str, Any]):
        self.dispatch('emoji_add', Emoji(message['body']['emoji']))

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

        self.dispatch('follow_request', FollowRequest(message))

    def parse_me_updated(self, message: Dict[str, Any]):
        pass

    def parse_read_all_announcements(self, message: Dict[str, Any]) -> None:
        pass  # TODO: 実装

    def parse_reply(self, message: NotePayload) -> None:
        """
        リプライ
        """
        self.dispatch('message', Note(RawNote(message)))

    def parse_follow(self, message: Dict[str, Any]) -> None:
        """
        ユーザーをフォローした際のイベントを解析する関数
        """

        self.dispatch('user_follow', User(RawUser(message)))

    def parse_followed(self, message: Dict[str, Any]) -> None:
        """
        フォローイベントを解析する関数
        """

        self.dispatch('follow', User(RawUser(message)))

    def parse_mention(self, message: Dict[str, Any]) -> None:
        """
        メンションイベントを解析する関数
        """

        self.dispatch('mention', Note(RawNote(message)))

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

    def parse_url_upload_finished(self, message: Dict[str, Any]) -> None:
        pass # TODO:実装

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
        self.dispatch('message', Chat(RawChat(message)))

    def parse_unread_messaging_message(self, message: Dict[str, Any]) -> None:
        """
        チャットが既読になっていない場合のデータを処理する関数
        """
        self.dispatch('message', Chat(RawChat(message)))

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
        self.dispatch('reaction', Reaction(message))

    def parse_note(self, message: NotePayload) -> None:
        """
        ノートイベントを解析する関数
        """
        note = Note(RawNote(message))
        # Router(self.http.ws).capture_message(note.id) TODO: capture message
        self.client._on_message(note)
