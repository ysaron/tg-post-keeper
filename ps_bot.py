import telebot
from telebot.types import Message, CallbackQuery, ReplyKeyboardRemove
import random

from sqler import SqlWorker as SqW
import core
from frame import Response
import config
from config import States, time_it

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
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)
    response = core.start_handler(message=message)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(commands=['help'])
def cmd_help(message: Message):
    """  """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.LOOK.value)
    response = core.help_handler(message, data)
    send_post(message, response, carousel=True)
    carousel_ids = core.define_carousel_ids(message, response)
    base.write_carousel_id(user_id=message.chat.id, carousel_ids=carousel_ids)
    bot.send_message(chat_id=message.chat.id, text='Управление постом:', reply_markup=response.keyboard)


@bot.message_handler(commands=['update'], func=lambda message: message.chat.id == config.ADMIN_ID)
def cmd_update(message: Message):
    """ Обработка команды от админа - обновление информации о боте """
    response = core.update(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    commands=['newcategory'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] in [States.DEFAULT.value,
                                                                                          States.LOOK.value]
)
def new_category(message: Message):
    """ Обработка команды /newcategory """
    base = SqW(config.DB_FILE)
    if base.get_user_state(message.chat.id)['state'] == States.LOOK.value:
        delete_posts(message=message, ids=[base.get_user_state(message.chat.id)['carousel_id'].split(',')[-1]])
        base.write_carousel_id(message.chat.id, [0])
    base.set_state(user_id=message.chat.id, state=States.CATEGORY_NAME.value)
    bot.send_message(chat_id=message.chat.id, text='Введите имя для новой категории (не более <b>20</b> символов)')


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.CATEGORY_NAME.value)
def add_category(message: Message):
    """ Получен текст-название новой категории """
    base = SqW(config.DB_FILE)
    new_state = States.DEFAULT.value
    base.set_state(user_id=message.chat.id, state=new_state)
    data['state'] = new_state
    response = core.add_category_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    commands=['delete'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] in [States.DEFAULT.value,
                                                                                          States.LOOK.value]
)
def choose_category_delete(message: Message):
    """  """
    base = SqW(config.DB_FILE)
    if base.get_user_state(message.chat.id)['state'] == States.LOOK.value:
        delete_posts(message=message, ids=[base.get_user_state(message.chat.id)['carousel_id'].split(',')[-1]])
        base.write_carousel_id(message.chat.id, [0])
    base.set_state(user_id=message.chat.id, state=States.DELETE.value)
    data['mode'] = 'delete'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    base.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.DELETE.value
)
def delete_category(call: CallbackQuery):
    """  """
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text='Удаление отменено.')
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
        base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    elif call.data == 'confirm':
        data['category'] = base.get_user_state(call.from_user.id)['current_category']
        base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
        response = core.delete_category(call.message, data=data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
    else:
        data['category'] = call.data
        response = core.delete_category_warn(call.message, data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        base.write_carousel_id(user_id=call.message.chat.id, carousel_ids=[call.message.message_id + 1])


@bot.message_handler(
    commands=['rename'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] in [States.DEFAULT.value,
                                                                                          States.LOOK.value]
)
def choose_category_rename(message: Message):
    """  """
    base = SqW(config.DB_FILE)
    if base.get_user_state(message.chat.id)['state'] == States.LOOK.value:
        delete_posts(message=message, ids=[base.get_user_state(message.chat.id)['carousel_id'].split(',')[-1]])
        base.write_carousel_id(message.chat.id, [0])
    base.set_state(user_id=message.chat.id, state=States.RENAME.value)
    data['mode'] = 'rename'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    base.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.RENAME.value
)
def new_category_name(call: CallbackQuery):
    """  """
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text='Переименование отменено.')
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
        base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    else:
        data['category'] = call.data
        response = core.choose_new_category_name(call.message, data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
        base.write_carousel_id(user_id=call.message.chat.id, carousel_ids=[call.message.message_id + 1])
        base.set_state(user_id=call.from_user.id, state=States.NEW_CATEGORY_NAME.value)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.NEW_CATEGORY_NAME.value
)
def new_category_name_cancel(call: CallbackQuery):
    """  """
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.send_message(chat_id=call.message.chat.id, text='Переименование отменено.')
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
        base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.NEW_CATEGORY_NAME.value
)
def rename_category(message: Message):
    """  """
    base = SqW(config.DB_FILE)
    data['category'] = base.get_user_state(message.chat.id)['current_category']
    response = core.rename_category(message, data)
    delete_posts(message=message, ids=base.get_user_state(message.chat.id)['carousel_id'].split(','))
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    base.write_current_category(message.chat.id, category='')  # Забыть текущую категорию
    base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)


@bot.message_handler(
    commands=['assemble'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
)
def assemble_post(message: Message):
    """ Обработка команды сборки ранее отправленного поста """
    base = SqW(config.DB_FILE)
    response = core.assemble_post_handler(message, data)
    base.set_state(user_id=message.chat.id, state=States.ASSEMBLE.value)
    send_post(message, response)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.ASSEMBLE.value
)
def setup_post(call: CallbackQuery):
    """ Обработка коллбэк-кнопок в режиме сборки поста """
    base = SqW(config.DB_FILE)
    if call.data == 'category':
        base.set_state(user_id=call.from_user.id, state=States.CATEGORY.value)
        response = core.choose_category(message=call.message, data=data)
        bot.send_message(chat_id=call.from_user.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'comment':
        base.set_state(user_id=call.from_user.id, state=States.COMMENT.value)
        response = core.await_comment(call.message, data)
        bot.answer_callback_query(callback_query_id=call.id, text=response.text)
        bot.send_message(chat_id=call.from_user.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'cancel':
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
        core.cancel_assemble(call.message)
        bot.answer_callback_query(callback_query_id=call.id, text='ОТМЕНА')
        bot.send_message(chat_id=call.message.chat.id, text='Сборка поста <b>отменена</b>.')
    elif call.data == 'confirm':
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
        response = core.confirm_post(message=call.message, data=data)
        bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.COMMENT.value
)
def accept_comment(message: Message):
    """ Обработка текста-комментария к собираемому посту """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.ASSEMBLE.value)
    response = core.handle_comment(message, data)
    send_post(message, response)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.COMMENT.value
)
def cancel_comment(call):
    """ Удаление ранее добавленного комментария """
    base = SqW(config.DB_FILE)
    if call.data == 'del_comment':
        bot.answer_callback_query(callback_query_id=call.id, text='Комментарий удален')
        response = core.remove_comment(call.message, data)
        base.set_state(user_id=call.from_user.id, state=States.ASSEMBLE.value)
        send_post(call.message, response)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.CATEGORY.value
)
def accept_category(call: CallbackQuery):
    """ Присвоение собираемому посту выбранной категории """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=call.message.chat.id, state=States.ASSEMBLE.value)
    response = core.handle_category(call, data)
    bot.answer_callback_query(callback_query_id=call.id, text=f'Посту присвоена категория {call.data}')
    send_post(call.message, response)


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value and
    message.text == 'Мои записи'
)
def look_categories(message: Message):
    """ Просмотр сохраненных записей; отправляем редактируемое сообщение с категориями-кнопками """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.LOOK.value)
    data['mode'] = 'look'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    base.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.message_handler(
    commands=['look'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] in [States.DEFAULT.value,
                                                                                          States.LOOK.value]
)
def look_categories_oldvers(message: Message):
    """ Просмотр сохраненных записей; отправляем редактируемое сообщение с категориями-кнопками """
    base = SqW(config.DB_FILE)
    if base.get_user_state(message.chat.id)['state'] == States.LOOK.value:
        delete_posts(message=message, ids=[base.get_user_state(message.chat.id)['carousel_id'].split(',')[-1]])
        base.write_carousel_id(message.chat.id, [0])
    base.set_state(user_id=message.chat.id, state=States.LOOK.value)
    data['mode'] = 'look'
    response = core.look_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
    base.write_carousel_id(user_id=message.chat.id, carousel_ids=[message.message_id + 1])


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value and
    message.text == 'Настройки'
)
def settings(message: Message):
    """  """
    base = SqW(config.DB_FILE)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.LOOK.value
)
def look_records(call: CallbackQuery):
    """ Просмотр постов выбранной категории """
    base = SqW(config.DB_FILE)
    if call.data == 'add_category':
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        base.set_state(user_id=call.message.chat.id, state=States.CATEGORY_NAME.value)
        bot.send_message(chat_id=call.message.chat.id, text='Введите имя новой категории (не более <b>20</b> символов)')
    elif call.data == 'prev' or call.data == 'next':
        response = core.carousel_handler(call, data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        base.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Управление постом:', reply_markup=response.keyboard)
    elif call.data == 'pass':  # Нажата холостая кнопка
        pass
    elif call.data == 'cancel':
        bot.answer_callback_query(callback_query_id=call.id, text='Отменено')
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        response = core.start_handler(message=call.message)
        bot.send_message(chat_id=call.message.chat.id, text='Вы вернулись в главное меню.',
                         reply_markup=response.keyboard)
        base.set_state(user_id=call.from_user.id, state=States.DEFAULT.value)
    elif call.data == 'remove':
        base.set_state(user_id=call.from_user.id, state=States.DELETE_POST.value)
        response = core.delete_post_warn(call.message, data)
        bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                              message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
    elif call.data == 'replace':
        base.set_state(user_id=call.from_user.id, state=States.REPLACE_POST.value)
        data['mode'] = 'replace'
        response = core.look_handler(call.message, data)
        bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                              message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
    else:
        data['category'] = call.data
        response = core.look_records_handler(message=call.message, data=data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        base.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Управление постом:', reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.DELETE_POST.value
)
def delete_post_from_category(call: CallbackQuery):
    """ Обработка подтверждения удаления поста """
    base = SqW(config.DB_FILE)
    if call.data == 'confirm':
        response = core.delete_post(call.message, data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.answer_callback_query(callback_query_id=call.id, text='Пост удален')
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        base.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='✅ Пост был <b>удален</b>', reply_markup=response.keyboard)
    elif call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        bot.edit_message_text(text='Управление постом:', chat_id=call.message.chat.id,
                              message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
    base.set_state(user_id=call.from_user.id, state=States.LOOK.value)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.REPLACE_POST.value
)
def replace_post(call: CallbackQuery):
    """ Обработка выбора другой категории для поста """
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        bot.edit_message_text(text='Управление постом:', chat_id=call.message.chat.id,
                              message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
        bot.edit_message_reply_markup(reply_markup=response.keyboard, chat_id=call.message.chat.id,
                                      message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
    else:
        data['category'] = call.data
        response = core.replace_post(call.message, data)
        delete_posts(message=call.message, ids=base.get_user_state(call.from_user.id)['carousel_id'].split(','))
        bot.answer_callback_query(callback_query_id=call.id, text='Пост перемещен')
        send_post(call.message, response, carousel=True)
        carousel_ids = core.define_carousel_ids(call.message, response)
        base.write_carousel_id(call.from_user.id, carousel_ids)
        bot.send_message(chat_id=call.message.chat.id, text='Пост был перемещен', reply_markup=response.keyboard)
    base.set_state(user_id=call.from_user.id, state=States.LOOK.value)


@bot.message_handler(
    content_types=['text', 'document', 'photo', 'video'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
)
def new_record(message: Message):
    """ Обработка всего в дефолтном состоянии, кроме определенных команд, как новой записи в базе """
    response = core.record_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(content_types=['text', 'document', 'photo', 'video'])
def any_msg(message: Message):
    """ Обработка всего, что не было обработано другими хэндлерами, как неизвестной команды """
    base = SqW(config.DB_FILE)
    delete_posts(message=message, ids=base.get_user_state(message.chat.id)['carousel_id'].split(','))
    help_msg = 'Непонятное сообщение.\nВозвращаемся в главное меню...\nПутеводитель по командам: /help'
    bot.send_message(chat_id=message.chat.id, text=help_msg)
    base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)


@time_it
def send_post(message: Message, response: Response, carousel=False):
    """ Оболочка для различных способов отправки сообщений ботом в зависимости от типа поста """
    base = SqW(config.DB_FILE)
    kb = response.keyboard if not carousel else ReplyKeyboardRemove()
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
        base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=kb)
    elif response.flag == 'error1':
        base.set_state(user_id=message.chat.id, state=States.COMMENT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)
    elif response.flag == 'error2':
        base.set_state(user_id=message.chat.id, state=States.CATEGORY.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)


@time_it
def delete_posts(message: Message, ids: list):
    """ удаляет все посты с id из списка """
    for i in ids:
        try:
            bot.delete_message(message.chat.id, message_id=i)
        except Exception as e:
            config.ps_logger.exception(f'Cannot delete posts for user {message.chat.id} => {e}')


if __name__ == '__main__':
    random.seed()
    bot.polling()  # после отладки изменить на bot.infinity_polling()
