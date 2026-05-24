# Copyright (C) 2024 by kiru-op@Github
# Updated 2026 - Pyrogram v2.x compatible

import re
from math import ceil

from pyrogram import filters, types
from pyrogram.errors import MessageNotModified, QueryIdInvalid, MessageIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
)

from config import BANNED_USERS, START_IMG_URL
from strings import get_command, get_string
from VIPMUSIC import HELPABLE, app
from VIPMUSIC.utils.database import get_lang, is_commanddelete_on
from VIPMUSIC.utils.decorators.language import LanguageStart
from VIPMUSIC.utils.inline.help import private_help_panel

HELP_COMMAND = get_command("HELP_COMMAND")

COLUMN_SIZE = 4
NUM_COLUMNS = 3

NORMAL_TO_SMALL_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ',
    'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ',
    'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
    's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
    'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ',
    'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ',
    'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
    'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x',
    'Y': 'ʏ', 'Z': 'ᴢ',
}


def to_small_caps(text: str) -> str:
    return ''.join(NORMAL_TO_SMALL_CAPS.get(c, c) for c in text)


class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text


def paginate_modules(page_n: int, module_dict: dict, prefix: str, chat=None, close: bool = False):
    sorted_modules = sorted(module_dict.values(), key=lambda x: x.__MODULE__.lower())

    if not chat:
        modules = [
            EqInlineKeyboardButton(
                to_small_caps(x.__MODULE__),
                callback_data="{}_module({},{})".format(prefix, x.__MODULE__.lower(), page_n),
            )
            for x in sorted_modules
        ]
    else:
        modules = [
            EqInlineKeyboardButton(
                to_small_caps(x.__MODULE__),
                callback_data="{}_module({},{},{})".format(prefix, chat, x.__MODULE__.lower(), page_n),
            )
            for x in sorted_modules
        ]

    pairs = [modules[i: i + NUM_COLUMNS] for i in range(0, len(modules), NUM_COLUMNS)]
    max_num_pages = ceil(len(pairs) / COLUMN_SIZE) if pairs else 1
    modulo_page = page_n % max_num_pages

    if len(pairs) > COLUMN_SIZE:
        current_pairs = pairs[modulo_page * COLUMN_SIZE: COLUMN_SIZE * (modulo_page + 1)]

        updated_pairs = []
        for row in current_pairs:
            updated_row = []
            for btn in row:
                original_module = re.search(r"_module\((.+?),", btn.callback_data)
                mod_name = original_module.group(1) if original_module else btn.text.lower()

                if not chat:
                    new_btn = EqInlineKeyboardButton(
                        btn.text,
                        callback_data="{}_module({},{})".format(prefix, mod_name, modulo_page),
                    )
                else:
                    new_btn = EqInlineKeyboardButton(
                        btn.text,
                        callback_data="{}_module({},{},{})".format(prefix, chat, mod_name, modulo_page),
                    )
                updated_row.append(new_btn)
            updated_pairs.append(updated_row)

        updated_pairs.append([
            EqInlineKeyboardButton(
                "❮",
                callback_data="{}_prev({})".format(
                    prefix,
                    modulo_page - 1 if modulo_page > 0 else max_num_pages - 1,
                ),
            ),
            EqInlineKeyboardButton(
                "ᴄʟᴏsᴇ" if close else "ʙᴀᴄᴋ",
                callback_data="close" if close else "settingsback_helper",
            ),
            EqInlineKeyboardButton(
                "❯",
                callback_data="{}_next({})".format(prefix, modulo_page + 1),
            ),
        ])
        return updated_pairs
    else:
        pairs.append([
            EqInlineKeyboardButton(
                "ᴄʟᴏsᴇ" if close else "ʙᴀᴄᴋ",
                callback_data="close" if close else "settingsback_helper",
            ),
        ])
        return pairs


@app.on_message(filters.command(HELP_COMMAND) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex(r"^settings_back_helper$") & ~BANNED_USERS)
async def helper_private(client, update: types.Message | types.CallbackQuery):
    is_callback = isinstance(update, types.CallbackQuery)

    if is_callback:
        try:
            await update.answer()
        except QueryIdInvalid:
            pass

        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))

        try:
            await update.message.edit_text(_["help_1"], reply_markup=keyboard)
        except MessageNotModified:
            pass
    else:
        chat_id = update.chat.id
        if await is_commanddelete_on(chat_id):
            try:
                await update.delete()
            except Exception:
                pass

        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help", close=True))

        if START_IMG_URL:
            await update.reply_photo(
                photo=START_IMG_URL,
                caption=_["help_1"],
                reply_markup=keyboard,
            )
        else:
            await update.reply_text(
                text=_["help_1"],
                reply_markup=keyboard,
            )


@app.on_message(filters.command(HELP_COMMAND) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard))


async def help_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    return keyboard


NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


@app.on_callback_query(filters.regex(r"^help_"))
async def help_button(client, query):
    home_match = re.match(r"help_home\((.+?)\)", query.data)
    mod_match = re.match(r"help_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back\((\d+)\)", query.data)
    create_match = re.match(r"help_create", query.data)

    language = await get_lang(query.message.chat.id)
    _ = get_string(language)
    top_text = _["help_1"]

    try:
        if mod_match:
            module = mod_match.group(1)
            prev_page_num = int(mod_match.group(2))
            text = (
                f"<b><u>ʜᴇʀᴇ ɪs ᴛʜᴇ ʜᴇʟᴘ ꜰᴏʀ {HELPABLE[module].__MODULE__}:</u></b>\n"
                + HELPABLE[module].__HELP__
            )
            key = InlineKeyboardMarkup([[
                InlineKeyboardButton("↪️ ʙᴀᴄᴋ", callback_data=f"help_back({prev_page_num})"),
                InlineKeyboardButton("🔄 ᴄʟᴏsᴇ", callback_data="close"),
            ]])
            await query.message.edit_text(
                text=text,
                reply_markup=key,
                link_preview_options=NO_PREVIEW,
            )

        elif home_match:
            await client.send_message(
                query.from_user.id,
                text=top_text,
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
            )
            try:
                await query.message.delete()
            except MessageIdInvalid:
                pass

        elif prev_match:
            curr_page = int(prev_match.group(1))
            await query.message.edit_text(
                text=top_text,
                reply_markup=InlineKeyboardMarkup(paginate_modules(curr_page, HELPABLE, "help")),
                link_preview_options=NO_PREVIEW,
            )

        elif next_match:
            next_page = int(next_match.group(1))
            await query.message.edit_text(
                text=top_text,
                reply_markup=InlineKeyboardMarkup(paginate_modules(next_page, HELPABLE, "help")),
                link_preview_options=NO_PREVIEW,
            )

        elif back_match:
            prev_page_num = int(back_match.group(1))
            await query.message.edit_text(
                text=top_text,
                reply_markup=InlineKeyboardMarkup(paginate_modules(prev_page_num, HELPABLE, "help")),
                link_preview_options=NO_PREVIEW,
            )

        elif create_match:
            await query.message.edit_text(
                text=top_text,
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
                link_preview_options=NO_PREVIEW,
            )

    except MessageNotModified:
        pass

    try:
        await query.answer()
    except QueryIdInvalid:
        pass
