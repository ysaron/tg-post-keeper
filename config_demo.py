from enum import Enum
import logging
from telebot import logger

TOKEN = 'Paste your token here'

DB_FILE = 'your_database_name.db'


class Storages:
    STATEFILE = 'temp_storage_filename_1.vdb'
    RECORDS = 'temp_storage_filename_2.vdb'
    CURRENT_RECORD = 'temp_storage_filename_3.vdb'
    CAROUSEL = 'temp_storage_filename_4.vdb'
    RECORD_LENGTH = 'temp_storage_filename_5.vdb'
    CATEGORY = 'temp_storage_filename_6.vdb'


class DefaultText:
    HELP_COMMANDS = """
<b>Список всех команд, которые могут тебе понадобиться:</b>\n
► /start или /cancel 
<i>Экстренный возврат в главное меню.</i>\n
► /help 
<i>...</i>\n
► /newcategory 
<i>Создание кастомной категории для хранения записей.</i>\n
► /delete 
<i>Выбор категории для полного и окончательного удаления (уничтожения, стирания, низведения до атомов).</i>\n
► /rename 
<i>Выбор категории для переименования.</i>\n
► /assemble 
<i>Начало сборки поста.</i>\n
► /look 
<i>Просмотр сохраненных записей.</i>\n
<b>Подробнейшие инструкции по эксплуатации бота — на следующей странице.</b>
"""
    HELP_GREETINGS = """
<b>PostSorterBot</b> <code>v0.9</code>\n
Привет!\nЭтот бот умеет сохранять сообщения Telegram в отдельных категориях, удобных для просмотра.
Листай вправо, чтобы ознакомиться с доступными командами.
"""
    HELP_MEDIA = """
<b>❕ Как использовать бота ❕</b>\n
1. Вернись в главное меню бота ("Закрыть" или /start).
2. Создай пару новых категорий (/newcategory).
3. Отправь любое сообщение, которое хочешь сохранить.
    <i>Поддерживаемые типы сообщений:
       ► от тебя;
       ► пересланное от пользователя;
       ► пересланное из канала.</i>
     <i>Поддерживаемые вложения:
       ► фото;
       ► видео;
       ► документы;
       ► альбомы из вышеперечисленных вложений.</i>
4. Нажми кнопку с командой /assemble.
5. Выбери категорию, в которую нужно сохранить запись, и (опционально) добавь комментарий от себя.
6. Просматривать записи можно с помощью команды /look <b>так же</b>, как и категорию HELP.
"""


DEFAULT_CATEGORIES = ['HELP', 'См. позже', 'Дела']
HELP_POSTS = [
    {'message_text': None,
     'caption': DefaultText.HELP_GREETINGS,
     'attach_type': 'photo',
     'att_photo': 'AgACAgIAAxkBAAIPZGBB5k6deEChEao5Sb3MA5Yfw7GxAALTsTEbZ4cJSo8q9vz0iiL_QSlAni4AAwEAAwIAA3gAA8DpAAIeBA',
     'att_video': '',
     'att_document': '',
     'ffc_title': 'Posts Keeper',
     'ffc_username': 'PostSorterBot',
     'category': 'HELP'},
    {'message_text': DefaultText.HELP_COMMANDS,
     'caption': None,
     'attach_type': 'text',
     'att_photo': '',
     'att_video': '',
     'att_document': '',
     'ffc_title': 'Posts Keeper',
     'ffc_username': 'PostSorterBot',
     'category': 'HELP'},
    {'message_text': None,
     'caption': DefaultText.HELP_MEDIA,
     'attach_type': 'media_group',
     'att_photo': 'AgACAgIAAxkBAAIPZGBB5k6deEChEao5Sb3MA5Yfw7GxAALTsTEbZ4cJSo8q9vz0iiL_QSlAni4AAwEAAwIAA3gAA8DpAAIeBA,'
                  'AgACAgIAAxkBAAIPZGBB5k6deEChEao5Sb3MA5Yfw7GxAALTsTEbZ4cJSo8q9vz0iiL_QSlAni4AAwEAAwIAA3gAA8DpAAIeBA,'
                  'AgACAgIAAxkBAAIPZGBB5k6deEChEao5Sb3MA5Yfw7GxAALTsTEbZ4cJSo8q9vz0iiL_QSlAni4AAwEAAwIAA3gAA8DpAAIeBA',
     'att_video': '',
     'att_document': '',
     'ffc_title': 'Posts Keeper',
     'ffc_username': 'PostSorterBot',
     'category': 'HELP'},
    {'message_text': None,
     'caption': None,
     'attach_type': 'video',
     'att_photo': '',
     'att_video': 'BAACAgIAAxkBAAIQcWBDQE-uYzscngGR9mJhaVwNPdhgAAKpCAACIXLpSCYXiZjU3xjvHgQ',
     'att_document': '',
     'ffc_title': 'Posts Keeper',
     'ffc_username': 'PostSorterBot',
     'category': 'Дела'}
]

# Настройка логов
ps_logger = logger
logger.setLevel(logging.INFO)

info_handler = logging.FileHandler('logs/info.log', encoding='utf-8')
err_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
info_handler.setLevel(logging.INFO)
err_handler.setLevel(logging.ERROR)

line = f'\n{"-" * 120}\n'
info_format = logging.Formatter('%(asctime)s %(levelname)s|%(name)s.py | %(message)s' + line,
                                datefmt='%d.%m.%Y %H:%M:%S')
err_format = logging.Formatter('%(asctime)s %(levelname)s|%(name)s.py | %(message)s' + line,
                               datefmt='%d.%m.%Y %H:%M:%S')
info_handler.setFormatter(info_format)
err_handler.setFormatter(err_format)

ps_logger.addHandler(info_handler)
ps_logger.addHandler(err_handler)


class States(Enum):
    """ Перечисление рабочих режимов диалога с юзером """
    NULL = '0'
    DEFAULT = '1'
    CATEGORY_NAME = '2'
    ASSEMBLE = '3'
    COMMENT = '4'
    CATEGORY = '5'
    LOOK = '6'
    DELETE = '7'
    RENAME = '8'
    NEW_CATEGORY_NAME = '9'
    DELETE_POST = '10'
    REPLACE_POST = '11'
