from telebot import types
from config import DEFAULT_CATEGORIES, States, Replies as Rp


class User:

    def __init__(self, message: types.Message):
        self.user_id = str(message.chat.id)
        self.username = message.from_user.username
        self.first_name = message.from_user.first_name
        self.last_name = message.from_user.last_name
        self.categories = ','.join(DEFAULT_CATEGORIES)


class Post:

    def __init__(self, post_db):
        self.post_id = post_db['id']
        self.message_text = post_db['message_text']
        self.caption = post_db['caption']
        self.attach_type = post_db['attach_type']
        self.photos = post_db['att_photo']
        self.videos = post_db['att_video']
        self.documents = post_db['att_document']
        self.forward_from_chat_id = post_db['ffc_id']
        self.forward_from_chat_title = post_db['ffc_title']
        self.forward_from_chat_username = post_db['ffc_username']
        self.date_created = post_db['date']
        self.date_saved = post_db['date_saved']
        self.comment = post_db['comment']
        self.category = post_db['category']
        self.text = Response.mktext_assembled_post(self)
        self.media = self.create_media_group(self.photos, self.videos, self.documents, self.text, self.attach_type)
        self.attachment = self.create_attachment(self.photos, self.videos, self.documents, self.media, self.attach_type)

    @staticmethod
    def create_media_group(photos: str = None, videos: str = None, documents: str = None,
                           caption: str = None, attach_type: str = None):
        """ Создание медиагруппы из id файлов-вложений поста """

        if attach_type != 'media_group':
            return None

        # определение, в каком списке должна появиться подпись
        photo_caption, video_caption, doc_caption = None, None, None
        if photos:
            photo_caption = caption
        elif not photos and videos:
            video_caption = caption
        elif not videos and documents:
            doc_caption = caption

        photo_list = [types.InputMediaPhoto(photos.split(',')[0], caption=photo_caption, parse_mode='HTML')] + \
                     [types.InputMediaPhoto(i) for i in photos.split(',')[1:]] if photos else []
        video_list = [types.InputMediaVideo(videos.split(',')[0], caption=video_caption, parse_mode='HTML')] + \
                     [types.InputMediaVideo(i) for i in videos.split(',')[1:]] if videos else []
        document_list = [types.InputMediaDocument(documents.split(',')[0], caption=doc_caption, parse_mode='HTML')] + \
                        [types.InputMediaDocument(i) for i in documents.split(',')[1:]] if documents else []
        return photo_list + video_list + document_list

    @staticmethod
    def create_attachment(photos: str, videos: str = None, documents: str = None, media: str = None,
                          attach_type: str = None):
        """ Создание атрибута вложений """
        if attach_type == 'photo':
            return [photos]
        elif attach_type == 'video':
            return [videos]
        elif attach_type == 'document':
            return [documents]
        elif attach_type == 'media_group':
            return media
        else:
            return None


class Response:

    def __init__(self, resp_type: str, data: dict = None):
        self.text = None
        self.attachment = None
        self.keyboard = types.ReplyKeyboardRemove()
        self.flag = None

        if resp_type == 'start':
            self.text = Rp.START
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'updated':
            self.text = Rp.HELP_UPDATED
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'added_category':
            self.text = self.mktext_added_category(data)
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'part_record':
            self.text = Rp.PART_RECEIVED_YES if data['success'] else Rp.PART_RECEIVED_NO
            self.keyboard = self.mkkb_new_record()
        elif resp_type == 'no_temp':
            self.text = Rp.NO_TEMP
            self.flag = 'no_records'
            self.keyboard = self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'caption_too_long':
            self.text = Rp.CAPTION_TOO_LONG
        elif resp_type == 'assembled_post':
            self.text = self.mktext_assembled_post(data['post'])
            self.attachment = data['post'].attachment
            self.keyboard = self.mkkb_assemble_post(data)
            self.flag = data['post'].attach_type
        elif resp_type == 'await_comment':
            self.text = self.mktext_await_comment(data)
            self.keyboard = self.mkkb_await_comment(data)
        elif resp_type == 'handled_comment':
            if data['success']:
                self.text = self.mktext_assembled_post(data['post'])
                self.flag = data['post'].attach_type
                self.attachment = data['post'].attachment
                self.keyboard = self.mkkb_assemble_post(data)
            else:
                self.text = Rp.COMMENT_RETRY
                self.flag = 'error1'
        elif resp_type == 'choose_category':
            self.text = Rp.CHOOSE_CATEGORY
            self.keyboard = self.mkkb_choose_category(data)
        elif resp_type == 'handled_category':
            if data['success']:
                self.text = self.mktext_assembled_post(data['post'])
                self.flag = data['post'].attach_type
                self.attachment = data['post'].attachment
                self.keyboard = self.mkkb_assemble_post(data)
            else:
                self.text = Rp.HANDLE_CATEGORY_ERROR
                self.flag = 'error2'
        elif resp_type == 'cancel_assembling':
            self.text = Rp.CANCEL_ASSEMBLING
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'confirm_post':
            self.text = Rp.CONFIRM_POST_.format(data['category'])
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'look_categories':
            self.text = self.mktext_categories_action(data)
            self.keyboard = self.mkkb_look_categories(data)
        elif resp_type == 'carousel':
            self.text = self.mktext_assembled_post(data['post'])
            self.flag = data['post'].attach_type
            self.attachment = data['post'].attachment
            self.keyboard = self.mkkb_carousel(data)
        elif resp_type == 'no_posts':
            self.text = self.mktext_no_posts(data)
            self.keyboard = self.mkkb_no_posts(data)
            self.attachment = None      # Скидывать пикчу перекати поле скажем
            self.flag = 'text'
        elif resp_type == 'delete_warning':
            self.text = Rp.DELETE_WARNING_.format(data['category'], data['length'])
            self.keyboard = self.mkkb_confirm(data)
        elif resp_type == 'deleted_category':
            if data['success']:
                self.text = Rp.DELETED_CATEGORY_.format(data['category'])
            else:
                self.text = Rp.DEL_CATEGORY_FAIL
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'new_category_name':
            self.text = Rp.NEW_CATEGORY_NAME_.format(data['category'])
            self.keyboard = self.mkkb_confirm(data)
        elif resp_type == 'renamed_category':
            if data['success']:
                self.text = Rp.RENAMED_CATEGORY_.format(data['category'])
            else:
                self.text = Rp.REN_CATEGORY_FAIL
            self.keyboard = self.mkkb_main_kb()
        elif resp_type == 'delete_post_warning':
            self.text = Rp.DEL_POST_WARNING
            self.keyboard = self.mkkb_confirm(data)
        elif resp_type == 'settings':
            self.text = Rp.SETTINGS
            self.keyboard = self.mkkb_settings()

    @staticmethod
    def mkkb_main_kb() -> types.ReplyKeyboardMarkup:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = ['Мои записи', 'Настройки']
        kb.row(*buttons)
        return kb

    @staticmethod
    def mktext_added_category(data: dict) -> str:
        if data['success']:
            return Rp.ADDED_CATEGORY_YES_.format(data['category'])
        else:
            return Rp.ADDED_CATEGORY_NO_.format(data['category'])

    @staticmethod
    def mkkb_new_record() -> types.ReplyKeyboardMarkup:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = ['/assemble', '/cancel']
        kb.row(*buttons)
        return kb

    @staticmethod
    def mktext_assembled_post(post: Post) -> str:
        if post.category is not None:
            text = f'<u><b>Категория:</b> {post.category}</u>\n\n'
        else:
            text = ''
        if post.message_text is not None:
            text = ''.join([text, post.message_text])
        elif post.caption is not None:
            text = ''.join([text, post.caption])
        symbols = 3900 if post.attach_type == 'text' else 950
        if len(text) < symbols:  # Телеграм не пропустит caption длиннее 1024 символов, а text - длиннее 4096
            if post.forward_from_chat_title is not None:
                text = '\n\n'.join([text, f'<b>Источник:</b> {post.forward_from_chat_title}'])
            if post.forward_from_chat_username is not None:
                text = ' '.join([text, f'(@{post.forward_from_chat_username})'])
            if post.date_created is not None:
                text = '\n'.join([text, f'<b>Создано:</b> <code>{post.date_created}</code>'])
            if post.date_saved is not None:
                text = '\n'.join([text, f'<b>Сохранено:</b> <code>{post.date_saved}</code>'])
        if post.comment is not None:
            text = '\n\n'.join([text, f'💬 <i>{post.comment}</i>'])

        return text

    @staticmethod
    def mkkb_assemble_post(data: dict) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text='Выбрать категорию', callback_data='category')
        btn2 = types.InlineKeyboardButton(text='Комментировать', callback_data='comment')
        kb.row(btn1, btn2)
        btn3 = types.InlineKeyboardButton(text='Отмена', callback_data='cancel')
        kb.add(btn3)
        if data['post'].category is not None:
            btn4 = types.InlineKeyboardButton(text='ПОДТВЕРДИТЬ', callback_data='confirm')
            kb.add(btn4)
        return kb

    @staticmethod
    def mktext_await_comment(data: dict) -> str:
        if data['post'].attach_type == 'text':
            symbols = 3900 - len(data['post'].text)
        else:
            symbols = 900 - len(data['post'].text)
        text = f'💬 Введите комментарий.\nДопустимое количество символов: {symbols}'
        if data['post'].comment is not None:
            text = '\n\n'.join([text, f'Заменяемый комментарий:\n{data["post"].comment}'])
        return text

    @staticmethod
    def mkkb_await_comment(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        if data['post'].comment is not None:
            btn1 = types.InlineKeyboardButton(text='Удалить комментарий', callback_data='del_comment')
            markup.add(btn1)
        return markup

    @staticmethod
    def mkkb_choose_category(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        try:
            data['category'].remove('HELP')
        except ValueError:
            pass
        buttons = [types.InlineKeyboardButton(text=cat, callback_data=cat) for cat in data['category']]
        button_rows = clustering(buttons, group_by=3)
        for btn_row in button_rows:
            markup.row(*btn_row)
        return markup

    @staticmethod
    def mkkb_look_categories(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=3)
        if data['mode'] == 'look':
            markup.add(types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category'))

        buttons = [types.InlineKeyboardButton(text=f'{btn[0]} ({btn[1]})', callback_data=btn[0])
                   for btn in data['category']]
        button_rows = clustering(buttons, group_by=3)
        for btn_row in button_rows:
            markup.row(*btn_row)

        cancel_text = 'Назад' if data['mode'] == 'replace' else 'Закрыть'
        markup.add(types.InlineKeyboardButton(text=f'{cancel_text}', callback_data='cancel'))
        return markup

    @staticmethod
    def mkkb_carousel(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text='<', callback_data='prev')
        btn2 = types.InlineKeyboardButton(text='>', callback_data='next')
        btn3 = types.InlineKeyboardButton(text='Закрыть', callback_data='cancel')
        btn4 = types.InlineKeyboardButton(text='Удалить', callback_data='remove')
        btn5 = types.InlineKeyboardButton(text='Переместить', callback_data='replace')
        btn6 = types.InlineKeyboardButton(text=f'{data["position"]}', callback_data='pass')
        markup.row(btn1, btn6, btn2)
        markup.row(btn4, btn5)
        markup.add(btn3)
        return markup

    @staticmethod
    def mktext_categories_action(data: dict) -> str:
        if data['mode'] == 'delete':
            return Rp.CATEGORIES_ACTION_DEL
        elif data['mode'] == 'rename':
            return Rp.CATEGORIES_ACTION_REN
        elif data['mode'] == 'replace':
            return Rp.CATEGORIES_ACTION_REPL
        else:
            return Rp.CATEGORIES_ACTION_LOOK

    @staticmethod
    def mkkb_confirm(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        btn2 = types.InlineKeyboardButton(text='Отмена', callback_data='cancel')
        if data['state'] in [States.LOOK.value, States.DELETE.value]:
            btn1 = types.InlineKeyboardButton(text='Подтвердить', callback_data='confirm')
            markup.row(btn1, btn2)
        elif data['state'] in [States.RENAME.value, States.REPLACE_POST.value]:
            markup.add(btn2)
        return markup

    @staticmethod
    def mktext_no_posts(data: dict) -> str:
        return Rp.NO_POSTS

    @staticmethod
    def mkkb_no_posts(data: dict) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text='Закрыть', callback_data='cancel')
        markup.add(btn1)
        return markup

    @staticmethod
    def mkkb_settings() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category')
        btn2 = types.InlineKeyboardButton(text='Переименовать категорию', callback_data='ren_category')
        btn3 = types.InlineKeyboardButton(text='Удалить категорию', callback_data='del_category')
        btn4 = types.InlineKeyboardButton(text='Закрыть', callback_data='cancel')
        buttons = [btn1, btn2, btn3, btn4]
        for btn in buttons:
            markup.add(btn)
        return markup


def clustering(lst: list, group_by: int) -> list[tuple]:
    """ Группирует список в список кортежей """
    it = [iter(lst)] * group_by
    cluster = list(zip(*it))
    extra = len(lst) % group_by
    if extra:
        cluster.append(tuple(lst[-extra:]))
    return cluster
