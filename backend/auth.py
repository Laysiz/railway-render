import json
import os
import uuid
import hashlib
import base64
import jwt
from datetime import datetime , timedelta
from functools import wraps
from flask import request , jsonify , g
from config import Config

# Путь к файлу с пользователями
USERS_FILE = "users.json"


class PasswordManager :
    """Класс для шифрования и хеширования паролей"""

    def __init__ ( self ) :
        pass

    def hash_password ( self , password: str ) -> str :
        """Хеширует пароль с солью"""
        salt = b'railway_system_salt_2024'
        dk = hashlib.pbkdf2_hmac ( 'sha256' , password.encode ( ) , salt , 100000 )
        return base64.b64encode ( dk ).decode ( )


class UserManager :
    """Менеджер пользователей для веб-версии"""

    def __init__ ( self ) :
        self.password_manager = PasswordManager ( )
        self.users_file = USERS_FILE
        self.load_users ( )

    def load_users ( self ) :
        """Загружает пользователей из файла"""
        if os.path.exists ( self.users_file ) :
            try :
                with open ( self.users_file , 'r' , encoding = 'utf-8' ) as f :
                    self.users = json.load ( f )
                print ( f"✅ Загружено {len ( self.users )} пользователей" )

                # Добавляем отсутствующие ID старым пользователям
                updated = False
                for user in self.users :
                    if 'id' not in user :
                        user [ 'id' ] = str ( uuid.uuid4 ( ) )
                        updated = True
                    if 'full_name' not in user :
                        user [ 'full_name' ] = user.get ( 'login' , 'Пользователь' )
                        updated = True
                    if 'is_active' not in user :
                        user [ 'is_active' ] = True
                        updated = True

                if updated :
                    self.save_users ( )
                    print ( "✅ Обновлены устаревшие записи пользователей" )

            except Exception as e :
                print ( f"❌ Не удалось загрузить пользователей: {e}" )
                self.users = [ ]
                self.create_default_admin ( )
        else :
            self.users = [ ]
            self.create_default_admin ( )

    def create_default_admin ( self ) :
        """Создает администратора по умолчанию"""
        default_admin = {
            "id" : str ( uuid.uuid4 ( ) ) ,
            "login" : "admin" ,
            "password" : self.password_manager.hash_password ( "admin123" ) ,
            "role" : "Администратор" ,
            "full_name" : "Системный администратор" ,
            "created_at" : datetime.now ( ).isoformat ( ) ,
            "is_active" : True
        }
        self.users.append ( default_admin )
        self.save_users ( )
        print ( "✅ Создан пользователь по умолчанию: admin/admin123" )

    def save_users ( self ) :
        """Сохраняет пользователей в файл"""
        try :
            with open ( self.users_file , 'w' , encoding = 'utf-8' ) as f :
                json.dump ( self.users , f , ensure_ascii = False , indent = 2 )
            return True
        except Exception as e :
            print ( f"❌ Ошибка сохранения пользователей: {e}" )
            return False

    def authenticate ( self , login: str , password: str ) :
        """Аутентификация пользователя"""
        for user in self.users :
            if user [ 'login' ] == login and user.get ( 'is_active' , True ) :
                hashed_input = self.password_manager.hash_password ( password )
                if user [ 'password' ] == hashed_input :
                    user [ 'last_login' ] = datetime.now ( ).isoformat ( )
                    self.save_users ( )

                    return {
                        "id" : user.get ( 'id' , str ( uuid.uuid4 ( ) ) ) ,
                        "login" : user.get ( 'login' , login ) ,
                        "role" : user.get ( 'role' , 'Электроник' ) ,
                        "full_name" : user.get ( 'full_name' , login )
                    }
        return None

    def get_user_by_id ( self , user_id: str ) :
        """Возвращает пользователя по ID"""
        for user in self.users :
            if user [ 'id' ] == user_id :
                return user
        return None

    def get_all_users ( self ) :
        """Возвращает всех пользователей"""
        return self.users

    def add_user ( self , login: str , password: str , role: str , full_name: str = "" ) :
        """Добавляет нового пользователя"""
        if any ( user [ 'login' ] == login for user in self.users ) :
            return False

        if role not in [ "Электроник" , "ПЭМ" , "Администратор" , "Инженер" , "Руководитель" ] :
            return False

        hashed_password = self.password_manager.hash_password ( password )

        user = {
            "id" : str ( uuid.uuid4 ( ) ) ,
            "login" : login ,
            "password" : hashed_password ,
            "role" : role ,
            "full_name" : full_name or login ,
            "created_at" : datetime.now ( ).isoformat ( ) ,
            "last_login" : None ,
            "is_active" : True
        }

        self.users.append ( user )
        self.save_users ( )
        return True

    def edit_user ( self , user_id: str , **kwargs ) :
        """Редактирует существующего пользователя"""
        user_index = -1
        for i , user in enumerate ( self.users ) :
            if user [ 'id' ] == user_id :
                user_index = i
                break

        if user_index == -1 :
            return False

        user = self.users [ user_index ]

        if 'login' in kwargs and kwargs [ 'login' ] != user [ 'login' ] :
            if any ( u [ 'login' ] == kwargs [ 'login' ] for u in self.users if u [ 'id' ] != user_id ) :
                return False

        if 'role' in kwargs and kwargs [ 'role' ] not in [ "Электроник" , "ПЭМ" , "Администратор" , "Инженер" ,
                                                           "Руководитель" ] :
            return False

        if 'password' in kwargs and kwargs [ 'password' ] :
            kwargs [ 'password' ] = self.password_manager.hash_password ( kwargs [ 'password' ] )

        for key , value in kwargs.items ( ) :
            if value is not None :
                user [ key ] = value

        user [ 'updated_at' ] = datetime.now ( ).isoformat ( )
        self.save_users ( )
        return True

    def delete_user ( self , user_id: str ) :
        """Деактивирует пользователя"""
        for user in self.users :
            if user [ 'id' ] == user_id :
                user [ 'is_active' ] = False
                user [ 'deleted_at' ] = datetime.now ( ).isoformat ( )
                self.save_users ( )
                return True
        return False

    def activate_user ( self , user_id: str ) :
        """Активирует пользователя"""
        for user in self.users :
            if user [ 'id' ] == user_id :
                user [ 'is_active' ] = True
                user.pop ( 'deleted_at' , None )
                self.save_users ( )
                return True
        return False


# Создаем глобальный экземпляр менеджера пользователей
user_manager = UserManager ( )


# Функции для работы с JWT токенами
def generate_token ( user_data ) :
    """Генерирует JWT токен для пользователя"""
    payload = {
        'user_id' : user_data [ 'id' ] ,
        'login' : user_data [ 'login' ] ,
        'role' : user_data [ 'role' ] ,
        'full_name' : user_data [ 'full_name' ] ,
        'exp' : datetime.utcnow ( ) + timedelta ( days = 1 )
    }
    return jwt.encode ( payload , Config.JWT_SECRET , algorithm = 'HS256' )


def verify_token ( token ) :
    """Проверяет JWT токен"""
    try :
        payload = jwt.decode ( token , Config.JWT_SECRET , algorithms = [ 'HS256' ] )
        return payload
    except jwt.ExpiredSignatureError :
        return None
    except jwt.InvalidTokenError :
        return None


def token_required ( f ) :
    """Декоратор для проверки JWT токена"""

    @wraps ( f )
    def decorated ( *args , **kwargs ) :
        token = None

        # Получаем токен из заголовка
        if 'Authorization' in request.headers :
            auth_header = request.headers [ 'Authorization' ]
            if auth_header.startswith ( 'Bearer ' ) :
                token = auth_header [ 7 : ]

        if not token :
            return jsonify ( { 'success' : False , 'message' : 'Токен не предоставлен' } ) , 401

        payload = verify_token ( token )
        if not payload :
            return jsonify ( { 'success' : False , 'message' : 'Недействительный или просроченный токен' } ) , 401

        # Добавляем информацию о пользователе в g
        g.user = payload
        g.user_info = {
            'id' : payload [ 'user_id' ] ,
            'login' : payload [ 'login' ] ,
            'role' : payload [ 'role' ] ,
            'full_name' : payload [ 'full_name' ]
        }

        return f ( *args , **kwargs )

    return decorated


def role_required ( permission ) :
    """Декоратор для проверки прав доступа"""

    def decorator ( f ) :
        @wraps ( f )
        def decorated ( *args , **kwargs ) :
            user_role = g.user.get ( 'role' , 'Электроник' )

            permissions = {
                "Администратор" : [
                    "view_trains" , "edit_trains" , "delete_trains" ,
                    "view_wagons" , "edit_wagons" , "delete_wagons" ,
                    "view_requests" , "create_requests" , "edit_requests" , "delete_requests" ,
                    "view_comments" , "create_comments" , "edit_comments" , "delete_comments" ,
                    "view_detached" , "restore_detached" , "delete_detached" ,
                    "manage_users" , "view_all_data" , "export_data" ,
                    "import_data"
                ] ,
                "Руководитель" : [
                    "view_trains" , "edit_trains" , "delete_trains" ,
                    "view_wagons" , "edit_wagons" , "delete_wagons" ,
                    "view_requests" , "create_requests" , "edit_requests" ,
                    "view_comments" , "create_comments" , "edit_comments" ,
                    "view_detached" , "restore_detached" ,
                    "view_all_data" , "export_data"
                ] ,
                "Инженер" : [
                    "view_trains" , "view_wagons" ,
                    "view_requests" , "create_requests" , "edit_requests" ,
                    "view_comments" , "create_comments" ,
                    "view_detached"
                ] ,
                "ПЭМ" : [
                    "view_trains" , "view_wagons" ,
                    "view_requests" , "create_requests" ,
                    "view_comments" , "create_comments"
                ] ,
                "Электроник" : [
                    "view_trains" , "view_wagons" ,
                    "view_requests" , "create_requests" ,
                    "view_comments" , "create_comments"
                ]
            }

            if permission not in permissions.get ( user_role , [ ] ) :
                return jsonify ( { 'success' : False , 'message' : 'Недостаточно прав' } ) , 403

            return f ( *args , **kwargs )

        return decorated

    return decorator