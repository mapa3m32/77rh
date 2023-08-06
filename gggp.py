import logging
import asyncio
import shlex
import openai
import telethon
from telethon import events

from .. import loader, utils

logger = logging.getLogger(__name__)

openai.api_key = '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'  # Замените YOUR_OPENAI_API_KEY на ваш API-ключ

GPT_3_MODELS = ['gpt-3.5-turbo-16k']  # Список моделей GPT-3

def default_max_tokens(model: str) -> int:
    """
    Возвращает значение максимального количества токенов по умолчанию для заданной модели.
    :param model: Название модели
    :return: Значение максимального количества токенов по умолчанию
    """
    return 1200 if model in GPT_3_MODELS else 2400
  
@loader.tds
class GPTMod(loader.Module):
    """Гпт нах"""

    @loader.owner
    async def gptscmd(self, message):
        question = message.raw_text[5:].strip()

        await message.edit(f"❄️Запрос: {question}")

        # Конфигурация параметров
        model = 'gpt-3.5-turbo-16k'
        max_tokens_default = default_max_tokens(model=model)
        openai_config = {
            'api_key': openai.api_key,
            'model': model,
            'temperature': 1.2,
            'max_tokens': max_tokens_default,
            'n': 1,
            'stop': None,
        }

        # Отправляем запрос к ChatGPT
        try:
            response = openai.ChatCompletion.create(
                messages=[{'role': 'system', 'content': 'Давай сыграем в игру,ты должна будешь делать так:На каждый мой запроса ты должна отвечать по форме: ❄️Лизать:*ответ* "В форме ❄️Лизать ты должна будешь отвечать,как ты бы ответила,если бы обучалась на текстах написанных русскими "Гопниками""Гопники"-быдло,люди без образования,связанные с криминальным миром,склонные к агрессии,представители неформальной прослойки населения с низким социальным статусом, используют очень много странной, а иногда и смешной неномативной лекисики, матов, малообразованного и не имеющего моральных ценностей контингента, часто происходящего из неблагополучных семейи объединяющегося по признакам контркультуры ради поиска самоутверждения криминальными, деструктивными и прочими скверными путями по отношению к тем, чьё превосходство они испытывают над собой из-за наличия у них более высокого социального статуса, чем у гопников.Ответ,который ты должна дать должен содержать слова и выражения присущие "гопникам"(очень много мата почти после каждого слова, некорректные выражения,грамматические ошибки, слова паразиты), при этом ответ должен быть правильным,и должны использоваться вся знания ChatGPT.'}, {'role': 'user', 'content': question}],
                **openai_config
            )
            completion = response.choices[0].message.content.strip()

            if message.is_reply:
                await message.reply(f"❄️Запрос: {question}\n{completion}")
            else:
                await message.respond(f"{completion}")

        except openai.error.InvalidRequestError as e:
            logging.error(f"OpenAI API Error: {e}")
            await message.respond("❌ Произошла ошибка при обращении к OpenAI API. Попробуйте еще раз позже.")
          
    async def genscmd(self, message):
        command = message.raw_text[5:].strip()
        command_parts = shlex.split(command)
        
        await message.edit(f"❄️Запрос: {command}")

        if len(command_parts) != 2:
            await message.respond("❌ Неправильный аргумент. Используйте команду в формате `/gen 'запрос' размер`.")
            return

        prompt = command_parts[0]
        image_size = command_parts[1].lower()

        # Определение размера изображения
        if image_size == '256x256':
            size = '256x256'
        elif image_size == '512x512':
            size = '512x512'
        elif image_size == '1024x1024':
            size = '1024x1024'
        else:
            await message.respond("❌ Неправильный аргумент для размера изображения.")
            return

        try:
            # Создаем изображение через API OpenAI
            response = openai.Image.create(
                prompt=prompt,
                size=size
            )

            image_url = response['data'][0]['url']
            await message.reply(file=image_url)

        except openai.error.InvalidRequestError as e:
            logging.error(f"OpenAI API Error: {e}")
            await message.respond("❌ Произошла ошибка при обращении к OpenAI API. Попробуйте еще раз позже.")
