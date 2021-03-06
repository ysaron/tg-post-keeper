import telebot
from telebot.types import Message, CallbackQuery
import random

import fsm
import core
from frame import Response
import config
from config import States

bot = telebot.TeleBot(token=config.TOKEN, parse_mode='HTML')

# Словарь для обмена данными между модулями / функциями
data = {
    'success': None,
    'category': None,
    'state': States.DEFAULT.value,
    'post': None,
    'user': None,
    'mode': '',
    'position': '-'
}


@bot.message_handler(commands=['start', 'cancel'])
def cmd_start(message: Message):
    """ Переход/возврат в дефолтное состояние """
    fsm.set_state(user_id=message.chat.id, value=States.DEFAULT.value)
    response = core.start_handler(message=message)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(commands=['help'])
def cmd_help(message: Message):
    """  """
    fsm.set_state(user_id=message.chat.id, value=States.LOOK.value)
    response = core.help_handler(message, data)
    send_post(message, response, carousel=True)
    carousel_ids = core.define_carousel_ids(message, response)
    fsm.write_carousel_id(message.chat.id, carousel_ids)
    bot.send_message(chat_id=message.chat.id, text='Управление постом:', reply_markup=response.keyboard)


@bot.message_handler(commands=['newcategory'],
                     func=lambda message: fsm.get_current_state(message.chat.id) in [States.DEFAULT.value,
                                                                                     States.LOOK.value])
def new_category(message: Message):
    """ Обработка команды /newcategory """
    if fsm.get_current_state(message.chat.id) == States.LOOK.value:
        delete_posts(message=message, ids=[fsm.get_carousel_id(message.chat.id)[-1]])
        fsm.write_carousel_id(message.chat.id, [0])
    fsm.set_state(user_id=message.chat.id, value=States.CATEGORY_NAME.value)
    bot.send_message(chat_id=message.chat.id, text='Введите имя для новой категории (не более <b>20</b> символов)')


@bot.message_handler(content_types=['text'],
                     func=lambda message: fsm.get_current_state(message.chat.id) == States.CATEGORY_NAME.value)
def add_category(message: Message):
    """ Получен текст-название новой категории """
    new_state = States.DEFAULT.value
    fsm.set_state(user_id=message.chat.id, value=new_state)
    data['state'] = new_state
    response = core.add_category_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(commands=['delete'],
                     func=lambda message: fsm.get_current_state(message.chat.id) in [States.DEFAULT.value,
                                                                                     States.LOOK.value])
def choose_category_delete(message: Message):
    """  """
    if fsm.get_current_state(message.chat.id) == States.LOOK.value:
        delete_posts(message=message, ids=[fsm.get_carousel_id(message.chat.id)[-1]])
        fsm.write_carousel_id(message.chat.id, [0])
    fsm.set_state(user_id=message.chat.id, value=States.DELETE.value)
    data['mode'] = 'delete'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    fsm.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.DELETE.value)
def delete_category(call: CallbackQuery):
    """  """
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text='Удаление отменено.')
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
        fsm.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    elif call.data == 'confirm':
        data['category'] = fsm.get_current_category(call.from_user.id)
        fsm.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
        response = core.delete_category(call.message, data=data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
    else:
        data['category'] = call.data
        response = core.delete_category_warn(call.message, data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        fsm.write_carousel_id(user_id=call.message.chat.id, carousel_ids=[call.message.message_id + 1])


@bot.message_handler(commands=['rename'],
                     func=lambda message: fsm.get_current_state(message.chat.id) in [States.DEFAULT.value,
                                                                                     States.LOOK.value])
def choose_category_rename(message: Message):
    """  """
    if fsm.get_current_state(message.chat.id) == States.LOOK.value:
        delete_posts(message=message, ids=[fsm.get_carousel_id(message.chat.id)[-1]])
        fsm.write_carousel_id(message.chat.id, [0])
    fsm.set_state(user_id=message.chat.id, value=States.RENAME.value)
    data['mode'] = 'rename'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    fsm.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.RENAME.value)
def new_category_name(call: CallbackQuery):
    """  """
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text='Переименование отменено.')
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
        fsm.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    else:
        data['category'] = call.data
        response = core.choose_new_category_name(call.message, data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        fsm.write_carousel_id(user_id=call.message.chat.id, carousel_ids=[call.message.message_id + 1])
        fsm.set_state(user_id=call.from_user.id, value=States.NEW_CATEGORY_NAME.value)


@bot.callback_query_handler(func=
                            lambda call: fsm.get_current_state(call.from_user.id) == States.NEW_CATEGORY_NAME.value)
def new_category_name_cancel(call: CallbackQuery):
    """  """
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text='Переименование отменено.')
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
        fsm.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию


@bot.message_handler(content_types=['text'],
                     func=lambda message: fsm.get_current_state(message.chat.id) == States.NEW_CATEGORY_NAME.value)
def rename_category(message: Message):
    """  """
    data['category'] = fsm.get_current_category(message.chat.id)
    response = core.rename_category(message, data)
    delete_posts(message=message, ids=fsm.get_carousel_id(message.chat.id))
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    fsm.write_current_category(message.chat.id, category='')  # Забыть текущую категорию
    fsm.set_state(user_id=message.chat.id, value=States.DEFAULT.value)


@bot.message_handler(commands=['assemble'],
                     func=lambda message: fsm.get_current_state(message.chat.id) == States.DEFAULT.value)
def assemble_post(message: Message):
    """ Обработка команды сборки ранее отправленного поста """
    response = core.assemble_post_handler(message, data)

    fsm.set_state(user_id=message.chat.id, value=States.ASSEMBLE.value)
    send_post(message, response)


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.ASSEMBLE.value)
def setup_post(call: CallbackQuery):
    """ Обработка коллбэк-кнопок в режиме сборки поста """
    if call.data == 'category':
        fsm.set_state(user_id=call.from_user.id, value=States.CATEGORY.value)
        response = core.choose_category(message=call.message, data=data)
        bot.send_message(chat_id=call.from_user.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'comment':
        fsm.set_state(user_id=call.from_user.id, value=States.COMMENT.value)
        response = core.await_comment(call.message, data)
        bot.send_message(chat_id=call.from_user.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'cancel':
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
        core.cancel_assemble(call.message)
        bot.send_message(chat_id=call.message.chat.id, text='Сборка поста <b>отменена</b>.')
    elif call.data == 'del_comment':
        pass  # отправить None в поле comment, снова отправить весь этот повторяющийся блок (запихнуть уже в функцию)
    elif call.data == 'confirm':
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
        response = core.confirm_post(message=call.message, data=data)
        bot.send_message(chat_id=call.message.chat.id, text=response.text)


@bot.message_handler(content_types=['text'],
                     func=lambda message: fsm.get_current_state(message.chat.id) == States.COMMENT.value)
def accept_comment(message: Message):
    """ Обработка текста-комментария к собираемому посту """
    fsm.set_state(user_id=message.chat.id, value=States.ASSEMBLE.value)
    response = core.handle_comment(message, data)
    send_post(message, response)


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.CATEGORY.value)
def accept_category(call: CallbackQuery):
    """ Присвоение собираемому посту выбранной категории """
    fsm.set_state(user_id=call.message.chat.id, value=States.ASSEMBLE.value)
    response = core.handle_category(call, data)
    send_post(call.message, response)


@bot.message_handler(commands=['look'],
                     func=lambda message: fsm.get_current_state(message.chat.id) in [States.DEFAULT.value,
                                                                                     States.LOOK.value])
def look_categories(message: Message):
    """ Просмотр сохраненных записей; отправляем редактируемое сообщение с категориями-кнопками """
    if fsm.get_current_state(message.chat.id) == States.LOOK.value:
        delete_posts(message=message, ids=[fsm.get_carousel_id(message.chat.id)[-1]])
        fsm.write_carousel_id(message.chat.id, [0])
    fsm.set_state(user_id=message.chat.id, value=States.LOOK.value)
    data['mode'] = 'look'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    fsm.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.LOOK.value)
def look_records(call: CallbackQuery):
    """ Просмотр постов выбранной категории """
    if call.data == 'add_category':
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        fsm.set_state(user_id=call.message.chat.id, value=States.CATEGORY_NAME.value)
        bot.send_message(chat_id=call.message.chat.id, text='Введите имя новой категории (не более <b>20</b> символов)')
    elif call.data == 'prev' or call.data == 'next':
        response = core.carousel_handler(call, data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        fsm.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Управление постом:', reply_markup=response.keyboard)
    elif call.data == 'pass':  # Нажата холостая кнопка
        pass
    elif call.data == 'cancel':
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        bot.send_message(chat_id=call.message.chat.id, text='Вы вернулись в главное меню.')
        fsm.set_state(user_id=call.from_user.id, value=States.DEFAULT.value)
    elif call.data == 'remove':
        fsm.set_state(user_id=call.from_user.id, value=States.DELETE_POST.value)
        response = core.delete_post_warn(call.message, data)
        bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                              message_id=fsm.get_carousel_id(call.from_user.id)[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=fsm.get_carousel_id(call.from_user.id)[-1])
    elif call.data == 'replace':
        fsm.set_state(user_id=call.from_user.id, value=States.REPLACE_POST.value)
        data['mode'] = 'replace'
        response = core.look_handler(call.message, data)
        bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                              message_id=fsm.get_carousel_id(call.from_user.id)[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=fsm.get_carousel_id(call.from_user.id)[-1])
    else:
        data['category'] = call.data
        response = core.look_records_handler(message=call.message, data=data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        fsm.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Управление постом:', reply_markup=response.keyboard)


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.DELETE_POST.value)
def delete_post_from_category(call: CallbackQuery):
    """ Обработка подтверждения удаления поста """
    if call.data == 'confirm':
        response = core.delete_post(call.message, data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        fsm.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='✅ Пост был <b>удален</b>', reply_markup=response.keyboard)
    elif call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        bot.edit_message_text(text='Управление постом:', chat_id=call.message.chat.id,
                              message_id=fsm.get_carousel_id(call.from_user.id)[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=fsm.get_carousel_id(call.from_user.id)[-1])
    fsm.set_state(user_id=call.from_user.id, value=States.LOOK.value)


@bot.callback_query_handler(func=lambda call: fsm.get_current_state(call.from_user.id) == States.REPLACE_POST.value)
def replace_post(call: CallbackQuery):
    """ Обработка выбора другой категории для поста """
    if call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        bot.edit_message_text(text='Управление постом:', chat_id=call.message.chat.id,
                              message_id=fsm.get_carousel_id(call.from_user.id)[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=fsm.get_carousel_id(call.from_user.id)[-1])
    else:
        data['category'] = call.data
        response = core.replace_post(call.message, data)
        delete_posts(message=call.message, ids=fsm.get_carousel_id(call.from_user.id))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        fsm.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Пост был перемещен', reply_markup=response.keyboard)
    fsm.set_state(user_id=call.from_user.id, value=States.LOOK.value)


@bot.message_handler(content_types=['text', 'document', 'photo', 'video'],
                     func=lambda message: fsm.get_current_state(message.chat.id) == States.DEFAULT.value)
def new_record(message: Message):
    """ Обработка всего в дефолтном состоянии, кроме определенных команд, как новой записи в базе """
    response = core.record_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(content_types=['text', 'document', 'photo', 'video'])
def any_msg(message: Message):
    """ Обработка всего, что не было обработано другими хэндлерами, как неизвестной команды """
    help_msg = 'Непонятное сообщение.\nВозвращаемся в главное меню...\nПутеводитель по командам: /help'
    bot.send_message(chat_id=message.chat.id, text=help_msg)
    fsm.set_state(user_id=message.chat.id, value=States.DEFAULT.value)


def send_post(message: Message, response: Response, carousel=False):
    """ Оболочка для различных способов отправки сообщений ботом в зависимости от типа поста """
    kb = response.keyboard if not carousel else None
    if response.flag == 'text':
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=kb)
    elif response.flag == 'photo':
        bot.send_photo(chat_id=message.chat.id, photo=response.attachment[0], caption=response.text,
                       reply_markup=kb)
    elif response.flag == 'video':
        bot.send_video(chat_id=message.chat.id, data=response.attachment[0], caption=response.text,
                       reply_markup=kb)
    elif response.flag == 'document':
        bot.send_document(chat_id=message.chat.id, data=response.attachment[0], caption=response.text,
                          reply_markup=kb)
    elif response.flag == 'media_group':
        bot.send_media_group(chat_id=message.chat.id, media=response.attachment)
        if not carousel:
            bot.send_message(chat_id=message.chat.id, text='Управление постом:', reply_markup=response.keyboard)
    elif response.flag == 'no_records':
        fsm.set_state(user_id=message.chat.id, value=States.DEFAULT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=kb)
    elif response.flag == 'error1':
        fsm.set_state(user_id=message.chat.id, value=States.COMMENT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)
    elif response.flag == 'error2':
        fsm.set_state(user_id=message.chat.id, value=States.CATEGORY.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)


def delete_posts(message: Message, ids: list):
    """ удаляет все посты с id из списка """
    for i in ids:
        try:
            bot.delete_message(message.chat.id, message_id=i)
        except Exception as e:
            raise e


if __name__ == '__main__':
    random.seed()
    bot.polling()  # после отладки изменить на bot.infinity_polling()
