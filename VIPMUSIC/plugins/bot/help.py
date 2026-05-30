#
# Copyright (C) 2024 by THE-VIP-BOY-OP@Github, < https://github.com/THE-VIP-BOY-OP >.
#
# This file is part of < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC > project,
# and is released under the MIT License.
# Please see < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC/blob/master/LICENSE >
#
# All rights reserved.
#

import re
from math import ceil
from typing import Union

import config
from config import BANNED_USERS, START_IMG_URL
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram import types

from strings import get_command, get_string
from VIPMUSIC import HELPABLE, app
from VIPMUSIC.utils.database import get_lang, is_commanddelete_on
from VIPMUSIC.utils.decorators.language import LanguageStart, languageCB
from VIPMUSIC.utils.inline.help import private_help_panel

# ─── Constants ────────────────────────────────────────────────────────────────

HELP_COMMAND = get_command("HELP_COMMAND")
COLUMN_SIZE = 4
NUM_COLUMNS = 3
DONATE_IMG = "https://envs.sh/AeS.jpg"


# ─── Helper Classes & Functions ───────────────────────────────────────────────


class EqInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton with equality/ordering support for sorting."""

    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text


def paginate_modules(page_n: int, module_dict: dict, prefix: str, chat=None, close: bool = False):
    """Build a paginated InlineKeyboard grid from a module dictionary."""
    if chat:
        modules = sorted(
            EqInlineKeyboardButton(
                x.__MODULE__,
                callback_data=f"{prefix}_module({chat},{x.__MODULE__.lower()},{page_n})",
            )
            for x in module_dict.values()
        )
    else:
        modules = sorted(
            EqInlineKeyboardButton(
                x.__MODULE__,
                callback_data=f"{prefix}_module({x.__MODULE__.lower()},{page_n})",
            )
            for x in module_dict.values()
        )

    pairs = [modules[i : i + NUM_COLUMNS] for i in range(0, len(modules), NUM_COLUMNS)]
    max_num_pages = ceil(len(pairs) / COLUMN_SIZE) if pairs else 1
    modulo_page = page_n % max_num_pages

    back_or_close = EqInlineKeyboardButton(
        "ᴄʟᴏsᴇ" if close else "ʙᴀᴄᴋ",
        callback_data="close" if close else "feature",
    )

    if len(pairs) > COLUMN_SIZE:
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (
                EqInlineKeyboardButton(
                    "❮",
                    callback_data=f"{prefix}_prev({modulo_page - 1 if modulo_page > 0 else max_num_pages - 1})",
                ),
                back_or_close,
                EqInlineKeyboardButton(
                    "❯",
                    callback_data=f"{prefix}_next({modulo_page + 1})",
                ),
            )
        ]
    else:
        pairs.append([back_or_close])

    return pairs


def _build_back_keyboard(callback_data: str, label: str = "✯ ʙᴀᴄᴋ ✯") -> InlineKeyboardMarkup:
    """Generic single-button back keyboard."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(text=label, callback_data=callback_data)]])


def back_to_music(_) -> InlineKeyboardMarkup:
    return _build_back_keyboard("music", _["BACK_BUTTON"])


def back_to_tools(_) -> InlineKeyboardMarkup:
    return _build_back_keyboard("tools", _["BACK_BUTTON"])


def back_to_management(_) -> InlineKeyboardMarkup:
    return _build_back_keyboard("management", _["BACK_BUTTON"])


async def help_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    return keyboard


# ─── Help Command Handlers ────────────────────────────────────────────────────


@app.on_message(filters.command(HELP_COMMAND) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(client, update: Union[types.Message, types.CallbackQuery]):
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
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard))


@app.on_callback_query(filters.regex(r"help_(.*?)"))
async def help_button(client, query: CallbackQuery):
    home_match  = re.match(r"help_home\((.+?)\)", query.data)
    mod_match   = re.match(r"help_module\((.+?),(.+?)\)", query.data)
    prev_match  = re.match(r"help_prev\((.+?)\)", query.data)
    next_match  = re.match(r"help_next\((.+?)\)", query.data)
    back_match  = re.match(r"help_back\((\d+)\)", query.data)
    create_match = re.match(r"help_create", query.data)

    _ = get_string(await get_lang(query.message.chat.id))
    top_text = _["help_1"]

    if mod_match:
        module = mod_match.group(1)
        prev_page_num = int(mod_match.group(2))
        text = (
            f"<b><u>Here Is The Help For {HELPABLE[module].__MODULE__}:</u></b>\n"
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


# ─── Category Callback Dispatchers ───────────────────────────────────────────

# Mapping: callback key → helpers attribute
_MUSIC_HELP_MAP = {
    "hb1":  "HELP_1",  "hb2":  "HELP_2",  "hb3":  "HELP_3",
    "hb4":  "HELP_4",  "hb5":  "HELP_5",  "hb6":  "HELP_6",
    "hb7":  "HELP_7",  "hb8":  "HELP_8",  "hb9":  "HELP_9",
    "hb10": "HELP_10", "hb11": "HELP_11", "hb12": "HELP_12",
    "hb13": "HELP_13", "hb14": "HELP_14", "hb15": "HELP_15",
}

_MANAGEMENT_HELP_MAP = {
    "extra": "EXTRA_1",
    "hb1":   "MHELP_1",  "hb2":  "MHELP_2",  "hb3":  "MHELP_3",
    "hb4":   "MHELP_4",  "hb5":  "MHELP_5",  "hb6":  "MHELP_6",
    "hb7":   "MHELP_7",  "hb8":  "MHELP_8",  "hb9":  "MHELP_9",
    "hb10":  "MHELP_10", "hb11": "MHELP_11", "hb12": "MHELP_12",
}

_TOOLS_HELP_MAP = {
    "ai":   "AI_1",
    "hb1":  "THELP_1",  "hb2":  "THELP_2",  "hb3":  "THELP_3",
    "hb4":  "THELP_4",  "hb5":  "THELP_5",  "hb6":  "THELP_6",
    "hb7":  "THELP_7",  "hb8":  "THELP_8",  "hb9":  "THELP_9",
    "hb10": "THELP_10", "hb11": "THELP_11", "hb12": "THELP_12",
}

_SECTION_INFO_TEXT = (
    "**Click on the buttons below for more information. "
    "If you're facing any problem, ask in [Support Chat](t.me/tg_friendsss)**\n\n"
    "**All commands can be used with: /**"
)


@app.on_callback_query(filters.regex("music_callback") & ~BANNED_USERS)
@languageCB
async def music_helper_cb(client, query: CallbackQuery, _):
    cb = query.data.strip().split(None, 1)[1]
    attr = _MUSIC_HELP_MAP.get(cb)
    if attr:
        await query.edit_message_text(getattr(helpers, attr), reply_markup=back_to_music(_))


@app.on_callback_query(filters.regex("management_callback") & ~BANNED_USERS)
@languageCB
async def management_callback_cb(client, query: CallbackQuery, _):
    cb = query.data.strip().split(None, 1)[1]
    attr = _MANAGEMENT_HELP_MAP.get(cb)
    if attr:
        await query.edit_message_text(getattr(helpers, attr), reply_markup=back_to_management(_))


@app.on_callback_query(filters.regex("tools_callback") & ~BANNED_USERS)
@languageCB
async def tools_callback_cb(client, query: CallbackQuery, _):
    cb = query.data.strip().split(None, 1)[1]
    attr = _TOOLS_HELP_MAP.get(cb)
    if attr:
        await query.edit_message_text(getattr(helpers, attr), reply_markup=back_to_tools(_))


# ─── Feature / Section Menus ─────────────────────────────────────────────────

def _feature_keyboard() -> list:
    return [
        [
            InlineKeyboardButton(
                "⚜️ Add Me To Your Group Or Channel ⚜️",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton("🎵 ᴍᴜsɪᴄ", callback_data="music"),
            InlineKeyboardButton("🛡 ᴍᴀɴᴀɢᴇᴍᴇɴᴛ", callback_data="management"),
        ],
        [
            InlineKeyboardButton("🔧 ᴛᴏᴏʟs", callback_data="tools"),
            InlineKeyboardButton("📋 ᴀʟʟ", callback_data="settings_back_helper"),
        ],
        [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="go_to_start")],
    ]


def _feature_text() -> str:
    return (
        f"**❖ Welcome to {app.mention}!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "❖ Management & Music Bot\n"
        "❖ No Lag | No Ads | No Promo\n"
        "❖ 24×7 Online | Best Sound Quality\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "❖ Click on Help to explore modules and commands!**"
    )


@app.on_callback_query(filters.regex("^feature$"))
async def feature_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text=_feature_text(),
        reply_markup=InlineKeyboardMarkup(_feature_keyboard()),
    )


@app.on_callback_query(filters.regex("^back_to_music$"))
async def back_to_music_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text=_feature_text(),
        reply_markup=InlineKeyboardMarkup(_feature_keyboard()),
    )


@app.on_callback_query(filters.regex("^music$"))
async def music_callback(client: Client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Admin",     callback_data="music_callback hb1"),
                InlineKeyboardButton("Auth",      callback_data="music_callback hb2"),
                InlineKeyboardButton("Broadcast", callback_data="music_callback hb3"),
            ],
            [
                InlineKeyboardButton("Bl-Chat",  callback_data="music_callback hb4"),
                InlineKeyboardButton("Bl-User",  callback_data="music_callback hb5"),
                InlineKeyboardButton("C-Play",   callback_data="music_callback hb6"),
            ],
            [
                InlineKeyboardButton("G-Ban",       callback_data="music_callback hb7"),
                InlineKeyboardButton("Loop",        callback_data="music_callback hb8"),
                InlineKeyboardButton("Maintenance", callback_data="music_callback hb9"),
            ],
            [
                InlineKeyboardButton("Ping",    callback_data="music_callback hb10"),
                InlineKeyboardButton("Play",    callback_data="music_callback hb11"),
                InlineKeyboardButton("Shuffle", callback_data="music_callback hb12"),
            ],
            [
                InlineKeyboardButton("Seek",  callback_data="music_callback hb13"),
                InlineKeyboardButton("Song",  callback_data="music_callback hb14"),
                InlineKeyboardButton("Speed", callback_data="music_callback hb15"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_SECTION_INFO_TEXT, reply_markup=keyboard)


@app.on_callback_query(filters.regex("^management$"))
async def management_callback(client: Client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⭐ Extra", callback_data="management_callback extra")],
            [
                InlineKeyboardButton("Ban",    callback_data="management_callback hb1"),
                InlineKeyboardButton("Kick",   callback_data="management_callback hb2"),
                InlineKeyboardButton("Mute",   callback_data="management_callback hb3"),
            ],
            [
                InlineKeyboardButton("Pin",    callback_data="management_callback hb4"),
                InlineKeyboardButton("Staff",  callback_data="management_callback hb5"),
                InlineKeyboardButton("Setup",  callback_data="management_callback hb6"),
            ],
            [
                InlineKeyboardButton("Zombie",    callback_data="management_callback hb7"),
                InlineKeyboardButton("Game",      callback_data="management_callback hb8"),
                InlineKeyboardButton("Imposter",  callback_data="management_callback hb9"),
            ],
            [
                InlineKeyboardButton("Sang Mata",  callback_data="management_callback hb10"),
                InlineKeyboardButton("Translate",  callback_data="management_callback hb11"),
                InlineKeyboardButton("T-Graph",    callback_data="management_callback hb12"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_SECTION_INFO_TEXT, reply_markup=keyboard)


@app.on_callback_query(filters.regex("^tools$"))
async def tools_callback(client: Client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🤖 ChatGPT", callback_data="tools_callback ai")],
            [
                InlineKeyboardButton("Google",    callback_data="tools_callback hb1"),
                InlineKeyboardButton("TTS Voice", callback_data="tools_callback hb2"),
                InlineKeyboardButton("Info",      callback_data="tools_callback hb3"),
            ],
            [
                InlineKeyboardButton("Font",    callback_data="tools_callback hb4"),
                InlineKeyboardButton("Math",    callback_data="tools_callback hb5"),
                InlineKeyboardButton("Tag All", callback_data="tools_callback hb6"),
            ],
            [
                InlineKeyboardButton("Image",    callback_data="tools_callback hb7"),
                InlineKeyboardButton("Hashtag",  callback_data="tools_callback hb8"),
                InlineKeyboardButton("Stickers", callback_data="tools_callback hb9"),
            ],
            [
                InlineKeyboardButton("Fun",     callback_data="tools_callback hb10"),
                InlineKeyboardButton("Quotly",  callback_data="tools_callback hb11"),
                InlineKeyboardButton("TR-DH",   callback_data="tools_callback hb12"),
            ],
            [InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="feature")],
        ]
    )
    await callback_query.message.edit(_SECTION_INFO_TEXT, reply_markup=keyboard)


# ─── About / Info Callbacks ───────────────────────────────────────────────────


@app.on_callback_query(filters.regex("^about$"))
async def about_callback(client: Client, callback_query: CallbackQuery):
    buttons = [
        [
            InlineKeyboardButton("✨ Developer ✨", callback_data="developer"),
            InlineKeyboardButton("⚡ Features ⚡",  callback_data="feature"),
        ],
        [
            InlineKeyboardButton("📓 Basic Guide", callback_data="basic_guide"),
            InlineKeyboardButton("⚜️ Donate",      callback_data="donate"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="go_to_start")],
    ]
    text = (
        f"**Hi, I am {app.mention} ✨**\n\n"
        "**A powerful Telegram group management & music bot that gives you a spam-free and fun environment.**\n\n"
        "● I can restrict users.\n"
        "● I can greet users with customizable welcome messages and set group rules.\n"
        "● I have a music player system.\n"
        "● I support ban, mute, welcome, kick, federation, and many more management features.\n"
        "● I have a note-keeping system, blacklists, and keyword-based auto-replies.\n"
        "● I check admin permissions before executing any command.\n\n"
        "**➻ Click a button below to learn more 🦚**"
    )
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex("^developer$"))
async def developer_callback(client: Client, callback_query: CallbackQuery):
    buttons = [
        [
            InlineKeyboardButton("🔰 Owner",   user_id=config.OWNER_ID[0]),
            InlineKeyboardButton("📍 Sudoers", url=f"https://t.me/{app.username}?start=sudo"),
        ],
        [
            InlineKeyboardButton("🎁 Instagram", url="https://instagram.com/the.vip.boy"),
            InlineKeyboardButton("💲 YouTube",   url="https://youtube.com/@THE_VIP_BOY"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="about")],
    ]
    text = (
        "✦ **This bot is crafted by a skilled developer to make your group easy to manage and more fun.**\n\n"
        "✦ **With just a few clicks, you can control everything — owner settings, sudoers, and explore socials.**\n\n"
        "✦ **Designed for smooth group management and great music. Just use the buttons below!**"
    )
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex("^support$"))
async def support_callback(client: Client, callback_query: CallbackQuery):
    keyboard = [
        [
            InlineKeyboardButton("🎭 Owner",   user_id=config.OWNER_ID[0]),
            InlineKeyboardButton("🌱 GitHub",  url="https://github.com/THE-VIP-BOY-OP"),
        ],
        [
            InlineKeyboardButton("⛅ Group",   url=config.SUPPORT_GROUP),
            InlineKeyboardButton("🎄 Channel", url=config.SUPPORT_CHANNEL),
        ],
        [InlineKeyboardButton("🏠 Home", callback_data="go_to_start")],
    ]
    await callback_query.message.edit_text(
        "**Click a button below to connect with us.**\n\n"
        "**Found a bug or want to give feedback? You're welcome in the support chat (✿◠‿◠)**",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@app.on_callback_query(filters.regex("^donate$"))
async def donate_callback(client: Client, callback_query: CallbackQuery):
    close = [[InlineKeyboardButton("✯ ᴄʟᴏsᴇ ✯", callback_data="close")]]
    caption = (
        "**Support my coding journey by donating to help enhance the bot's features and development.**\n\n"
        "**Your contribution will directly fund innovative, user-friendly tools and exciting bot capabilities.**\n\n"
        "**Simply scan the code and make a payment — no hassle, just a quick way to support new features.**\n\n"
        "**Every donation, big or small, goes a long way in pushing this project forward. Thank you! 🙏**"
    )
    await callback_query.message.reply_photo(
        photo=DONATE_IMG,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(close),
    )


@app.on_callback_query(filters.regex("^basic_guide$"))
async def basic_guide_callback(client: Client, callback_query: CallbackQuery):
    keyboard = [[InlineKeyboardButton("✯ ʙᴀᴄᴋ ✯", callback_data="about")]]
    guide_text = (
        f"**Hey! Here's a quick guide to using {app.mention} 🎉**\n\n"
        "**1.** Click on the **'Add Me To Your Group'** button.\n"
        "**2.** Select your group name.\n"
        "**3.** Grant the bot all necessary permissions for full functionality.\n\n"
        "**To access commands, choose between Music or Management preferences.**\n"
        "**If you still face issues, feel free to reach out for support ✨**"
    )
    await callback_query.message.edit_text(
        text=guide_text, reply_markup=InlineKeyboardMarkup(keyboard)
    )
