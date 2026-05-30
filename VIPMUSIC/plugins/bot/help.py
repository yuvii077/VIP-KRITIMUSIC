#
# Copyright (C) 2024 by THE-VIP-BOY-OP@Github, < https://github.com/THE-VIP-BOY-OP >.
#
# This file is part of < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC > project,
# and is released under the MIT License.
# Please see < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC/blob/master/LICENSE >
#
# All rights reserved.
#

from __future__ import annotations

import re
from math import ceil
from typing import Union

import config
from config import BANNED_USERS, START_IMG_URL
from pyrogram import Client, filters, types
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from strings import get_command, get_string
from strings import helpers
from VIPMUSIC import HELPABLE, app
from VIPMUSIC.utils.database import get_lang, is_commanddelete_on
from VIPMUSIC.utils.decorators.language import LanguageStart, languageCB
from VIPMUSIC.utils.inline.help import private_help_panel

# ─────────────────────────── Constants ────────────────────────────────────────

HELP_COMMAND = get_command("HELP_COMMAND")

COLUMN_SIZE: int = 4
NUM_COLUMNS: int = 3

DONATE_IMG: str = "https://envs.sh/AeS.jpg"

# ─────────────────────────── Helpers ──────────────────────────────────────────


class EqInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton with ordering support (for sorted())."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InlineKeyboardButton) and self.text == other.text

    def __lt__(self, other: EqInlineKeyboardButton) -> bool:
        return self.text < other.text

    def __gt__(self, other: EqInlineKeyboardButton) -> bool:
        return self.text > other.text


def paginate_modules(
    page_n: int,
    module_dict: dict,
    prefix: str,
    chat: int | None = None,
    close: bool = False,
) -> list[list[EqInlineKeyboardButton]]:
    """Build a paginated keyboard from a module dictionary."""

    def make_button(module_name: str) -> EqInlineKeyboardButton:
        if chat:
            cb = f"{prefix}_module({chat},{module_name.lower()},{page_n})"
        else:
            cb = f"{prefix}_module({module_name.lower()},{page_n})"
        return EqInlineKeyboardButton(module_name, callback_data=cb)

    modules = sorted(make_button(x.__MODULE__) for x in module_dict.values())
    pairs = [modules[i : i + NUM_COLUMNS] for i in range(0, len(modules), NUM_COLUMNS)]

    max_num_pages = ceil(len(pairs) / COLUMN_SIZE) if pairs else 1
    modulo_page = page_n % max_num_pages

    nav_label = "ᴄʟᴏsᴇ" if close else "Bᴀᴄᴋ"
    nav_cb = "close" if close else "feature"

    if len(pairs) > COLUMN_SIZE:
        prev_page = modulo_page - 1 if modulo_page > 0 else max_num_pages - 1
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (
                EqInlineKeyboardButton("❮", callback_data=f"{prefix}_prev({prev_page})"),
                EqInlineKeyboardButton(nav_label, callback_data=nav_cb),
                EqInlineKeyboardButton("❯", callback_data=f"{prefix}_next({modulo_page + 1})"),
            )
        ]
    else:
        pairs.append([EqInlineKeyboardButton(nav_label, callback_data=nav_cb)])

    return pairs


def _make_back_keyboard(callback_data: str, label: str = "BACK_BUTTON") -> InlineKeyboardMarkup:
    """Generic single-button 'back' keyboard factory."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="✯ ʙᴀᴄᴋ ✯", callback_data=callback_data)]]
    )


def back_to_music(_: dict) -> InlineKeyboardMarkup:
    return _make_back_keyboard("music")


def back_to_tools(_: dict) -> InlineKeyboardMarkup:
    return _make_back_keyboard("tools")


def back_to_management(_: dict) -> InlineKeyboardMarkup:
    return _make_back_keyboard("management")


async def help_parser(
    _name: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> InlineKeyboardMarkup:
    return keyboard or InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))


# ─────────────────────────── Help Command ─────────────────────────────────────


@app.on_message(filters.command(HELP_COMMAND) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(
    client: Client,
    update: Union[types.Message, types.CallbackQuery],
) -> None:
    is_callback = isinstance(update, types.CallbackQuery)

    if is_callback:
        try:
            await update.answer()
        except Exception:
            pass

        chat_id = update.message.chat.id
        _ = get_string(await get_lang(chat_id))
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
        await update.edit_message_text(_["help_1"], reply_markup=keyboard)
    else:
        chat_id = update.chat.id

        if await is_commanddelete_on(chat_id):
            try:
                await update.delete()
            except Exception:
                pass

        _ = get_string(await get_lang(chat_id))
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help", close=True))

        if START_IMG_URL:
            await update.reply_photo(photo=START_IMG_URL, caption=_["help_1"], reply_markup=keyboard)
        else:
            await update.reply_text(text=_["help_1"], reply_markup=keyboard)


@app.on_message(filters.command(HELP_COMMAND) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client: Client, message: Message, _: dict) -> None:
    keyboard = private_help_panel(_)
    await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard))


# ─────────────────────────── Help Button Router ───────────────────────────────


@app.on_callback_query(filters.regex(r"help_(.*?)"))
async def help_button(client: Client, query: CallbackQuery) -> None:
    language = await get_lang(query.message.chat.id)
    _ = get_string(language)
    top_text: str = _["help_1"]

    home_match  = re.match(r"help_home\((.+?)\)", query.data)
    mod_match   = re.match(r"help_module\((.+?),(.+?)\)", query.data)
    prev_match  = re.match(r"help_prev\((.+?)\)", query.data)
    next_match  = re.match(r"help_next\((.+?)\)", query.data)
    back_match  = re.match(r"help_back\((\d+)\)", query.data)
    create_match = re.match(r"help_create", query.data)

    if mod_match:
        module = mod_match.group(1)
        prev_page_num = int(mod_match.group(2))
        text = (
            f"<b><u>ʜᴇʀᴇ ɪs ᴛʜᴇ ʜᴇʟᴘ ғᴏʀ {HELPABLE[module].__MODULE__}:</u></b>\n"
            + HELPABLE[module].__HELP__
        )
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("↪️ ʙᴀᴄᴋ", callback_data=f"help_back({prev_page_num})"),
                    InlineKeyboardButton("🔄 ᴄʟᴏsᴇ", callback_data="close"),
                ]
            ]
        )
        await query.message.edit(text=text, reply_markup=key, disable_web_page_preview=True)

    elif home_match:
        await app.send_message(query.from_user.id, text=top_text)
        await query.message.delete()

    elif prev_match:
        curr_page = int(prev_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(paginate_modules(curr_page, HELPABLE, "help")),
            disable_web_page_preview=True,
        )

    elif next_match:
        next_page = int(next_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(paginate_modules(next_page, HELPABLE, "help")),
            disable_web_page_preview=True,
        )

    elif back_match:
        prev_page_num = int(back_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(paginate_modules(prev_page_num, HELPABLE, "help")),
            disable_web_page_preview=True,
        )

    elif create_match:
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
            disable_web_page_preview=True,
        )

    await client.answer_callback_query(query.id)


# ─────────────────────────── Category Callbacks ───────────────────────────────

_HELP_SECTION_TEXT = (
    "**ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ғᴏʀ ᴍᴏʀᴇ ɪɴғᴏʀᴍᴀᴛɪᴏɴ. "
    "ɪғ ʏᴏᴜ'ʀᴇ ғᴀᴄɪɴɢ ᴀɴʏ ᴘʀᴏʙʟᴇᴍ ʏᴏᴜ ᴄᴀɴ ᴀsᴋ ɪɴ "
    "[sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ.](t.me/tg_friendsss)**\n\n"
    "**ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs ᴄᴀɴ ʙᴇ ᴜsᴇᴅ ᴡɪᴛʜ: /**"
)


@app.on_callback_query(filters.regex("music_callback") & ~BANNED_USERS)
@languageCB
async def music_helper_cb(client: Client, query: CallbackQuery, _: dict) -> None:
    cb = query.data.strip().split(None, 1)[1]
    keyboard = back_to_music(_)

    # fmt: off
    help_map: dict[str, str] = {
        "hb1":  helpers.HELP_1,  "hb2":  helpers.HELP_2,
        "hb3":  helpers.HELP_3,  "hb4":  helpers.HELP_4,
        "hb5":  helpers.HELP_5,  "hb6":  helpers.HELP_6,
        "hb7":  helpers.HELP_7,  "hb8":  helpers.HELP_8,
        "hb9":  helpers.HELP_9,  "hb10": helpers.HELP_10,
        "hb11": helpers.HELP_11, "hb12": helpers.HELP_12,
        "hb13": helpers.HELP_13, "hb14": helpers.HELP_14,
        "hb15": helpers.HELP_15,
    }
    # fmt: on

    if text := help_map.get(cb):
        await query.edit_message_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex("management_callback") & ~BANNED_USERS)
@languageCB
async def management_callback_cb(client: Client, query: CallbackQuery, _: dict) -> None:
    cb = query.data.strip().split(None, 1)[1]
    keyboard = back_to_management(_)

    # fmt: off
    help_map: dict[str, str] = {
        "extra": helpers.EXTRA_1,
        "hb1":   helpers.MHELP_1,  "hb2":  helpers.MHELP_2,
        "hb3":   helpers.MHELP_3,  "hb4":  helpers.MHELP_4,
        "hb5":   helpers.MHELP_5,  "hb6":  helpers.MHELP_6,
        "hb7":   helpers.MHELP_7,  "hb8":  helpers.MHELP_8,
        "hb9":   helpers.MHELP_9,  "hb10": helpers.MHELP_10,
        "hb11":  helpers.MHELP_11, "hb12": helpers.MHELP_12,
    }
    # fmt: on

    if text := help_map.get(cb):
        await query.edit_message_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex("tools_callback") & ~BANNED_USERS)
@languageCB
async def tools_callback_cb(client: Client, query: CallbackQuery, _: dict) -> None:
    cb = query.data.strip().split(None, 1)[1]
    keyboard = back_to_tools(_)

    # fmt: off
    help_map: dict[str, str] = {
        "ai":    helpers.AI_1,
        "hb1":   helpers.THELP_1,  "hb2":  helpers.THELP_2,
        "hb3":   helpers.THELP_3,  "hb4":  helpers.THELP_4,
        "hb5":   helpers.THELP_5,  "hb6":  helpers.THELP_6,
        "hb7":   helpers.THELP_7,  "hb8":  helpers.THELP_8,
        "hb9":   helpers.THELP_9,  "hb10": helpers.THELP_10,
        "hb11":  helpers.THELP_11, "hb12": helpers.THELP_12,
    }
    # fmt: on

    if text := help_map.get(cb):
        await query.edit_message_text(text, reply_markup=keyboard)


# ─────────────────────────── Feature / Category Menus ─────────────────────────

_FEATURE_TEXT = """\
**❖ ᴛʜɪs ɪs {mention} !

━━━━━━━━━━━━━━━━━━━━━━━━━━
❖ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ | ᴍᴜsɪᴄ ʙᴏᴛ
❖ ɴᴏ ʟᴀɢ  •  ɴᴏ ᴀᴅs  •  ɴᴏ ᴘʀᴏᴍᴏ
❖ 24 × 7 ʀᴜɴɴɪɴɢ  •  ʙᴇsᴛ sᴏᴜɴᴅ ǫᴜᴀʟɪᴛʏ
━━━━━━━━━━━━━━━━━━━━━━━━━━
❖ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴғᴏ
   ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs!
━━━━━━━━━━━━━━━━━━━━━━━━━━**\
"""

_FEATURE_KEYBOARD: list[list[InlineKeyboardButton]] = [
    [
        InlineKeyboardButton(
            "⚜️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ / ᴄʜᴀɴɴᴇʟ ⚜️",
            url=f"https://t.me/{app.username}?startgroup=true",
        )
    ],
    [
        InlineKeyboardButton("🎵 ᴍᴜsɪᴄ", callback_data="music"),
        InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ", callback_data="management"),
    ],
    [
        InlineKeyboardButton("🛠 ᴛᴏᴏʟs", callback_data="tools"),
        InlineKeyboardButton("📋 ᴀʟʟ", callback_data="settings_back_helper"),
    ],
    [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="go_to_start")],
]


@app.on_callback_query(filters.regex("^feature$"))
@app.on_callback_query(filters.regex("^back_to_music$"))
async def feature_callback(client: Client, callback_query: CallbackQuery) -> None:
    await callback_query.message.edit_text(
        text=_FEATURE_TEXT.format(mention=app.mention),
        reply_markup=InlineKeyboardMarkup(_FEATURE_KEYBOARD),
    )


@app.on_callback_query(filters.regex("^music$"))
async def music_callback(client: Client, callback_query: CallbackQuery) -> None:
    # Buttons sorted A → Z (hb number = alphabetical position)
    # hb1=Admin, hb2=Auth, hb3=Bl-Chat, hb4=Bl-User, hb5=Broadcast,
    # hb6=C-Play, hb7=G-Ban, hb8=Loop, hb9=Maintenance, hb10=Ping,
    # hb11=Play, hb12=Seek, hb13=Shuffle, hb14=Song, hb15=Speed
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Aᴅᴍɪɴ",     callback_data="music_callback hb1"),
                InlineKeyboardButton("Aᴜᴛʜ",      callback_data="music_callback hb2"),
                InlineKeyboardButton("Bʟ-Cʜᴀᴛ",   callback_data="music_callback hb3"),
            ],
            [
                InlineKeyboardButton("Bʟ-Usᴇʀ",   callback_data="music_callback hb4"),
                InlineKeyboardButton("Bʀᴏᴀᴅᴄᴀsᴛ", callback_data="music_callback hb5"),
                InlineKeyboardButton("C-Pʟᴀʏ",    callback_data="music_callback hb6"),
            ],
            [
                InlineKeyboardButton("G-Bᴀɴ",        callback_data="music_callback hb7"),
                InlineKeyboardButton("Lᴏᴏᴘ",         callback_data="music_callback hb8"),
                InlineKeyboardButton("Mᴀɪɴᴛᴇɴᴀɴᴄᴇ",  callback_data="music_callback hb9"),
            ],
            [
                InlineKeyboardButton("Pɪɴɢ",     callback_data="music_callback hb10"),
                InlineKeyboardButton("Pʟᴀʏ",     callback_data="music_callback hb11"),
                InlineKeyboardButton("Sᴇᴇᴋ",     callback_data="music_callback hb12"),
            ],
            [
                InlineKeyboardButton("Sʜᴜғғʟᴇ",  callback_data="music_callback hb13"),
                InlineKeyboardButton("Sᴏɴɢ",     callback_data="music_callback hb14"),
                InlineKeyboardButton("Sᴘᴇᴇᴅ",    callback_data="music_callback hb15"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_HELP_SECTION_TEXT, reply_markup=keyboard)


@app.on_callback_query(filters.regex("^management$"))
async def management_callback(client: Client, callback_query: CallbackQuery) -> None:
    # Sorted A to Z: Ban, Extra, Game, Impostor, Kick, Mute, Pin, Sang Mata, Set Up, Staff, T-Graph, Translate, Zombie
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʙᴀɴ",       callback_data="management_callback hb1"),
                InlineKeyboardButton("єxᴛʀᴀ",     callback_data="management_callback extra"),
                InlineKeyboardButton("ɢᴀᴍᴇ",      callback_data="management_callback hb3"),
            ],
            [
                InlineKeyboardButton("ɪᴍᴘᴏsᴛᴇʀ",  callback_data="management_callback hb4"),
                InlineKeyboardButton("ᴋɪᴄᴋ",      callback_data="management_callback hb5"),
                InlineKeyboardButton("ᴍᴜᴛᴇ",      callback_data="management_callback hb6"),
            ],
            [
                InlineKeyboardButton("ᴘɪɴ",        callback_data="management_callback hb7"),
                InlineKeyboardButton("sᴀɴɢ ᴍᴀᴛᴀ", callback_data="management_callback hb8"),
                InlineKeyboardButton("sᴇᴛ ᴜᴘ",    callback_data="management_callback hb9"),
            ],
            [
                InlineKeyboardButton("sᴛᴀғғ",      callback_data="management_callback hb10"),
                InlineKeyboardButton("ᴛ-ɢʀᴀᴘʜ",   callback_data="management_callback hb11"),
                InlineKeyboardButton("ᴛʀᴀɴsʟᴀᴛᴇ", callback_data="management_callback hb12"),
            ],
            [
                InlineKeyboardButton("ᴢᴏᴍʙɪᴇ",    callback_data="management_callback hb13"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_HELP_SECTION_TEXT, reply_markup=keyboard)


@app.on_callback_query(filters.regex("^tools$"))
async def tools_callback(client: Client, callback_query: CallbackQuery) -> None:
    # Sorted A to Z: ChatGPT, Font, Fun, Google, Hastag, Image, Info, Math, Quotly, Stickers, Tagall, TR-DH, TTS-Voice
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ᴄʜᴀᴛɢᴘᴛ",  callback_data="tools_callback ai"),
                InlineKeyboardButton("ғᴏɴᴛ",      callback_data="tools_callback hb1"),
                InlineKeyboardButton("ғᴜɴ",        callback_data="tools_callback hb2"),
            ],
            [
                InlineKeyboardButton("ɢᴏᴏɢʟᴇ",    callback_data="tools_callback hb3"),
                InlineKeyboardButton("ʜᴀsᴛᴀɢ",    callback_data="tools_callback hb4"),
                InlineKeyboardButton("ɪᴍᴀɢᴇ",     callback_data="tools_callback hb5"),
            ],
            [
                InlineKeyboardButton("ɪɴғᴏ",       callback_data="tools_callback hb6"),
                InlineKeyboardButton("ᴍᴀᴛʜ",       callback_data="tools_callback hb7"),
                InlineKeyboardButton("ǫᴜᴏᴛʟʏ",     callback_data="tools_callback hb8"),
            ],
            [
                InlineKeyboardButton("sᴛɪᴄᴋᴇʀs",  callback_data="tools_callback hb9"),
                InlineKeyboardButton("ᴛᴀɢᴀʟʟ",     callback_data="tools_callback hb10"),
                InlineKeyboardButton("ᴛʀ-ᴅʜ",      callback_data="tools_callback hb11"),
            ],
            [
                InlineKeyboardButton("ᴛᴛs-ᴠᴏɪᴄᴇ", callback_data="tools_callback hb12"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_HELP_SECTION_TEXT, reply_markup=keyboard)


# ─────────────────────────── About / Info Panels ──────────────────────────────


@app.on_callback_query(filters.regex("^about$"))
async def about_callback(client: Client, callback_query: CallbackQuery) -> None:
    buttons = [
        [
            InlineKeyboardButton("✨ ᴅᴇᴠᴇʟᴏᴘᴇʀ ✨", callback_data="developer"),
            InlineKeyboardButton("⚡ ғᴇᴀᴛᴜʀᴇ ⚡",   callback_data="feature"),
        ],
        [
            InlineKeyboardButton("📓 ʙᴀsɪᴄ ɢᴜɪᴅᴇ 📓", callback_data="basic_guide"),
            InlineKeyboardButton("⚜️ ᴅᴏɴᴀᴛᴇ ⚜️",      callback_data="donate"),
        ],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="go_to_start")],
    ]

    text = (
        f"**ʜɪ! ɪ ᴀᴍ {app.mention} ✨**\n\n"
        "**ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ + ᴍᴜsɪᴄ ʙᴏᴛ ᴛʜᴀᴛ ᴋᴇᴇᴘs ʏᴏᴜʀ "
        "ɢʀᴏᴜᴘ sᴘᴀᴍ-ғʀᴇᴇ ᴀɴᴅ ғᴜɴ :)**\n\n"
        "● ɪ ᴄᴀɴ ʀᴇsᴛʀɪᴄᴛ / ʙᴀɴ / ᴍᴜᴛᴇ ᴜsᴇʀs.\n"
        "● ɪ sᴇɴᴅ ᴄᴜsᴛᴏᴍɪᴢᴀʙʟᴇ ᴡᴇʟᴄᴏᴍᴇ ᴍᴇssᴀɢᴇs ᴀɴᴅ ɢʀᴏᴜᴘ ʀᴜʟᴇs.\n"
        "● ɪ ʜᴀᴠᴇ ᴀ ғᴜʟʟ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ sʏsᴛᴇᴍ.\n"
        "● ɪ sᴜᴘᴘᴏʀᴛ ɴᴏᴛᴇs, ʙʟᴀᴄᴋʟɪsᴛs, ᴀᴜᴛᴏ-ʀᴇᴘʟɪᴇs, ᴀɴᴅ ᴍᴏʀᴇ.\n"
        "● ɪ ᴄʜᴇᴄᴋ ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs ʙᴇғᴏʀᴇ ᴇᴠᴇʀʏ ᴀᴄᴛɪᴏɴ.\n\n"
        "**➻ ᴄʟɪᴄᴋ ᴀ ʙᴜᴛᴛᴏɴ ᴛᴏ ʟᴇᴀʀɴ ᴍᴏʀᴇ 🦚**"
    )

    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex("^developer$"))
async def developer_callback(client: Client, callback_query: CallbackQuery) -> None:
    buttons = [
        [
            InlineKeyboardButton("🔰 ᴏᴡɴᴇʀ 🔰",   user_id=config.OWNER_ID[0]),
            InlineKeyboardButton("📍 sᴜᴅᴏᴇʀs 📍", url=f"https://t.me/{app.username}?start=sudo"),
        ],
        [
            InlineKeyboardButton("🎁 ɪɴsᴛᴀ 🎁",    url="https://instagram.com/the.vip.boy"),
            InlineKeyboardButton("💲 ʏᴏᴜᴛᴜʙᴇ 💲",  url="https://youtube.com/@THE_VIP_BOY"),
        ],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="about")],
    ]

    text = (
        "✦ **ᴛʜɪs ʙᴏᴛ ɪs ʙᴜɪʟᴛ ʙʏ ᴀ sᴋɪʟʟᴇᴅ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ ᴍᴀᴋᴇ ɢʀᴏᴜᴘ "
        "ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴇᴀsʏ ᴀɴᴅ ᴍᴏʀᴇ ғᴜɴ.**\n\n"
        "✦ **ᴡɪᴛʜ ᴊᴜsᴛ ᴀ ғᴇᴡ ᴄʟɪᴄᴋs, ᴄᴏɴᴛʀᴏʟ ᴇᴠᴇʀʏᴛʜɪɴɢ — ᴏᴡɴᴇʀ sᴇᴛᴛɪɴɢs, "
        "sᴜᴅᴏᴇʀs, ɪɴsᴛᴀɢʀᴀᴍ, ʏᴏᴜᴛᴜʙᴇ ᴀɴᴅ ᴍᴏʀᴇ.**\n\n"
        "✦ **ᴅᴇsɪɢɴᴇᴅ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ sᴍᴏᴏᴛʜʟʏ ᴀɴᴅ ᴇɴᴊᴏʏ ᴍᴜsɪᴄ ᴛᴏᴏ. "
        "ᴊᴜsᴛ ᴛᴀᴘ ᴀ ʙᴜᴛᴛᴏɴ ᴀɴᴅ sᴇᴇ ʜᴏᴡ ᴇᴀsʏ ɪᴛ ɪs!**"
    )

    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex("^support$"))
async def support_callback(client: Client, callback_query: CallbackQuery) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🎭 ᴏᴡɴᴇʀ 🎭",   user_id=config.OWNER_ID[0]),
            InlineKeyboardButton("🌱 ɢɪᴛʜᴜʙ 🌱",  url="https://github.com/THE-VIP-BOY-OP"),
        ],
        [
            InlineKeyboardButton("⛅ ɢʀᴏᴜᴘ ⛅",   url=config.SUPPORT_GROUP),
            InlineKeyboardButton("🎄 ᴄʜᴀɴɴᴇʟ 🎄", url=config.SUPPORT_CHANNEL),
        ],
        [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="go_to_start")],
    ]

    text = (
        "**๏ ᴄʟɪᴄᴋ ᴀ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ**\n\n"
        "**ɪғ ʏᴏᴜ ғɪɴᴅ ᴀɴʏ ᴇʀʀᴏʀ ᴏʀ ʙᴜɢ, ᴏʀ ᴡᴀɴᴛ ᴛᴏ ɢɪᴠᴇ ғᴇᴇᴅʙᴀᴄᴋ, "
        "ʏᴏᴜ ᴀʀᴇ ᴀʟᴡᴀʏs ᴡᴇʟᴄᴏᴍᴇ ɪɴ ᴏᴜʀ sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ ✿◠‿◠**"
    )

    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


@app.on_callback_query(filters.regex("^donate$"))
async def donate_callback(client: Client, callback_query: CallbackQuery) -> None:
    close = [[InlineKeyboardButton("✯ ᴄʟᴏsᴇ ✯", callback_data="close")]]
    caption = (
        "**sᴜᴘᴘᴏʀᴛ ᴍʏ ᴄᴏᴅɪɴɢ ᴊᴏᴜʀɴᴇʏ ʙʏ ᴅᴏɴᴀᴛɪɴɢ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ʜᴇʟᴘ "
        "ᴇɴʜᴀɴᴄᴇ ᴛʜɪs ʙᴏᴛ's ғᴇᴀᴛᴜʀᴇs.**\n\n"
        "**ʏᴏᴜʀ ᴄᴏɴᴛʀɪʙᴜᴛɪᴏɴ ᴅɪʀᴇᴄᴛʟʏ ғᴜɴᴅs ɪɴɴᴏᴠᴀᴛɪᴠᴇ ᴛᴏᴏʟs ᴀɴᴅ "
        "ᴇxᴄɪᴛɪɴɢ ɴᴇᴡ ᴄᴀᴘᴀʙɪʟɪᴛɪᴇs.**\n\n"
        "**sᴄᴀɴ ᴛʜᴇ ᴄᴏᴅᴇ ᴀɴᴅ ᴍᴀᴋᴇ ᴀ ᴘᴀʏᴍᴇɴᴛ — ǫᴜɪᴄᴋ, ᴇᴀsʏ, ɪᴍᴘᴀᴄᴛғᴜʟ.**\n\n"
        "**ᴇᴠᴇʀʏ ᴅᴏɴᴀᴛɪᴏɴ, ʙɪɢ ᴏʀ sᴍᴀʟʟ, ᴘᴜsʜᴇs ᴛʜɪs ᴘʀᴏᴊᴇᴄᴛ ғᴏʀᴡᴀʀᴅ. "
        "ᴛʜᴀɴᴋ ʏᴏᴜ! 💙**"
    )
    await callback_query.message.reply_photo(
        photo=DONATE_IMG,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(close),
    )


@app.on_callback_query(filters.regex("^basic_guide$"))
async def basic_guide_callback(client: Client, callback_query: CallbackQuery) -> None:
    keyboard = [[InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="about")]]
    guide_text = (
        f"**ʜᴇʏ! ᴛʜɪs ɪs ᴀ ǫᴜɪᴄᴋ ɢᴜɪᴅᴇ ᴛᴏ ᴜsɪɴɢ** {app.mention} **🎉**\n\n"
        "**1.** ᴄʟɪᴄᴋ **'ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ'** ʙᴜᴛᴛᴏɴ.\n"
        "**2.** sᴇʟᴇᴄᴛ ʏᴏᴜʀ ɢʀᴏᴜᴘ ɴᴀᴍᴇ.\n"
        "**3.** ɢʀᴀɴᴛ ᴛʜᴇ ʙᴏᴛ ᴀʟʟ ɴᴇᴄᴇssᴀʀʏ ᴘᴇʀᴍɪssɪᴏɴs.\n\n"
        "**ᴛᴏ ᴀᴄᴄᴇss ᴄᴏᴍᴍᴀɴᴅs, ᴄʜᴏᴏsᴇ ʙᴇᴛᴡᴇᴇɴ ᴍᴜsɪᴄ ᴏʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴘʀᴇғᴇʀᴇɴᴄᴇs.**\n"
        "**ɪғ ʏᴏᴜ sᴛɪʟʟ ғᴀᴄᴇ ɪssᴜᴇs, ʀᴇᴀᴄʜ ᴏᴜᴛ ᴛᴏ ᴏᴜʀ sᴜᴘᴘᴏʀᴛ ✨**"
    )
    await callback_query.message.edit_text(
        text=guide_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
