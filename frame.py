from telebot import types
from config import DEFAULT_CATEGORIES, States, time_it


class User:

    def __init__(self, message: types.Message):
        self.user_id = str(message.chat.id)  # или message.from_user.id
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

        # определение, в каком листе должна появиться подпись
        photo_caption, video_caption, doc_caption = None, None, None
        if photos != '':
            photo_caption = caption
        elif photos == '' and videos != '':
            video_caption = caption
        elif videos == '' and documents != '':
            doc_caption = caption

        photo_list = [types.InputMediaPhoto(photos.split(',')[0], caption=photo_caption, parse_mode='HTML')] + \
                     [types.InputMediaPhoto(i) for i in photos.split(',')[1:]] if photos != '' else []
        video_list = [types.InputMediaVideo(videos.split(',')[0], caption=video_caption, parse_mode='HTML')] + \
                     [types.InputMediaVideo(i) for i in videos.split(',')[1:]] if videos != '' else []
        document_list = [types.InputMediaDocument(documents.split(',')[0], caption=doc_caption, parse_mode='HTML')] + \
                        [types.InputMediaDocument(i) for i in documents.split(',')[1:]] if documents != '' else []
        return photo_list + video_list + document_list

    @staticmethod
    def create_attachment(photos: str, videos: str = None, documents: str = None, media: str = None,
                          attach_type: str = None):
        """  """
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
            self.text = '<b>Вы находитесь в главном меню.</b>\n► /help — узнать, как работать с ботом.'

        elif resp_type == 'added_category':
            self.text = self.mktext_added_category(data)
        elif resp_type == 'part_record':
            self.text = 'Получено ✅' if data['success'] else 'Кажется, уже пора нажимать /assemble'
            self.keyboard = self.mkkb_new_record(data)
        elif resp_type == 'no_temp':
            self.text = 'Чтобы сохранить что-то, нужно сначала это что-то мне отправить ☝️'
            self.flag = 'no_records'
            self.keyboard = types.ReplyKeyboardRemove()
        elif resp_type == 'caption_too_long':
            self.text = '❌ Недопустимая длина подписи вложения.'
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
                self.text = 'Попробуй еще.'
                self.flag = 'error1'
        elif resp_type == 'choose_category':
            self.text = 'Выберите категорию из доступных'
            self.keyboard = self.mkkb_choose_category(data)
        elif resp_type == 'handled_category':
            if data['success']:
                self.text = self.mktext_assembled_post(data['post'])
                self.flag = data['post'].attach_type
                self.attachment = data['post'].attachment
                self.keyboard = self.mkkb_assemble_post(data)
            else:
                self.text = '❌ Не-не-не. Нужно нажать кнопку с категорией.'
                self.flag = 'error2'
        elif resp_type == 'confirm_post':
            self.text = f'✅ Пост сохранен в категории <code>{data["category"]}</code>'
            self.keyboard = types.ReplyKeyboardRemove()
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
            self.text = f'Удалить категорию <code>{data["category"]}</code> и все ее посты ({data["length"]})?' \
                        f'\n❗️<b><i>Это действие необратимо.</i></b>'
            self.keyboard = self.mkkb_confirm(data)
        elif resp_type == 'deleted_category':
            self.text = f'✅ Категория <code>{data["category"]}</code> удалена, как и все ее посты.'
            self.keyboard = types.ReplyKeyboardRemove()
        elif resp_type == 'new_category_name':
            self.text = f'Введите новое название для категории <code>{data["category"]}</code>'
            self.keyboard = self.mkkb_confirm(data)
        elif resp_type == 'renamed_category':
            if data['success']:
                self.text = f'✅ Категория <code>{data["category"]}</code> была переименована.'
            else:
                self.text = '❌ Не удалось переименовать категорию.'
            self.keyboard = types.ReplyKeyboardRemove()
        elif resp_type == 'delete_post_warning':
            self.text = 'Удалить эту запись?'
            self.keyboard = self.mkkb_confirm(data)

    @staticmethod
    def mktext_added_category(data: dict) -> str:
        """  """
        if data['success']:
            return f'✅ Успешно добавлена категория <code>{data["category"]}</code>'
        else:
            return f'❌ Категория <code>{data["category"]}</code> не была добавлена.'

    @staticmethod
    def mkkb_new_record(data: dict):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = ['/assemble', '/cancel']
        for button in buttons:
            kb.add(button)
        return kb

    @staticmethod
    def mktext_assembled_post(post: Post) -> str:
        """  """
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
        """  """
        # assert flag in range(3)
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
    def mktext_await_comment(data: dict):
        """  """
        if data['post'].attach_type == 'text':
            symbols = 3900 - len(data['post'].text)
        else:
            symbols = 900 - len(data['post'].text)
        text = f'💬 Введите комментарий.\nДопустимое количество символов: {symbols}'
        if data['post'].comment is not None:
            text = '\n\n'.join([text, f'Заменяемый комментарий:\n{data["post"].comment}'])
        return text

    @staticmethod
    def mkkb_await_comment(data: dict):
        """  """
        markup = types.InlineKeyboardMarkup()
        if data['post'].comment is not None:
            btn1 = types.InlineKeyboardButton(text='Удалить комментарий', callback_data='del_comment')
            markup.add(btn1)
        return markup

    @staticmethod
    def mkkb_choose_category(data: dict):
        """  """
        markup = types.InlineKeyboardMarkup()
        buttons = [types.InlineKeyboardButton(text=cat, callback_data=cat) for cat in data['category']]
        for index, category in enumerate(buttons):
            try:
                if index % 2 == 0:
                    markup.row(buttons[index], buttons[index+1])
            except IndexError:
                markup.add(buttons[index])
                break
        return markup

    @staticmethod
    @time_it
    def mkkb_look_categories(data: dict):
        """ КРАЙНЕ ГОВНОКОДИСТО. Подумать, как исправить """
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = data['category']
        if data['mode'] == 'look':
            markup.add(types.InlineKeyboardButton(text='Добавить категорию', callback_data='add_category'))
        for index, category in enumerate(buttons):
            try:
                if index % 3 == 0:
                    markup.row(types.InlineKeyboardButton(text=f'{buttons[index][0]} ({buttons[index][1]})',
                                                          callback_data=f'{buttons[index][0]}'),
                               types.InlineKeyboardButton(text=f'{buttons[index+1][0]} ({buttons[index+1][1]})',
                                                          callback_data=f'{buttons[index+1][0]}'),
                               types.InlineKeyboardButton(text=f'{buttons[index+2][0]} ({buttons[index+2][1]})',
                                                          callback_data=f'{buttons[index+2][0]}'))
            except IndexError:
                if index == len(buttons) - 2:
                    markup.row(types.InlineKeyboardButton(text=f'{buttons[index][0]} ({buttons[index][1]})',
                                                          callback_data=f'{buttons[index][0]}'),
                               types.InlineKeyboardButton(text=f'{buttons[index+1][0]} ({buttons[index+1][1]})',
                                                          callback_data=f'{buttons[index+1][0]}'))
                    break
                elif index == len(buttons) - 1:
                    markup.add(types.InlineKeyboardButton(text=f'{buttons[index][0]} ({buttons[index][1]})',
                                                          callback_data=f'{buttons[index][0]}'))
                    break
        cancel_text = 'Назад' if data['mode'] == 'replace' else 'Закрыть'
        markup.add(types.InlineKeyboardButton(text=f'{cancel_text}', callback_data=f'cancel'))
        return markup

    @staticmethod
    @time_it
    def mkkb_carousel(data: dict):
        """  """
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text=f'<', callback_data=f'prev')
        btn2 = types.InlineKeyboardButton(text=f'>', callback_data=f'next')
        btn3 = types.InlineKeyboardButton(text=f'Закрыть', callback_data=f'cancel')
        btn4 = types.InlineKeyboardButton(text=f'Удалить', callback_data=f'remove')
        btn5 = types.InlineKeyboardButton(text=f'Переместить', callback_data=f'replace')
        btn6 = types.InlineKeyboardButton(text=f'{data["position"]}', callback_data=f'pass')
        markup.row(btn1, btn6, btn2)
        markup.row(btn4, btn5)
        markup.add(btn3)
        return markup

    @staticmethod
    def mktext_categories_action(data: dict):
        """  """
        if data['mode'] == 'delete':
            return 'Выберите категорию для удаления:'
        elif data['mode'] == 'rename':
            return 'Выберите категорию для переименования:'
        elif data['mode'] == 'replace':
            return 'Выберите категорию для перемещения:'
        else:
            return 'Выберите категорию для просмотра:'

    @staticmethod
    def mkkb_confirm(data: dict):
        """  """
        markup = types.InlineKeyboardMarkup()
        btn2 = types.InlineKeyboardButton(text=f'Отмена', callback_data=f'cancel')
        if data['state'] in [States.DELETE.value, States.DELETE_POST.value]:
            btn1 = types.InlineKeyboardButton(text=f'Подтвердить', callback_data=f'confirm')
            markup.row(btn1, btn2)
        elif data['state'] in [States.RENAME.value, States.REPLACE_POST.value]:
            markup.add(btn2)
        return markup

    @staticmethod
    def mktext_no_posts(data: dict):
        """  """
        return f'❎ В выбранной категории сейчас нет ни одного поста.'

    @staticmethod
    def mkkb_no_posts(data: dict):
        """  """
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text=f'Отмена', callback_data=f'cancel')
        markup.add(btn1)
        return markup


