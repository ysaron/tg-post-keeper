from vedis import Vedis
from config import States, Storages, ps_logger


def get_current_state(user_id: str) -> str:
    """
    Пытаемся узнать из базы текущее состояние юзера
    :param user_id: id чата с юзером
    :return: (str(int)) текущее состояние юзера
    """
    with Vedis(Storages.STATEFILE) as vdb:
        try:
            return vdb[user_id].decode()
        except KeyError:                     # Если такого юзера не оказалось
            return States.NULL.value         # Нулевое значение - начало диалога


def set_state(user_id: str, value: str) -> bool:
    """
    Смена состояния на желаемое, запись нового состояния в базу
    :param user_id: id чата с юзером
    :param value: (str(int)) состояние
    :return: True / False
    """
    with Vedis(Storages.STATEFILE) as vdb:
        try:
            vdb[user_id] = value
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot set state {value} for user {user_id} => ({e})')
            return False


def write_records_id(user_id: str, id_list: list) -> bool:
    """ Записывает в Vedis юзеру список id (в БД) постов текущей категории"""
    with Vedis(Storages.RECORDS) as vdb:
        try:
            vdb[user_id] = ','.join([str(i) for i in id_list])
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot write id-list {id_list} for user {user_id} => ({e})')
            return False


def get_records_id(user_id: str) -> list:
    """ Получает список id всех постов текущей категории для данного юзера """
    with Vedis(Storages.RECORDS) as vdb:
        try:
            return [int(i) for i in vdb[user_id].decode().split(',')]
        except Exception as e:
            ps_logger.exception(f'Cannot get id-list for user {user_id} => ({e})')
            return []


def write_current_record(user_id: str, post_id: int) -> bool:
    """ Записывает в Vedis юзеру id поста, отображаемого в данный момент """
    with Vedis(Storages.CURRENT_RECORD) as vdb:
        try:
            vdb[user_id] = str(post_id)
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot write current_post_id for user {user_id} => ({e})')
            return False


def get_current_record(user_id: str) -> int:
    """ Получает id (в БД) отображаемого в данный момент поста данного юзера """
    with Vedis(Storages.CURRENT_RECORD) as vdb:
        try:
            return int(vdb[user_id].decode())
        except Exception as e:
            ps_logger.exception(f'Cannot get current record for user {user_id} => ({e})')
            return 0


def write_carousel_id(user_id: str, carousel_ids: list[int]) -> bool:
    """ Записывает в Vedis юзеру id Telegram-сообщения с "каруселью", отображающей записи """
    with Vedis(Storages.CAROUSEL) as vdb:
        try:
            vdb[user_id] = ','.join(str(i) for i in carousel_ids)
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot write carousel id {carousel_ids} for user {user_id} => ({e})')
            return False


def get_carousel_id(user_id: str) -> list[int]:
    """ Получает id поста в Telegram с "каруселью", отображающей записи """
    with Vedis(Storages.CAROUSEL) as vdb:
        try:
            return [int(i) for i in vdb[user_id].decode().split(',')]
        except Exception as e:
            ps_logger.exception(f'Cannot get carousel id for user {user_id} => ({e})')
            return []


def write_post_length(user_id: str, length: int) -> bool:
    """ Записывает в Vedis юзеру длину отправляемого поста (кол-во вложений) """
    with Vedis(Storages.RECORD_LENGTH) as vdb:
        try:
            vdb[user_id] = str(length)
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot write length of post for user {user_id} => ({e})')
            return False


def get_post_length(user_id: str):
    """ Получает длину текущего поста (кол-во вложений) """
    with Vedis(Storages.RECORD_LENGTH) as vdb:
        try:
            return int(vdb[user_id].decode())
        except Exception as e:
            ps_logger.exception(f'Cannot get length of post for user {user_id} => ({e})')
            return


def get_current_category(user_id: str) -> str:
    """  """
    with Vedis(Storages.CATEGORY) as vdb:
        try:
            return vdb[user_id].decode()
        except KeyError:
            return 'unknown'


def write_current_category(user_id: str, category: str) -> bool:
    """  """
    with Vedis(Storages.CATEGORY) as vdb:
        try:
            vdb[user_id] = category
            return True
        except Exception as e:
            ps_logger.exception(f'Cannot write category {category} as current for user {user_id} => ({e})')
            return False
