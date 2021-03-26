import telebot
from telebot.types import Message, CallbackQuery, ReplyKeyboardRemove
import random

from sqler import SqlWorker as SqW
import core
from frame import Response
import config
from config import States, Replies as Rp, time_it

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


class MsqUpdate:
    """ Контекстный менеджер для удаления старых сообщений по ID и записи ID новых сообщений """

    def __init__(self, response: Response = None, message: Message = None, delete: bool = False, last: bool = False,
                 mem: bool = False, next_one: bool = False, state: str = None):
        """
        :param response: объект подготовленного ответа бота
        :param message: объект входящего сообщения
        :param delete: True/False - удалить/не удалять запомненные ранее сообщения
        :param last: True/False - удалить последнее/все запомненные сообщения
        :param mem: True/False - запомнить/не запоминать отправляемые сообщения
        :param next_one: True/False - запомнить 1 следующее сообщение/вычислить id запоминаемой группы сообщений
        :param state: not None - сменить состояние диалога
        """
        self.base = SqW(config.DB_FILE)
        self.message = message
        self.response = response
        self.delete = delete
        self.last = last
        self.mem = mem
        self.next = next_one
        self.state = state

    def __enter__(self):
        if self.delete:
            id_list = self.base.get_user_state(self.message.chat.id)['carousel_id'].split(',')
            if self.last:
                id_list = [id_list[-1]]
            delete_posts(message=self.message, ids=id_list)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mem:
            if self.next:
                carousel_ids = [self.message.message_id + 1]
            else:
                carousel_ids = core.define_carousel_ids(message=self.message, response=self.response)
            self.base.write_carousel_id(user_id=self.message.chat.id, carousel_ids=carousel_ids)
        if self.state:
            self.base.set_state(user_id=self.message.chat.id, state=self.state)


@bot.message_handler(commands=['start', 'cancel'])
def cmd_start(message: Message):
    """ Переход/возврат в дефолтное состояние """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)
    response = core.start_handler(message=message)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(commands=['help'])
def cmd_help(message: Message):
    """ Просмотр встроенной категории HELP """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.LOOK.value)
    response = core.help_handler(message, data)
    with MsqUpdate(response, message, mem=True):
        send_post(message, response, carousel=True)
        bot.send_message(chat_id=message.chat.id, text=Rp.POST_CONTROL, reply_markup=response.keyboard)


@bot.message_handler(commands=['update'], func=lambda message: message.chat.id == config.ADMIN_ID)
def cmd_update(message: Message):
    """ Обновление информации о боте в категории HELP (только для админа) """
    response = core.update(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
    and message.text == 'Настройки'
)
def settings(message: Message):
    """ Открытие меню настроек """
    response = core.settings_handler(message, data)
    with MsqUpdate(response, message, mem=True, next_one=True, state=States.SETTINGS.value):
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.SETTINGS.value
)
def selected_settings(call: CallbackQuery):
    """ Обработка команды из меню Настройки """
    if call.data == 'add_category':
        with MsqUpdate(message=call.message, delete=True, state=States.CATEGORY_NAME.value):
            bot.send_message(chat_id=call.message.chat.id, text=Rp.CATEGORY_NAME)
    elif call.data == 'ren_category':
        data['mode'] = 'rename'
        response = core.look_handler(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, next_one=True, state=States.RENAME.value):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'del_category':
        data['mode'] = 'delete'
        response = core.look_handler(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, next_one=True, state=States.DELETE.value):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'cancel':
        response = core.settings_cancel(call.message, data)
        with MsqUpdate(response, call.message, delete=True, state=States.DEFAULT.value):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.CATEGORY_NAME.value)
def add_category(message: Message):
    """ Обработка текста как названия новой категории """
    base = SqW(config.DB_FILE)
    new_state = States.DEFAULT.value
    base.set_state(user_id=message.chat.id, state=new_state)
    data['state'] = new_state
    response = core.add_category_handler(message, data)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.DELETE.value
)
def delete_category(call: CallbackQuery):
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        with MsqUpdate(message=call.message, delete=True, state=States.DEFAULT.value):
            bot.send_message(chat_id=call.message.chat.id, text=Rp.CANCEL_REMOVAL)
            base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    elif call.data == 'confirm':
        data['category'] = base.get_user_state(call.from_user.id)['current_category']
        response = core.delete_category(call.message, data=data)
        with MsqUpdate(response, call.message, delete=True, state=States.DEFAULT.value):
            base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
    else:
        data['category'] = call.data
        response = core.delete_category_warn(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, next_one=True):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.RENAME.value
)
def new_category_name(call: CallbackQuery):
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        with MsqUpdate(message=call.message, delete=True, state=States.DEFAULT.value):
            bot.send_message(chat_id=call.message.chat.id, text=Rp.CANCEL_RENAME)
            base.write_current_category(call.from_user.id, category='')  # Забыть текущую категорию
    else:
        data['category'] = call.data
        response = core.choose_new_category_name(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, next_one=True, state=States.NEW_CAT_NAME.value):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.NEW_CAT_NAME.value
)
def new_category_name_cancel(call: CallbackQuery):
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        with MsqUpdate(message=call.message, delete=True, state=States.DEFAULT.value):
            bot.send_message(chat_id=call.message.chat.id, text=Rp.CANCEL_RENAME)
            base.write_current_category(call.from_user.id, category='')


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.NEW_CAT_NAME.value
)
def rename_category(message: Message):
    base = SqW(config.DB_FILE)
    data['category'] = base.get_user_state(message.chat.id)['current_category']
    response = core.rename_category(message, data)
    with MsqUpdate(response, message, delete=True, state=States.DEFAULT.value):
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)
        base.write_current_category(message.chat.id, category='')


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
    and message.text == 'Сохранить'
)
def assemble_post(message: Message):
    """ Сборка ранее отправленного поста """
    response = core.assemble_post_handler(message, data)
    with MsqUpdate(response, message, mem=True, state=States.ASSEMBLE.value):
        send_post(message, response)


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
    and message.text == 'Отмена'
)
def cancel_post(message: Message):
    """ Отмена сохранения поста """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)
    response = core.start_handler(message=message)
    bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.ASSEMBLE.value
)
def setup_post(call: CallbackQuery):
    """ Обработка коллбэк-кнопок в режиме сборки поста """
    base = SqW(config.DB_FILE)
    if call.data == 'category':
        response = core.choose_category(message=call.message, data=data)
        with MsqUpdate(response, call.message, state=States.CATEGORY.value):
            control_msg_id = base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            bot.edit_message_text(text=response.text, chat_id=call.message.chat.id, message_id=control_msg_id)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=control_msg_id,
                                          reply_markup=response.keyboard)
    elif call.data == 'comment':
        response = core.await_comment(call.message, data)
        with MsqUpdate(response, call.message, state=States.COMMENT.value):
            control_msg_id = base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            bot.edit_message_text(text=response.text, chat_id=call.message.chat.id, message_id=control_msg_id)
            if response.keyboard.keyboard:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=control_msg_id,
                                              reply_markup=response.keyboard)
            bot.answer_callback_query(callback_query_id=call.id, text=response.text)
    elif call.data == 'cancel':
        response = core.cancel_assemble(call.message)
        with MsqUpdate(response, call.message, delete=True, state=States.DEFAULT.value):
            bot.answer_callback_query(callback_query_id=call.id, text=Rp.CANCEL)
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)
    elif call.data == 'confirm':
        response = core.confirm_post(message=call.message, data=data)
        with MsqUpdate(response, call.message, delete=True, last=True, state=States.DEFAULT.value):
            bot.send_message(chat_id=call.message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.message_handler(
    content_types=['text'],
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.COMMENT.value
)
def accept_comment(message: Message):
    """ Обработка текста как комментария к собираемому посту """
    base = SqW(config.DB_FILE)
    base.set_state(user_id=message.chat.id, state=States.ASSEMBLE.value)
    response = core.handle_comment(message, data)
    # with MsqUpdate(response, message, delete=)    придумать как привести к общему знаменателю и этот случай
    send_post(message, response)
    msg_id_list = base.get_user_state(message.chat.id)['carousel_id'].split(',')
    msg_id_list.append(str(int(msg_id_list[-1]) + 1))
    delete_posts(message=message, ids=msg_id_list)
    carousel_ids = core.define_carousel_ids(message, response)
    base.write_carousel_id(message.chat.id, carousel_ids)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.COMMENT.value
)
def cancel_comment(call: CallbackQuery):
    """ Удаление ранее добавленного комментария """
    if call.data == 'del_comment':
        bot.answer_callback_query(callback_query_id=call.id, text=Rp.COMMENT_REMOVED)
        response = core.remove_comment(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, state=States.ASSEMBLE.value):
            send_post(call.message, response)
    elif call.data == 'cancel':
        pass


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.CATEGORY.value
)
def accept_category(call: CallbackQuery):
    """ Присвоение собираемому посту выбранной категории """
    response = core.handle_category(call, data)
    with MsqUpdate(response, call.message, delete=True, mem=True, state=States.ASSEMBLE.value):
        bot.answer_callback_query(callback_query_id=call.id, text=f'{Rp.POST_ASSIGNED}{call.data}')
        send_post(call.message, response)


@bot.message_handler(
    func=lambda message: SqW(config.DB_FILE).get_user_state(message.chat.id)['state'] == States.DEFAULT.value
    and message.text == 'Мои записи'
)
def look_categories(message: Message):
    """ Просмотр добавленных категорий """
    data['mode'] = 'look'
    response = core.look_handler(message, data)
    with MsqUpdate(response, message, mem=True, next_one=True, state=States.LOOK.value):
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.LOOK.value
)
def look_records(call: CallbackQuery):
    """ Просмотр постов выбранной категории """
    base = SqW(config.DB_FILE)
    if call.data == 'add_category':
        with MsqUpdate(message=call.message, delete=True, state=States.CATEGORY_NAME.value):
            bot.send_message(chat_id=call.message.chat.id, text=Rp.CATEGORY_NAME)
    elif call.data == 'prev' or call.data == 'next':
        response = core.carousel_handler(call, data)
        with MsqUpdate(response, call.message, delete=True, mem=True):
            send_post(call.message, response, carousel=True)
            bot.send_message(chat_id=call.message.chat.id, text=Rp.POST_CONTROL, reply_markup=response.keyboard)
    elif call.data == 'pass':  # Нажата пустая кнопка
        pass
    elif call.data == 'cancel':
        response = core.start_handler(message=call.message)
        with MsqUpdate(response, call.message, delete=True, state=States.DEFAULT.value):
            bot.answer_callback_query(callback_query_id=call.id, text=Rp.CANCEL)
            bot.send_message(chat_id=call.message.chat.id, text=Rp.MAIN_MENU_RET,
                             reply_markup=response.keyboard)
    elif call.data == 'remove':
        response = core.delete_post_warn(call.message, data)
        with MsqUpdate(response, call.message, state=States.DELETE_POST.value):
            bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                                  message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
            bot.edit_message_reply_markup(
                reply_markup=response.keyboard, chat_id=call.message.chat.id,
                message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            )
    elif call.data == 'replace':
        data['mode'] = 'replace'
        response = core.look_handler(call.message, data)
        with MsqUpdate(response, call.message, state=States.REPLACE_POST.value):
            bot.edit_message_text(text=response.text, chat_id=call.message.chat.id,
                                  message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
            bot.edit_message_reply_markup(
                reply_markup=response.keyboard, chat_id=call.message.chat.id,
                message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            )
    else:
        data['category'] = call.data
        response = core.look_records_handler(message=call.message, data=data)
        with MsqUpdate(response, call.message, delete=True, mem=True):
            send_post(call.message, response, carousel=True)
            bot.send_message(chat_id=call.message.chat.id, text=Rp.POST_CONTROL, reply_markup=response.keyboard)


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.DELETE_POST.value
)
def delete_post_from_category(call: CallbackQuery):
    """ Обработка подтверждения удаления поста """
    base = SqW(config.DB_FILE)
    if call.data == 'confirm':
        response = core.delete_post(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, state=States.LOOK.value):
            bot.answer_callback_query(callback_query_id=call.id, text=Rp.POST_REMOVED)
            send_post(call.message, response, carousel=True)
            bot.send_message(chat_id=call.message.chat.id, text=Rp.POST_REMOVED, reply_markup=response.keyboard)
    elif call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        with MsqUpdate(response, call.message, state=States.LOOK.value):
            bot.edit_message_text(text=Rp.POST_CONTROL, chat_id=call.message.chat.id,
                                  message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
            bot.edit_message_reply_markup(
                reply_markup=response.keyboard, chat_id=call.message.chat.id,
                message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            )


@bot.callback_query_handler(
    func=lambda call: SqW(config.DB_FILE).get_user_state(call.from_user.id)['state'] == States.REPLACE_POST.value
)
def replace_post(call: CallbackQuery):
    """ Обработка выбора другой категории для поста """
    base = SqW(config.DB_FILE)
    if call.data == 'cancel':
        response = core.change_post_cancel(call.message, data)
        with MsqUpdate(response, call.message, state=States.LOOK.value):
            bot.edit_message_text(text=Rp.POST_CONTROL, chat_id=call.message.chat.id,
                                  message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1])
            bot.edit_message_reply_markup(
                reply_markup=response.keyboard, chat_id=call.message.chat.id,
                message_id=base.get_user_state(call.from_user.id)['carousel_id'].split(',')[-1]
            )
    else:
        data['category'] = call.data
        response = core.replace_post(call.message, data)
        with MsqUpdate(response, call.message, delete=True, mem=True, state=States.LOOK.value):
            bot.answer_callback_query(callback_query_id=call.id, text=Rp.POST_REPLACED)
            send_post(call.message, response, carousel=True)
            bot.send_message(chat_id=call.message.chat.id, text=Rp.POST_REPLACED, reply_markup=response.keyboard)


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
    with MsqUpdate(message=message, delete=True, state=States.DEFAULT.value):
        bot.send_message(chat_id=message.chat.id, text=Rp.UNKNOWN)


@time_it
def send_post(message: Message, response: Response, carousel=False):
    """ Оболочка для различных способов отправки сообщений ботом в зависимости от типа поста """
    base = SqW(config.DB_FILE)
    if response.flag == 'text':
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=ReplyKeyboardRemove())
    elif response.flag == 'photo':
        bot.send_photo(chat_id=message.chat.id, photo=response.attachment[0], caption=response.text,
                       reply_markup=ReplyKeyboardRemove())
    elif response.flag == 'video':
        bot.send_video(chat_id=message.chat.id, data=response.attachment[0], caption=response.text,
                       reply_markup=ReplyKeyboardRemove())
    elif response.flag == 'document':
        bot.send_document(chat_id=message.chat.id, data=response.attachment[0], caption=response.text,
                          reply_markup=ReplyKeyboardRemove())
    elif response.flag == 'media_group':
        bot.send_media_group(chat_id=message.chat.id, media=response.attachment)
    elif response.flag == 'no_records':
        base.set_state(user_id=message.chat.id, state=States.DEFAULT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text, reply_markup=ReplyKeyboardRemove())
    elif response.flag == 'error1':
        base.set_state(user_id=message.chat.id, state=States.COMMENT.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)
    elif response.flag == 'error2':
        base.set_state(user_id=message.chat.id, state=States.CATEGORY.value)
        bot.send_message(chat_id=message.chat.id, text=response.text)

    if response.flag in ['text', 'photo', 'video', 'document', 'media_group'] and not carousel:
        bot.send_message(chat_id=message.chat.id, text=Rp.POST_CONTROL, reply_markup=response.keyboard)


@time_it
def delete_posts(message: Message, ids: list):
    """ Удаление всех постов с id из списка """
    try:
        for i in ids:
            bot.delete_message(message.chat.id, message_id=i)
    except Exception as e:
        config.ps_logger.exception(f'Cannot delete posts for user {message.chat.id} => {e}')


if __name__ == '__main__':
    random.seed()
    bot.infinity_polling()
