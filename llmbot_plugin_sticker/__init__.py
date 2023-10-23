# -*- coding: utf-8 -*-
# @Time    : 2023/10/22 下午11:30
# @Author  : sudoskys
# @File    : __init__.py.py
# @Software: PyCharm
__plugin_name__ = "reply_emoji"
__openapi_version__ = "20231017"

import os
import pathlib
import random
from typing import Optional

import emoji
from llmkira.sdk.func_calling import verify_openapi_version

verify_openapi_version(__plugin_name__, __openapi_version__)

from loguru import logger
from pydantic import validator, BaseModel, Field

from llmkira.schema import RawMessage
from llmkira.sdk.endpoint.openai import Function
from llmkira.sdk.func_calling import PluginMetadata, BaseTool
from llmkira.sdk.func_calling.schema import FuncPair
from llmkira.task import Task, TaskHeader

from llmbot_plugin_sticker.event import StickerEvent

dir_path = os.path.split(os.path.realpath(__file__))[0]
_pack = pathlib.Path(dir_path + '/sticker.zip')
if not _pack.exists():
    raise ValueError("sticker.zip not found")

_cache = pathlib.Path.home() / ".cache" / "sticker"
if not _cache.exists():
    _cache.mkdir(parents=False, exist_ok=True)
    # 解压到 cache
    import zipfile

    print("Unzip sticker")
    with zipfile.ZipFile(_pack, "r") as zip_ref:
        zip_ref.extractall(_cache)

sticker_event = StickerEvent(sticker_dir=_cache)

sticker = Function(name=__plugin_name__,
                   description=f"Respond emotionally(emoji_sticker) to messages")
sticker.add_property(
    property_name="select_emoji",
    property_description=f"EMOJI ONLY IN {sticker_event.prompt()}",
    property_type="string",
    required=True
)


class Sticker(BaseModel):
    select_emoji: Optional[str] = Field(default=None, description=f"EMOJI ONLY IN {sticker_event.prompt()}")

    class Config:
        extra = "allow"

    @validator("select_emoji")
    def delay_validator(cls, v):
        if not v:
            raise ValueError("没想好要发什么表情呢")
        return v


class StickerTool(BaseTool):
    """
    搜索工具
    """
    silent: bool = True
    function: Function = sticker
    keywords: list = ["贴纸", "表情", "emoji", "sticker"]
    require_auth: bool = False
    repeatable = True

    def pre_check(self):
        return True

    def func_message(self, message_text):
        """
        如果合格则返回message，否则返回None，表示不处理
        """
        for i in self.keywords:
            if i in message_text:
                return self.function
        # 正则匹配
        if self.pattern:
            match = self.pattern.match(message_text)
            if match:
                return self.function
        # 加入随机因子
        if len(message_text) < 50:
            if random.randint(0, 100) < 50:
                return self.function
        return None

    async def failed(self, platform, task, receiver, reason):
        try:
            _meta = task.task_meta.reply_notify(
                plugin_name=__plugin_name__,
                callback=task.task_meta.callback,
            )
            await Task(queue=platform).send_task(
                task=TaskHeader(
                    sender=task.sender,
                    receiver=receiver,
                    task_meta=_meta,
                    message=[
                        RawMessage(
                            user_id=receiver.user_id,
                            chat_id=receiver.chat_id,
                            text=f"刚刚想发贴纸发不出来，因为系统说{reason} ..."
                        )
                    ]
                )
            )
        except Exception as e:
            logger.error(e)

    async def callback(self, sign: str, task: TaskHeader):
        return None

    async def run(self, task: TaskHeader, receiver: TaskHeader.Location, arg, **kwargs):
        """
        处理message，返回message
        """
        try:
            _set = Sticker.parse_obj(arg)
            logger.debug("Plugin: {} run with arg: {}", __plugin_name__, arg)
            _sticker, _sticker_path = sticker_event.get_sticker(_set.select_emoji)
            if not _sticker_path:
                raise ValueError(f"找不着表情")
            _meta = task.task_meta.reply_message(
                plugin_name=__plugin_name__,
                callback=TaskHeader.Meta.Callback(
                    role="function",
                    name=__plugin_name__
                )
            )
            file = await RawMessage.upload_file(name=f"{emoji.demojize(_sticker)}.webp",
                                                data=_sticker_path.read_bytes())
            await Task(queue=receiver.platform).send_task(
                task=TaskHeader(
                    sender=task.sender,  # 继承发送者
                    receiver=receiver,  # 因为可能有转发，所以可以单配
                    task_meta=_meta,
                    message=[
                        RawMessage(
                            user_id=receiver.user_id,
                            chat_id=receiver.chat_id,
                            text=f"🍖 Sticker: {_sticker}",
                            just_file=True,
                            file=[file]
                        )
                    ]
                )
            )
        except Exception as e:
            logger.exception(e)
            await self.failed(platform=receiver.platform, task=task, receiver=receiver, reason=str(e))


__plugin_meta__ = PluginMetadata(
    name=__plugin_name__,
    description="send sticker when chat....",
    usage="just wait sometime....",
    openapi_version=__openapi_version__,
    function={
        FuncPair(function=sticker, tool=StickerTool)
    },
    homepage="https://github.com/LlmKira"
)
