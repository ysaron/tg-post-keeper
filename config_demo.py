from enum import Enum
import logging
from datetime import datetime
from telebot import logger

TOKEN = 'Paste your token here'
ADMIN_ID = 0    # Paste your user id here

DB_FILE = 'your_database_name.db'


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
<b>PostSorterBot</b> <code>v1.3</code>\n
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
6. Просматривать записи можно с помощью:
       ► команды /look;
       ► кнопки "Мои записи"
   <b>так же</b>, как и категорию HELP.
"""
    HELP_NEWS = """
<b>🔆 Последние обновления 🔆</b>
► Возможность отменить добавленный комментарий при сохранении поста
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
    {'message_text': DefaultText.HELP_NEWS,
     'caption': None,
     'attach_type': 'text',
     'att_photo': '',
     'att_video': '',
     'att_document': '',
     'ffc_title': 'Posts Keeper',
     'ffc_username': 'PostSorterBot',
     'category': 'HELP'},
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


class Replies:
    POST_CONTROL = 'Управление постом:'
    CATEGORY_NAME = 'Введите имя для новой категории (не более <b>20</b> символов)'
    CANCEL_REMOVAL = 'Удаление отменено.'
    CANCEL_RENAME = 'Переименование отменено.'
    CANCEL = 'ОТМЕНЕНО'
    CANCEL_ASSEMBLING = 'Сборка поста <b>отменена</b>.'
    COMMENT_REMOVED = 'Комментарий удален.'
    POST_REMOVED = '✅ Пост был <b>удален</b>'
    POST_REPLACED = 'Пост был перемещен.'
    POST_ASSIGNED = 'Посту присвоена категория '
    MAIN_MENU_RET = 'Вы вернулись в главное меню.'
    UNKNOWN = 'Непонятное сообщение.\nВозвращаемся в главное меню...\nПутеводитель по командам: /help'
    START = '<b>Вы находитесь в главном меню.</b>\n► /help — узнать, как работать с ботом.'
    HELP_UPDATED = 'Категория HELP была массово обновлена. /help'
    PART_RECEIVED_YES = 'Получено ✅'
    PART_RECEIVED_NO = 'Кажется, уже пора нажимать /assemble'
    NO_TEMP = 'Чтобы сохранить что-то, нужно сначала это что-то мне отправить ☝️'
    CAPTION_TOO_LONG = '❌ Недопустимая длина подписи вложения.'
    COMMENT_RETRY = 'Не удалось обработать комментарий. Попробуй еще ' \
                    '(или /start для отмены и возвращения в главное меню).'
    CHOOSE_CATEGORY = 'Выбери категорию из доступных:'
    HANDLE_CATEGORY_ERROR = '❌ Не-не-не. Нужно нажать кнопку с категорией.'
    DEL_CATEGORY_FAIL = '❌ Не удалось удалить категорию.'
    REN_CATEGORY_FAIL = '❌ Не удалось переименовать категорию.'
    DEL_POST_WARNING = 'Удалить эту запись?'
    CATEGORIES_ACTION_DEL = 'Выберите категорию для удаления:'
    CATEGORIES_ACTION_REN = 'Выберите категорию для переименования:'
    CATEGORIES_ACTION_REPL = 'Выберите категорию для перемещения:'
    CATEGORIES_ACTION_LOOK = 'Выберите категорию для просмотра:'
    NO_POSTS = '❎ В выбранной категории сейчас нет ни одного поста.'

    # Сообщения для последующего форматирования .format()
    CONFIRM_POST_ = '✅ Пост сохранен в категории <code>{}</code>'
    DELETE_WARNING_ = 'Удалить категорию <code>{}</code> и все ее посты ({})?\n❗️<b><i>Это действие необратимо.</i></b>'
    DELETED_CATEGORY_ = '✅ Категория <code>{}</code> удалена, как и все ее посты.'
    NEW_CATEGORY_NAME_ = 'Введи новое название для категории <code>{}</code>'
    RENAMED_CATEGORY_ = '✅ Категория <code>{}</code> была переименована.'
    ADDED_CATEGORY_YES_ = '✅ Успешно добавлена категория <code>{}</code>'
    ADDED_CATEGORY_NO_ = '❌ Категория <code>{}</code> не была добавлена.'


def time_it(func):
    """ Логирование времени выполнения любой функции """

    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        delta = (datetime.now() - start).microseconds
        ps_logger.info(f'EXECUTION {func.__module__}.{func.__name__}: {delta / 1000} ms')
        return result

    return wrapper
