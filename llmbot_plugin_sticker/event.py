# -*- coding: utf-8 -*-
# @Time    : 2023/10/23 上午12:17
# @Author  : sudoskys
# @File    : event.py
# @Software: PyCharm
import pathlib
import re
from typing import Tuple, Union

import emoji


class StickerEvent(object):
    def __init__(self, sticker_dir: pathlib.Path):
        if not sticker_dir.exists() or not sticker_dir.is_dir():
            raise Exception(f'sticker dir not exists {sticker_dir}')
        self.sticker_dir = sticker_dir
        self.sticker_tale = {}
        self.emoji_pattern = re.compile("["
                                        u"\U0001F600-\U0001F64F"  # emoticons
                                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                        "]+", flags=re.UNICODE)
        self.get_sticker_table()

    def get_sticker_table(self) -> None:
        sticker_list = list(self.sticker_dir.glob('*.png'))
        _emoji = {}
        for sticker in sticker_list:
            # 校验是否名称
            if len(emoji.emojize(sticker.stem)) == 1:
                # 存储 raw
                _emoji[emoji.demojize(sticker.stem)] = sticker.absolute()
        self.sticker_tale = _emoji

    def prompt(self):
        _emoji_list = ""
        for _emoji in self.sticker_tale.keys():
            _emoji_list += f"{_emoji.strip(':')},"
        return f"[{_emoji_list}]"

    def get_sticker(self, emoji_text: str) -> Union[Tuple[str, pathlib.Path], Tuple[None, None]]:
        # 首取
        _table = self.emoji_pattern.findall(emoji_text)
        if _table:
            emoji_text = _table[0]
        # 重新解码
        emoji_text = emoji.demojize(emoji_text)

        # 修复不规范码
        emoji_text = f":{emoji_text.strip(':')}:"

        if emoji_text in self.sticker_tale:
            return emoji_text, self.sticker_tale[emoji_text]
        return None, None
