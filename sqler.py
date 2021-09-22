import sqlite3
from typing import Optional
from frame import User
from config import ps_logger, time_it


class SqlWorker:
    """ Класс для работы с SQLite """

    def __init__(self, database):
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = self.dict_factory
        self.cursor = self.connection.cursor()

        # --- Ускорение транзакций ------------------------
        self.cursor.execute("""PRAGMA synchronous = 0""")  # (!) Риск повреждения базы при сбое питания
        self.cursor.execute("""PRAGMA temp_store = MEMORY""")

    @staticmethod
    def dict_factory(cursor, row) -> dict:
        """ Оформляет ответ БД в виде словаря """
        d = {}
        for index, column in enumerate(cursor.description):
            d[column[0]] = row[index]
        return d

    def get_user(self, user_id: str) -> Optional[dict]:
        """ Получение данных о пользователе по id """
        with self.connection:
            query = "SELECT id, user_id, username, first_name, last_name, categories FROM users WHERE user_id = ?"
            values = (user_id,)
            try:
                self.cursor.execute(query, values)
                return self.cursor.fetchone()
            except Exception as e:
                ps_logger.exception(f'Cannot get user (id {user_id}) => ({e})')

    def get_all_users(self) -> list:
        with self.connection:
            query = "SELECT id, user_id, username, first_name, last_name, categories FROM users"
            try:
                self.cursor.execute(query)
                return self.cursor.fetchall()
            except Exception as e:
                ps_logger.exception(f'Cannot get all users => ({e})')
                return []

    def add_user(self, user: User) -> bool:
        """ Добавление нового пользователя в базу """
        with self.connection:
            query = "INSERT INTO users ('user_id', 'username', 'first_name', 'last_name', 'categories') " \
                    "VALUES (?, ?, ?, ?, ?)"
            values = (user.user_id, user.username, user.first_name, user.last_name, user.categories)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot add new user (username @{user.username}) => ({e})')
                return False

    def check_table(self, table_name: str) -> bool:
        """ Проверка существования таблицы в БД """
        with self.connection:
            query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            try:
                self.cursor.execute(query)
                return self.cursor.fetchone() is not None  # False, если таблицы не существует
            except Exception as e:
                ps_logger.exception(f'Cannot confirm the existence of the table "{table_name}" => ({e})')
                return False

    @time_it
    def add_user_temp(self, user_id: str) -> bool:
        """ Создание персональной таблицы пользователя для хранения необработанного поста  """
        with self.connection:
            query = f"""CREATE TABLE '{user_id}_temp' 
                    (id INTEGER primary key autoincrement unique not null,
                    message_id INTEGER not null,
                    date INTEGER not null,
                    fw_date INTEGER,
                    ffc_id TEXT,
                    ffc_title TEXT,
                    ffc_username TEXT,
                    content_type TEXT,
                    message_text TEXT,
                    caption TEXT,
                    file_id TEXT,
                    file_uniq_id TEXT,
                    media_group_id TEXT)"""
            try:
                self.cursor.execute(query)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to create table "{user_id}_temp" => ({e})')
                return False

    @time_it
    def add_user_storage(self, user_id: str) -> bool:
        """ Создание персональной таблицы пользователя для хранения его постов """
        with self.connection:
            query = f"""CREATE TABLE '{user_id}_storage' 
                    (id INTEGER primary key autoincrement unique not null,
                    message_text TEXT,
                    caption TEXT,
                    att_photo TEXT,
                    att_video TEXT,
                    att_document TEXT,
                    attach_type TEXT,
                    ffc_id TEXT,
                    ffc_title TEXT,
                    ffc_username TEXT,
                    date INTEGER,
                    date_saved DATETIME,
                    comment TEXT,
                    category TEXT)"""
            try:
                self.cursor.execute(query)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to create table "{user_id}_storage" => ({e})')
                return False

    def get_user_categories(self, user_id: str) -> str:
        """ Получение сохраненных пользователем категорий """
        with self.connection:
            query = "SELECT categories FROM users WHERE user_id = ?"
            values = (user_id,)
            try:
                self.cursor.execute(query, values)
                return self.cursor.fetchone()['categories']
            except Exception as e:
                ps_logger.exception(f'Cannot get categories for user {user_id} => ({e})')
                return ''

    def add_user_categories(self, user: User) -> bool:
        """ Обновление списка сохраненных юзером категорий """
        with self.connection:
            query = "UPDATE users SET categories = ? WHERE user_id = ?"
            values = (user.categories, user.user_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot add categories for user {user.user_id} => ({e})')
                return False

    def add_temp_record(self, user_id: str, message_id: int, date: int, content_type, fw_date: int = None,
                        ffc_id: str = None, ffc_title: str = None, ffc_username: str = None,
                        message_text: str = None, caption: str = None, file_id: str = None, file_uniq_id: str = None,
                        media_group_id: str = None) -> bool:
        """ Запись в temp-таблицу пользователя поста или частей поста с медиагруппой """
        with self.connection:
            query = f"""INSERT INTO '{user_id}_temp' ('message_id', 'date', 'content_type', 'fw_date',
                    'ffc_id', 'ffc_title', 'ffc_username', 'message_text', 'caption', 'file_id',
                    'file_uniq_id', 'media_group_id') VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
            values = (message_id, date, content_type, fw_date, ffc_id, ffc_title, ffc_username, message_text, caption,
                      file_id, file_uniq_id, media_group_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot add temporary record for user {user_id} => ({e})')
                return False

    @time_it
    def get_all_temp(self, user_id: str) -> list:
        """ Получение всех записей в temp-таблице пользователя """
        with self.connection:
            query = f"SELECT * FROM '{user_id}_temp'"
            try:
                self.cursor.execute(query)
                return self.cursor.fetchall()
            except Exception as e:
                ps_logger.exception(f'Cannot get all temporary records for user {user_id} => ({e})')
                return []

    def clear_temp(self, user_id: str) -> bool:
        """ Очистка temp-таблицы """
        with self.connection:
            query = f"DELETE FROM '{user_id}_temp'"
            try:
                self.cursor.execute(query)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot clear table {user_id}_temp => ({e})')
                return False

    @time_it
    def write_record(self, user_id: str, message_text: str = None, caption: str = None, att_photo: str = None,
                     att_video: str = None, att_document: str = None, attach_type: str = None, ffc_id: str = None,
                     ffc_title: str = None, ffc_username: str = None, date: str = None, date_saved: str = None,
                     comment: str = None, category: str = None) -> bool:
        """ Записывает пост в постоянное хранилище пользователя """
        with self.connection:
            query = f"""INSERT INTO '{user_id}_storage' ('message_text', 'caption', 'att_photo',
                    'att_video', 'att_document', 'attach_type', 'ffc_id', 'ffc_title', 'ffc_username',
                    'date', 'date_saved', 'comment', 'category') VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            values = (message_text, caption, att_photo, att_video, att_document, attach_type, ffc_id, ffc_title,
                      ffc_username, date, date_saved, comment, category)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to write post for user {user_id} => ({e})')
                return False

    def get_post(self, user_id: str, post_id: int = None) -> Optional[dict]:
        """ Получение сохраненного поста (по id или последний сохраненный) """
        with self.connection:
            try:
                if post_id is None:
                    self.cursor.execute(f"""SELECT * FROM '{user_id}_storage' ORDER BY id DESC LIMIT 1""")
                else:
                    self.cursor.execute(f"""SELECT * FROM '{user_id}_storage' WHERE id = ?""", (post_id,))
                return self.cursor.fetchone()
            except Exception as e:
                ps_logger.exception(f'Failed to get post {post_id} for user {user_id} => ({e})')
                return None

    def delete_post(self, user_id: int, post_id: int) -> bool:
        """ Удаление поста пользователя по id """
        with self.connection:
            query = f"DELETE FROM '{user_id}_storage' WHERE id = ?"
            values = (post_id,)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to delete post {post_id} for user {user_id} => ({e})')
                return False

    def edit_comment(self, user_id: int, post_id: int, comment) -> bool:
        """ Обновление поля комментария к посту пользователя """
        with self.connection:
            query = f"UPDATE '{user_id}_storage' SET comment = ? WHERE id = ?"
            values = (comment, post_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to edit comment field (user {user_id}, post {post_id}) => ({e})')
                return False

    def edit_category(self, user_id: int, post_id: int, category: str) -> bool:
        """ Обновление категории поста пользователя """
        with self.connection:
            query = f"UPDATE '{user_id}_storage' SET category = ? WHERE id = ?"
            values = (category, post_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to edit category field (user {user_id}, post {post_id}) => ({e})')
                return False

    def get_all_by_category(self, user_id: str, category: str) -> list:
        """ Получение всех постов пользователя из данной категории """
        with self.connection:
            query = f"SELECT * FROM '{user_id}_storage' WHERE category = ?"
            values = (category,)
            try:
                self.cursor.execute(query, values)
                return self.cursor.fetchall()
            except Exception as e:
                ps_logger.exception(f'Cannot get all posts of "{category}" category for user {user_id} => ({e})')
                return []

    def delete_all_by_category(self, user_id: str, category: str) -> bool:
        with self.connection:
            query = f"DELETE FROM '{user_id}_storage' WHERE category = ?"
            values = (category,)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot delete all posts of "{category}" category for user {user_id} => ({e})')
                return False

    def change_category_of_posts(self, user_id: str, old_category: str, new_category: str) -> bool:
        with self.connection:
            query = f"UPDATE '{user_id}_storage' SET category = ? WHERE category = ?"
            values = (new_category, old_category)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot change [{old_category} -> {new_category}] for user {user_id} => ({e})')
                return False

    def get_user_state(self, user_id: int) -> dict:
        """ Возвращает всю информацию о состоянии диалога с юзером """
        with self.connection:
            query = "SELECT * FROM temp WHERE user_id = ?"
            values = (str(user_id),)
            try:
                self.cursor.execute(query, values)
                return self.cursor.fetchone()
            except Exception as e:
                ps_logger.exception(f'Cannot get state for user {user_id} => ({e})')
                return {}

    def write_user_in_state_table(self, user_id: str, state: str) -> bool:
        with self.connection:
            query = "INSERT INTO temp ('user_id', 'state') VALUES (?, ?)"
            values = (user_id, state)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Failed to write user {user_id} in temp table => ({e})')
                return False

    def set_state(self, user_id: int, state: str = '1') -> bool:
        with self.connection:
            query = "UPDATE temp SET state = ? WHERE user_id = ?"
            values = (state, str(user_id))
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot set state {state} for user {user_id} => ({e})')
                return False

    def write_records_id(self, user_id: str, id_list: list[int]) -> bool:
        id_list_str = ','.join([str(i) for i in id_list])
        with self.connection:
            query = "UPDATE temp SET records_id = ? WHERE user_id = ?"
            values = (id_list_str, user_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot write records_ids for user {user_id} => ({e})')
                return False

    def write_current_record(self, user_id: str, post_id: int) -> bool:
        with self.connection:
            query = "UPDATE temp SET current_record = ? WHERE user_id = ?"
            values = (str(post_id), user_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot write current record {post_id} for user {user_id} => ({e})')
                return False

    def write_carousel_id(self, user_id: int, carousel_ids: list[int]) -> bool:
        with self.connection:
            query = "UPDATE temp SET carousel_id = ? WHERE user_id = ?"
            values = (','.join([str(i) for i in carousel_ids]), str(user_id))
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot write carousel ids for user {user_id} => ({e})')
                return False

    def write_post_length(self, user_id: str, length: int) -> bool:
        with self.connection:
            query = "UPDATE temp SET post_length = ? WHERE user_id = ?"
            values = (str(length), user_id)
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot write post length for user {user_id} => ({e})')
                return False

    def write_current_category(self, user_id: int, category: str) -> bool:
        with self.connection:
            query = "UPDATE temp SET current_category = ? WHERE user_id = ?"
            values = (category, str(user_id))
            try:
                self.cursor.execute(query, values)
                self.connection.commit()
                return True
            except Exception as e:
                ps_logger.exception(f'Cannot write current category for user {user_id} => ({e})')
                return False
