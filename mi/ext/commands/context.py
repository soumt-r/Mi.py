from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mi.ext.commands import BotBase, CMD
    from mi.framework.models.note import Note
    from mi.framework.models.user import User


class Context:
    __slots__ = ('__message', 'bot', 'args', 'kwargs', 'command', '__cmd')

    def __init__(
            self,
            *,
            message,
            bot: BotBase,
            args=None,
            kwargs=None,
            cmd: CMD = None
    ):
        self.__message: Note = message
        self.bot: BotBase = bot
        self.args = args if args else ()
        self.kwargs = kwargs if kwargs else {}
        self.command = cmd.func
        self.__cmd = cmd

    @property
    def message(self) -> Note:
        return self.__message

    @property
    def author(self) -> User:
        return self.__message.author

    @property
    def cog(self):
        return self.bot.get_cog(self.__cmd.cog_name)
