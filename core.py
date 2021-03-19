from datetime import datetime
import pytz
from telebot.types import Message, CallbackQuery
from frame import User, Response, Post
from sqler import SqlWorker
import config


def start_handler(message: Message) -> Response:
    """ Обработка возврата в дефолтное состояние """
    user = User(message)
    base = SqlWorker(config.DB_FILE)

    # Если такого юзера еще нет - добавляем его
    if base.get_user(user.user_id) is None:
        config.ps_logger.info(f'NEW USER ({user.first_name} {user.last_name} | @{user.username})!')
        base.add_user(user)
        base.write_user_in_state_table(user_id=user.user_id, state=config.States.DEFAULT.value)

    # Если у юзера нет нужных таблиц - создаем их
    if not base.check_table(f'{user.user_id}_temp'):
        base.add_user_temp(user.user_id)
    if not base.check_table(f'{user.user_id}_storage'):
        base.add_user_storage(user.user_id)

        # Автоматически заполняем категорию help-постами
        help_fill(user.user_id)
    base.clear_temp(user.user_id)
    return Response(resp_type='start')


def help_handler(message: Message, data: dict) -> Response:
    """ Обработка команды /help """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    records = base.get_all_by_category(user_id=user.user_id, category='HELP')
    if not records:
        return Response(resp_type='no_posts')
    records_ids = [record['id'] for record in records]
    base.write_records_id(user_id=user.user_id, id_list=records_ids)
    base.write_current_record(user_id=user.user_id, post_id=records_ids[0])
    post_db = base.get_post(user.user_id, records_ids[0])
    post = Post(post_db)
    data['post'] = post
    data['position'] = f'Стр. {records_ids.index(records_ids[0]) + 1} из {len(records_ids)}'
    return Response(resp_type='carousel', data=data)


def update(message: Message, data: dict):
    """ Обновляет категорию HELP у пользователей в соответствии с обновлением бота """
    base = SqlWorker(config.DB_FILE)
    all_users = base.get_all_users()
    users_ids = [i['user_id'] for i in all_users]
    for user_id in users_ids:
        base.delete_all_by_category(user_id, category='HELP')
        help_fill(user_id)
    return Response(resp_type='updated', data=data)


def add_category_handler(message: Message, data: dict) -> Response:
    """ Обработка добавления новой категории """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    existing_categories = base.get_user_categories(user.user_id)
    if message.text in existing_categories or len(message.text) > 20:
        added = False
    elif message.text == 'HELP':
        added = False
    else:
        user.categories = ','.join([existing_categories, message.text])
        added = base.add_user_categories(user)
    data['success'] = added
    data['category'] = message.text
    return Response(resp_type='added_category', data=data)


def record_handler(message: Message, data: dict) -> Response:
    """ Обработка новых записей в базе """
    c_type = message.content_type
    user = User(message)
    base = SqlWorker(config.DB_FILE)

    # К слишком длинной подписи вложения не получится добавить стандартные подписи бота, не говоря уже о комментарии
    # Telegram разрешает caption не более 1024 символов
    if message.html_caption is not None and len(message.html_caption) > 880:
        base.set_state(user.user_id, config.States.DEFAULT.value)
        return Response(resp_type='caption_too_long', data=data)

    # Поддерживаемые типы файлов:
    # Видео
    if c_type == 'video':
        file_id = message.json['video']['file_id']
        file_uniq_id = message.json['video']['file_unique_id']
    # Фото
    elif c_type == 'photo':
        file_id = message.json['photo'][-1]['file_id']
        file_uniq_id = message.json['photo'][-1]['file_unique_id']
    # Документ
    elif c_type == 'document':
        file_id = message.json['document']['file_id']
        file_uniq_id = message.json['document']['file_unique_id']
    # Если пришел текст или что-либо еще
    else:
        file_id = None
        file_uniq_id = None
    if message.forward_from_chat is not None:
        ff_id = message.forward_from_chat.id
        ff_title = message.forward_from_chat.title
        ff_username = message.forward_from_chat.username
    elif message.forward_from is not None:
        ff_id = message.forward_from.id
        last_name = message.forward_from.last_name if message.forward_from.last_name is not None else ''
        ff_title = ' '.join([message.forward_from.first_name, last_name])
        ff_username = message.forward_from.username
    else:
        ff_id = user.user_id
        last_name = user.last_name if user.last_name is not None else ''
        ff_title = ' '.join([user.first_name, last_name])
        ff_username = user.username

    if len(base.get_all_temp(user.user_id)) <= 10:
        base.add_temp_record(
            user_id=user.user_id,
            message_id=message.message_id,
            date=message.date,
            content_type=c_type,
            fw_date=message.forward_date,
            ffc_id=ff_id,
            ffc_title=ff_title,
            ffc_username=ff_username,
            message_text=message.html_text,
            caption=message.html_caption,
            file_id=file_id,
            file_uniq_id=file_uniq_id,
            media_group_id=message.media_group_id
        )
        data['success'] = True
    else:  # уже слишком много частей
        data['success'] = False
    return Response(resp_type='part_record', data=data)


def assemble_post_handler(message: Message, data: dict) -> Response:
    """ Сборка поста из 1 или более частей в temp """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    parts = base.get_all_temp(user.user_id)
    if len(parts) == 0:
        return Response(resp_type='no_temp')
    elif len(parts) == 1:  # Запись из 1 части
        if parts[0]['content_type'] == 'text':  # текст без вложений
            message_text = parts[0]['message_text']
            caption, att_photo, att_video, att_document = None, None, None, None
            attach_type = 'text'
        else:  # 1 вложение
            message_text = None
            caption = parts[0]['caption']
            attach_type = parts[0]['content_type']
            att_photo = parts[0]['file_id'] if attach_type == 'photo' else None
            att_video = parts[0]['file_id'] if attach_type == 'video' else None
            att_document = parts[0]['file_id'] if attach_type == 'document' else None
    else:  # несколько вложений
        message_text = None
        caption = extract_item(parts, 'caption')
        attach_type = 'media_group'
        att_photo = ','.join([part['file_id'] for part in parts if part['content_type'] == 'photo'])
        att_video = ','.join([part['file_id'] for part in parts if part['content_type'] == 'video'])
        att_document = ','.join([part['file_id'] for part in parts if part['content_type'] == 'document'])
    user_id = user.user_id
    ffc_id = parts[0]['ffc_id']
    ffc_username = parts[0]['ffc_username']
    ffc_title = parts[0]['ffc_title']
    if parts[0]['fw_date'] is not None:
        date = epoch_to_strftime(parts[0]['fw_date'])
    else:
        date = epoch_to_strftime(parts[0]['date'])
    date_saved = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    assembled = base.write_record(user_id=user_id,
                                  message_text=message_text,
                                  caption=caption,
                                  att_photo=att_photo,
                                  att_video=att_video,
                                  att_document=att_document,
                                  attach_type=attach_type,
                                  ffc_id=ffc_id,
                                  ffc_title=ffc_title,
                                  ffc_username=ffc_username,
                                  date=date,
                                  date_saved=date_saved)
    deleted = base.clear_temp(user_id=user_id)
    data['success'] = assembled and deleted
    post_db = base.get_post(user_id=user_id)
    data['post'] = Post(post_db)
    data['user'] = user
    base.write_current_record(user_id=user_id, post_id=data['post'].post_id)
    base.write_carousel_id(user_id=user_id, carousel_ids=[message.message_id + 1])
    return Response(resp_type='assembled_post', data=data)


def epoch_to_strftime(epoch: int) -> str:
    """
    :param epoch: UNIX-время (кол-во секунд с 01.01.1970 00:00)
    :return: Форматированное время ДД.ММ.ГГГГ
    """
    date = datetime.fromtimestamp(epoch, tz=pytz.timezone('Europe/Moscow'))
    return date.strftime('%d.%m.%Y %H:%M:%S')


def cancel_assemble(message: Message):
    """ Отмена сборки поста; удаление его из базы """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_id = base.get_user_state(user.user_id)['current_record']
    base.delete_post(user_id=user.user_id, post_id=post_id)
    return Response(resp_type='cancel_assembling')


def await_comment(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post = Post(base.get_post(user_id=user.user_id, post_id=base.get_user_state(user.user_id)['current_record']))
    data['post'] = post
    return Response(resp_type='await_comment', data=data)


def handle_comment(message: Message, data: dict) -> Response:
    """ Обрабатывает полученный комментарий записи """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_db = base.get_post(user_id=user.user_id, post_id=base.get_user_state(user.user_id)['current_record'])
    post = Post(post_db)
    symbols = 3800 if post.attach_type == 'text' else 800
    if len(message.text) > symbols - len(post.text):
        data['post'] = post
        data['success'] = False
        return Response(resp_type='handled_comment', data=data)
    added = base.edit_comment(user_id=user.user_id, post_id=post.post_id, comment=message.text)
    data['post'] = Post(base.get_post(user_id=user.user_id,
                                      post_id=base.get_user_state(user.user_id)['current_record']))
    data['success'] = added
    return Response(resp_type='handled_comment', data=data)


def remove_comment(message: Message, data: dict):
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_db = base.get_post(user_id=user.user_id, post_id=base.get_user_state(user.user_id)['current_record'])
    post = Post(post_db)
    removed = base.edit_comment(user_id=user.user_id, post_id=post.post_id, comment=None)
    data['post'] = Post(base.get_post(user_id=user.user_id,
                                      post_id=base.get_user_state(user.user_id)['current_record']))
    data['success'] = removed
    return Response(resp_type='handled_comment', data=data)


def choose_category(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    data['category']: list = base.get_user_categories(user.user_id).split(',')
    return Response(resp_type='choose_category', data=data)


def handle_category(call: CallbackQuery, data: dict) -> Response:
    """ Редактирование категории при сборке поста """
    user = User(call.message)
    base = SqlWorker(config.DB_FILE)
    data['success'] = base.edit_category(user_id=user.user_id,
                                         post_id=base.get_user_state(user.user_id)['current_record'],
                                         category=call.data)
    if call.data not in base.get_user_categories(user.user_id):
        data['success'] = False
    data['post'] = Post(base.get_post(user_id=user.user_id,
                                      post_id=base.get_user_state(user.user_id)['current_record']))
    return Response(resp_type='handled_category', data=data)


def confirm_post(message: Message, data: dict) -> Response:
    """ Обработка подтверждения поста """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_db = Post(base.get_post(user_id=user.user_id, post_id=base.get_user_state(user.user_id)['current_record']))
    data['category'] = post_db.category
    return Response(resp_type='confirm_post', data=data)


def look_handler(message: Message, data: dict) -> Response:
    """ Просмотр сохраненных категорий """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    categories: list = base.get_user_categories(user.user_id).split(',')
    data['category'] = [(cat, len(base.get_all_by_category(user.user_id, cat))) for cat in categories]
    return Response(resp_type='look_categories', data=data)


def look_records_handler(message: Message, data: dict) -> Response:
    """ Начало просмотра постов категории (с №1) """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    records = base.get_all_by_category(user_id=user.user_id, category=data['category'])
    if not records:
        return Response(resp_type='no_posts', data=data)
    records_ids = [record['id'] for record in records]
    base.write_records_id(user_id=user.user_id, id_list=records_ids)
    base.write_current_record(user_id=user.user_id, post_id=records_ids[0])
    post_db = base.get_post(user.user_id, records_ids[0])
    post = Post(post_db)
    data['post'] = post
    data['position'] = f'Стр. {records_ids.index(records_ids[0]) + 1} из {len(records_ids)}'
    return Response(resp_type='carousel', data=data)


def delete_category_warn(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    data['state'] = base.get_user_state(user.user_id)['state']
    base.write_current_category(user.user_id, data['category'])
    records = base.get_all_by_category(user_id=user.user_id, category=data['category'])
    data['length'] = len(records)
    return Response(resp_type='delete_warning', data=data)


def delete_category(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    if data['category'] == 'HELP':
        data['success'] = False
        return Response(resp_type='deleted_category', data=data)
    posts_deleted = base.delete_all_by_category(user_id=user.user_id, category=data['category'])
    categories = base.get_user_categories(user.user_id).split(',')
    categories.remove(data['category'])
    user.categories = ','.join(categories)
    categories_changed = base.add_user_categories(user=user)
    data['success'] = posts_deleted and categories_changed
    return Response(resp_type='deleted_category', data=data)


def choose_new_category_name(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    data['state'] = base.get_user_state(user.user_id)['state']
    base.write_current_category(user.user_id, data['category'])
    return Response(resp_type='new_category_name', data=data)


def rename_category(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    new = message.text
    old = data['category']
    if old == 'HELP' or len(new) > 20:
        data['success'] = False
    else:
        changed1 = base.change_category_of_posts(user_id=user.user_id, old_category=old, new_category=new)
        categories = base.get_user_categories(user.user_id).split(',')
        categories[categories.index(old)] = new
        user.categories = ','.join(categories)
        changed2 = base.add_user_categories(user=user)
        data['success'] = changed1 and changed2
    return Response(resp_type='renamed_category', data=data)


def carousel_handler(call: CallbackQuery, data: dict) -> Response:
    """ Обработка переключений страниц с постами текущей категории """
    user = User(call.message)
    base = SqlWorker(config.DB_FILE)
    try:
        records_ids = [int(i) for i in base.get_user_state(user.user_id)['records_id'].split(',')]
    except ValueError:
        return Response(resp_type='no_posts', data=data)
    current_record = base.get_user_state(user.user_id)['current_record']
    new_record = shift(records_ids, current_record, call.data)
    base.write_current_record(user_id=user.user_id, post_id=new_record)
    post_db = base.get_post(user.user_id, new_record)
    post = Post(post_db)
    data['post'] = post
    data['position'] = f'Стр. {records_ids.index(new_record) + 1} из {len(records_ids)}'
    return Response(resp_type='carousel', data=data)


def delete_post_warn(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    data['state'] = base.get_user_state(user.user_id)['state']
    return Response(resp_type='delete_post_warning', data=data)


def change_post_cancel(message: Message, data: dict) -> Response:
    return Response(resp_type='carousel', data=data)


def delete_post(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_id = base.get_user_state(user.user_id)['current_record']
    deleted: bool = base.delete_post(user_id=user.user_id, post_id=post_id)
    post_list = [int(i) for i in base.get_user_state(user.user_id)['records_id'].split(',')]
    new_record = shift(post_list, post_id, 'next')
    post_list.remove(post_id)
    base.write_records_id(user_id=user.user_id, id_list=post_list)
    base.write_current_record(user_id=user.user_id, post_id=new_record)
    post_db = base.get_post(user.user_id, new_record)
    if post_db is None:
        return Response(resp_type='no_posts', data=data)
    post = Post(post_db)
    data['post'] = post
    return Response(resp_type='carousel', data=data)


def replace_post(message: Message, data: dict) -> Response:
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    post_id = base.get_user_state(user.user_id)['current_record']
    replaced: bool = base.edit_category(user_id=user.user_id, post_id=post_id, category=data['category'])
    post_list = [int(i) for i in base.get_user_state(user.user_id)['records_id'].split(',')]
    new_record = shift(post_list, post_id, 'next')
    post_list.remove(post_id)   # Удаление поста из текущей "карусели"
    base.write_records_id(user_id=user.user_id, id_list=post_list)
    base.write_current_record(user_id=user.user_id, post_id=new_record)
    post_db = base.get_post(user.user_id, new_record)
    if post_db is None:
        return Response(resp_type='no_posts', data=data)
    post = Post(post_db)
    data['post'] = post
    return Response(resp_type='carousel', data=data)


def settings_handler(message: Message, data: dict):
    """ Переход в меню Настройки """
    user = User(message)
    base = SqlWorker(config.DB_FILE)
    return Response(resp_type='settings', data=data)


def settings_cancel(message: Message, data: dict):
    """ Закрытие меню Настройки """
    return Response(resp_type='start')


def extract_item(dicts: list[dict], key_: str):
    """ Извлекает первое не-None значение в списке словарей по определенному ключу """
    for item in dicts:
        if item[key_] is not None:
            return item[key_]
    return None


def assemble_comment(message: Message, post: Post) -> str:
    """ Прикрепление комментария к тексту поста """
    return '\n\n'.join([post.text, message.text])


def shift(items: list, current, direction: str):
    """ Возвращает элемент рядом с заданным в закольцованном списке """
    assert direction in ['prev', 'next']
    max_index = len(items) - 1
    current_index = items.index(current)
    if direction == 'prev':
        new_index = current_index - 1 if current_index != 0 else max_index
    elif direction == 'next':
        new_index = current_index + 1 if current_index != max_index else 0
    else:
        new_index = 0
    return items[new_index]


def define_carousel_ids(message: Message, response: Response) -> list:
    """ Определяет список id сообщений, в дальнейшем подлежащих удалению """
    additional_msg_amount = 1
    if response.attachment is not None:
        return list(range(message.message_id + 1,
                          message.message_id + 1 + len(response.attachment) + additional_msg_amount))
    else:
        return [message.message_id + 1, message.message_id + 1 + additional_msg_amount]


def help_fill(user_id: str):
    """ Добавляет пользователю заранее сконфигурированные HELP-посты """
    base = SqlWorker(config.DB_FILE)
    for help_post in config.HELP_POSTS:
        base.write_record(user_id=user_id,
                          message_text=help_post['message_text'],
                          caption=help_post['caption'],
                          att_photo=help_post['att_photo'],
                          att_video=help_post['att_video'],
                          att_document=help_post['att_document'],
                          attach_type=help_post['attach_type'],
                          ffc_title=help_post['ffc_title'],
                          ffc_username=help_post['ffc_username'],
                          category=help_post['category'])
