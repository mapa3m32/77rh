import json
import base64
import aiohttp
import telethon
from telethon.tl.patched import Message
from telethon.tl import types
from typing import List, Union
from time import gmtime, strftime
from .. import loader, utils

MESSAGE_TYPES = {
    'photo': '📷 Фото',
    'sticker': 'Стикер',
    'video_note': '📹 Видеосообщение',
    'video': '📹 Видео',
    'gif': '🖼 GIF',
    'poll': '📊 Опрос',
    'geo': '📍 Местоположение',
    'contact': '👤 Контакт',
    'voice': lambda msg: f"🎵 Голосовое сообщение: {strftime(msg.voice.attributes[0].duration)}",
    'audio': lambda msg: f"🎧 Музыка: {strftime(msg.audio.attributes[0].duration)} | {msg.audio.attributes[0].performer} - {msg.audio.attributes[0].title}",
    'document': lambda msg: f"💾 Файл: {msg.file.name}"
}


@loader.tds
class ShitQuotesMod(loader.Module):
    async def client_ready(self, client: telethon.TelegramClient, db: dict):
        self.client = client
        self.db = db
        self.api_endpoint = 'https://quotes.fl1yd.su/generate'
        self.settings = self.get_settings()

    async def qcmd(self, message: types.Message):
        return await self.sqcmd(message)

    async def sqcmd(self, message: Message):
        args: List[str] = utils.get_args(message)
        if not await message.get_reply_message():
            return

        isFile = '!file' in args
        [count] = [int(arg) for arg in args if arg.isdigit() and int(arg) > 0] or [1]
        [bg_color] = [arg for arg in args if arg != '!file' and not arg.isdigit()] or [self.settings['bg_color']]

        if count > self.settings['max_messages']:
            return

        payload = {
            'messages': await self.quote_parse_messages(message, count),
            'quote_color': bg_color,
            'text_color': self.settings['text_color']
        }

        if self.settings['debug']:
            file = open('SQuotesDebug.json', 'w')
            json.dump(payload, file, indent=4, ensure_ascii=False)
            await message.respond(file=file.name)

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_endpoint, json=payload) as r:
                if r.status != 200:
                    return

                quote = io.BytesIO(await r.read())
                quote.name = 'SQuote.png' if isFile else 'SQuote.webp'

                await utils.answer(message, quote, force_document=isFile)
        return await message.delete()

    async def quote_parse_messages(self, message: Message, count: int):
        payloads = []
        async for msg in self.client.iter_messages(
            message.chat_id, count, reverse=True, add_offset=1,
            offset_id=(await message.get_reply_message()).id,
        ):
            avatar = rank = reply_id = reply_name = reply_text = None
            entities = self.get_entities(msg.entities)

            if msg.fwd_from:
                if msg.fwd_from.from_id:
                    user_id = msg.fwd_from.from_id.channel_id if isinstance(msg.fwd_from.from_id, types.PeerChannel) else msg.fwd_from.from_id.user_id
                    try:
                        user = await self.client.get_entity(user_id)
                    except Exception:
                        name, avatar = await self.get_profile_data(msg.sender)
                        return (
                            'Вот блин, произошла ошибка. Возможно на этом канале тебя забанили, и невозможно получить информацию.',
                            None, msg.sender.id, name, avatar, 'ошибка', None, None, None, None
                        )
                    name, avatar = await self.get_profile_data(user)
                    user_id = user.id
                elif msg.fwd_from.from_name:
                    user_id = msg.chat_id
            else:
                if reply := await msg.get_reply_message():
                    reply_id = reply.sender.id
                    reply_name = telethon.utils.get_display_name(reply.sender)
                    reply_text = self.get_message_text(reply, True) + (
                        '\n' + reply.raw_text
                        if reply.raw_text and self.get_message_text(reply, True)
                        else reply.raw_text or ''
                    )

                user = await self.client.get_entity(msg.sender)
                name, avatar = await self.get_profile_data(user)
                user_id = user.id

                if msg.is_group and msg.is_channel:
                    admins = await self.client.get_participants(msg.chat_id, filter=types.ChannelParticipantsAdmins)
                    if user in admins:
                        admin = admins[admins.index(user)].participant
                        rank = admin.rank or ('creator' if isinstance(admin, types.ChannelParticipantCreator) else admin)

            media = await self.client.download_media(self.get_message_media(msg), bytes, thumb=-1)
            media = base64.b64encode(media).decode() if media else None

            via_bot = msg.via_bot.username if msg.via_bot else None
            text = ((msg.raw_text or '') + (
                ('\n' + self.get_message_text(msg))
                if msg.raw_text
                else self.get_message_text(msg)
            ) if self.get_message_text(msg) else '')

            payloads.append(
                {
                    'text': text,
                    'media': media,
                    'entities': entities,
                    'author': {
                        'id': user_id,
                        'name': name,
                        'avatar': avatar,
                        'rank': rank or '',
                        'via_bot': via_bot
                    },
                    'reply': {
                        'id': reply_id,
                        'name': reply_name,
                        'text': reply_text
                    }
                }
            )

        return payloads

    async def qfcmd(self, message: Message):
        args: str = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        await message.delete()

        try:
            payload = await self.fakequote_parse_messages(args, reply)
        except (IndexError, ValueError):
            return

        if len(payload) > self.settings['max_messages']:
            return

        payload = {
            'messages': payload,
            'quote_color': self.settings['bg_color'],
            'text_color': self.settings['text_color']
        }

        if self.settings['debug']:
            file = open('SQuotesDebug.json', 'w')
            json.dump(payload, file, indent=4, ensure_ascii=False)
            await message.respond(file=file.name)

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_endpoint, json=payload) as r:
                if r.status != 200:
                    return await message.delete()

        quote = io.BytesIO(await r.read())
        quote.name = 'SQuote.webp'

    async def fakequote_parse_messages(self, args: str, reply: Message):
        async def get_user(args: str):
            args_, text = args.split(), ''
            user = await self.client.get_entity(
                int(args_[0]) if args_[0].isdigit() else args_[0])

            if len(args_) > 1:
                user = await self.client.get_entity(
                    int(args) if args.isdigit() else args)
            else:
                text = args.split(maxsplit=1)[1]
            return user, text

        if reply or (reply and args):
            user = reply.sender
            name, avatar = await self.get_profile_data(user)
            text = args or ''

        else:
            messages = []
            for part in args.split(';'):
                user, text = await get_user(part)
                name, avatar = await self.get_profile_data(user)
                reply_id = reply_name = reply_text = None

                if '-r' in part:
                    user, text = await get_user(''.join(part.split('-r')[0]))
                    user2, text2 = await get_user(''.join(part.split('-r')[1]))

                    name, avatar = await self.get_profile_data(user)
                    name2, _ = await self.get_profile_data(user2)

                    reply_id = user2.id
                    reply_name = name2
                    reply_text = text2

                messages.append(
                    {
                        'text': text,
                        'media': None,
                        'entities': None,
                        'author': {
                            'id': user.id,
                            'name': name,
                            'avatar': avatar,
                            'rank': ''
                        },
                        'reply': {
                            'id': reply_id,
                            'name': reply_name,
                            'text': reply_text
                        }
                    }
                )
            return messages

        return [
            {
                'text': text,
                'media': None,
                'entities': None,
                'author': {
                    'id': user.id,
                    'name': name,
                    'avatar': avatar,
                    'rank': ''
                },
                'reply': {
                    'id': None,
                    'name': None,
                    'text': None
                }
            }
        ]

    async def get_profile_data(self, user: types.User):
        avatar = await self.client.download_profile_photo(user.id, bytes)
        return telethon.utils.get_display_name(user), base64.b64encode(avatar).decode() if avatar else None

    async def sqsetcmd(self, message: Message):
        args: List[str] = utils.get_args_raw(message).split(maxsplit=1)
        if not args:
            return await utils.answer(
                message,
                f'Настройки\n'
                f'Максимум сообщений (max_messages) {self.settings["max_messages"]}\n'
                f'Цвет квоты (bg_color) {self.settings["bg_color"]}\n'
                f'Цвет текста (text_color) {self.settings["text_color"]}\n'
                f'Дебаг (debug) {self.settings["debug"]}\n\n'
                f'Настроить можно с помощью .sqset параметр значение или .sqset reset'
            )

        if args[0] == 'reset':
            self.get_settings(True)
            return await utils.answer(
                message, 'Настройки квот были сброшены')

        if len(args) < 2:
            return await utils.answer(
                message, 'Недостаточно аргументов')

        mods = ['max_messages', 'bg_color', 'text_color', 'debug']
        if args[0] not in mods:
            return await utils.answer(
                message, f'Такого параметра нет, есть: {", ".join(mods)}')

        elif args[0] == 'debug':
            if args[1].lower() not in ['true', 'false']:
                return await utils.answer(
                    message, 'Такого значения параметра нет, есть: true, false')
            self.settings[args[0]] = args[1].lower() == 'true'

        elif args[0] == 'max_messages':
            if not args[1].isdigit():
                return await utils.answer(
                    message, 'Это не число')
            self.settings[args[0]] = int(args[1])

        else:
            self.settings[args[0]] = args[1]

        self.db.set('SQuotes', 'settings', self.settings)
        return await utils.answer(
            message, f'Значение параметра {args[0]} было выставлено на {args[1]}')

    def get_settings(self, force: bool = False):
        settings: dict = self.db.get('SQuotes', 'settings', {})
        if not settings or force:
            settings.update(
                {
                    'max_messages': 15,
                    'bg_color': '#162330',
                    'text_color': '#fff',
                    'debug': False
                }
            )
            self.db.set('SQuotes', 'settings', settings)

        return settings
