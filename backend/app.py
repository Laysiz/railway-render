import sys
import os
from flask import Flask , request , jsonify , send_from_directory
from flask_cors import CORS
from datetime import datetime , date
from database import SupabaseDatabase
from auth import user_manager , generate_token , token_required , role_required
from config import Config

print("=" * 50)
print("🚂 STARTING RAILWAY MANAGEMENT SYSTEM")
print("=" * 50)
print(f"Current directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")
print(f"Python path: {sys.path}")
print("=" * 50)

try:
    from flask import Flask
    print("✅ Flask imported successfully")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    
app = Flask ( __name__ , static_folder = '../frontend' , static_url_path = '' )
app.config [ 'SECRET_KEY' ] = Config.SECRET_KEY
CORS ( app )

# Инициализируем базу данных
db = SupabaseDatabase ( )


# ------------------------------------------------------------------------
# СЕРВИРОВАНИЕ ФРОНТЕНДА
# ------------------------------------------------------------------------

@app.route ( '/' )
def serve_index ( ) :
    return send_from_directory ( '../frontend' , 'index.html' )


@app.route ( '/<path:path>' )
def serve_frontend ( path ) :
    if path.startswith ( 'api/' ) :
        return jsonify ( { 'error' : 'Not found' } ) , 404
    return send_from_directory ( '../frontend' , path )


# ------------------------------------------------------------------------
# МАРШРУТЫ ДЛЯ АУТЕНТИФИКАЦИИ
# ------------------------------------------------------------------------

@app.route ( '/api/auth/login' , methods = [ 'POST' ] )
def login ( ) :
    """Вход в систему"""
    data = request.json
    login = data.get ( 'login' )
    password = data.get ( 'password' )

    if not login or not password :
        return jsonify ( { 'success' : False , 'message' : 'Введите логин и пароль' } ) , 400

    user = user_manager.authenticate ( login , password )
    if not user :
        return jsonify ( { 'success' : False , 'message' : 'Неверный логин или пароль' } ) , 401

    token = generate_token ( user )

    return jsonify ( {
        'success' : True ,
        'token' : token ,
        'user' : user
    } )


@app.route ( '/api/auth/me' , methods = [ 'GET' ] )
@token_required
def get_current_user ( ) :
    """Получает информацию о текущем пользователе"""
    return jsonify ( {
        'success' : True ,
        'user' : g.user_info
    } )


# ------------------------------------------------------------------------
# МАРШРУТЫ ДЛЯ ПОЕЗДОВ
# ------------------------------------------------------------------------

@app.route ( '/api/trains' , methods = [ 'GET' ] )
@token_required
def get_trains ( ) :
    """Получает список всех поездов"""
    date_param = request.args.get ( 'date' )

    if date_param :
        try :
            selected_date = datetime.strptime ( date_param , '%Y-%m-%d' ).date ( )
            trains = db.fetch_trains_by_date ( selected_date )
        except :
            return jsonify ( { 'success' : False , 'message' : 'Неверный формат даты' } ) , 400
    else :
        trains = db.fetch_trains ( )

    return jsonify ( { 'success' : True , 'trains' : trains } )


@app.route ( '/api/trains' , methods = [ 'POST' ] )
@token_required
@role_required ( 'edit_trains' )
def add_train ( ) :
    """Добавляет новый поезд"""
    data = request.json
    name = data.get ( 'name' )
    pem_fio = data.get ( 'pem_fio' , '' )
    depot_date = data.get ( 'depot_date' )
    trip_days = data.get ( 'trip_days' , 7 )

    if not name :
        return jsonify ( { 'success' : False , 'message' : 'Введите название поезда' } ) , 400

    if depot_date :
        try :
            depot_date = datetime.strptime ( depot_date , '%Y-%m-%d' ).date ( )
        except :
            return jsonify ( { 'success' : False , 'message' : 'Неверный формат даты' } ) , 400
    else :
        depot_date = date.today ( )

    result = db.add_train ( name , pem_fio , depot_date , trip_days )

    if result.get ( 'success' ) :
        db._log_audit ( "add_train" , f"Добавлен поезд: {name}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/trains/<train_id>' , methods = [ 'PUT' ] )
@token_required
@role_required ( 'edit_trains' )
def update_train ( train_id ) :
    """Обновляет данные поезда"""
    data = request.json
    name = data.get ( 'name' )
    pem_fio = data.get ( 'pem_fio' , '' )
    depot_date = data.get ( 'depot_date' )
    trip_days = data.get ( 'trip_days' )

    if not name :
        return jsonify ( { 'success' : False , 'message' : 'Введите название поезда' } ) , 400

    if depot_date :
        try :
            depot_date = datetime.strptime ( depot_date , '%Y-%m-%d' ).date ( )
        except :
            return jsonify ( { 'success' : False , 'message' : 'Неверный формат даты' } ) , 400

    result = db.update_train ( train_id , name , pem_fio , depot_date , trip_days )

    if result.get ( 'success' ) :
        db._log_audit ( "update_train" , f"Обновлен поезд ID: {train_id}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/trains/<train_id>' , methods = [ 'DELETE' ] )
@token_required
@role_required ( 'delete_trains' )
def delete_train ( train_id ) :
    """Удаляет поезд"""
    result = db.delete_train ( train_id )

    if result.get ( 'success' ) :
        db._log_audit ( "delete_train" , f"Удален поезд ID: {train_id}" , g.user_info )

    return jsonify ( result )


# ------------------------------------------------------------------------
# МАРШРУТЫ ДЛЯ ВАГОНОВ
# ------------------------------------------------------------------------

@app.route ( '/api/trains/<train_id>/wagons' , methods = [ 'GET' ] )
@token_required
def get_wagons ( train_id ) :
    """Получает вагоны для поезда"""
    wagons = db.fetch_wagons_for_train ( train_id )
    return jsonify ( { 'success' : True , 'wagons' : wagons } )


@app.route ( '/api/trains/<train_id>/wagons' , methods = [ 'POST' ] )
@token_required
@role_required ( 'edit_wagons' )
def add_wagon ( train_id ) :
    """Добавляет вагон в поезд"""
    data = request.json
    number = data.get ( 'number' )
    wagon_type = data.get ( 'type' )

    if not number or not wagon_type :
        return jsonify ( { 'success' : False , 'message' : 'Заполните все поля' } ) , 400

    result = db.add_wagon ( train_id , number , wagon_type )

    if result.get ( 'success' ) :
        db._log_audit ( "add_wagon" , f"Добавлен вагон #{number}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/wagons/<wagon_id>' , methods = [ 'DELETE' ] )
@token_required
@role_required ( 'delete_wagons' )
def delete_wagon ( wagon_id ) :
    """Удаляет вагон"""
    result = db.delete_wagon ( wagon_id )

    if result.get ( 'success' ) :
        db._log_audit ( "delete_wagon" , f"Удален вагон ID: {wagon_id}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/wagons/<wagon_id>/systems' , methods = [ 'PUT' ] )
@token_required
@role_required ( 'edit_wagons' )
def update_wagon_systems ( wagon_id ) :
    """Обновляет системы вагона"""
    data = request.json
    systems = data.get ( 'systems' , { } )
    has_systems = data.get ( 'has_systems' , { } )
    comment = data.get ( 'comment' , '' )

    result = db.update_wagon_systems ( wagon_id , systems , has_systems , comment )

    if result.get ( 'success' ) :
        db._log_audit ( "update_wagon_systems" , f"Обновлены системы вагона ID: {wagon_id}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/wagons/search' , methods = [ 'GET' ] )
@token_required
def search_wagon ( ) :
    """Ищет вагон по номеру"""
    wagon_number = request.args.get ( 'number' , '' )

    if not wagon_number :
        return jsonify ( { 'success' : False , 'message' : 'Введите номер вагона' } ) , 400

    results = db.search_wagon_by_number ( wagon_number )
    return jsonify ( { 'success' : True , 'results' : results } )


# ------------------------------------------------------------------------
# МАРШРУТЫ ДЛЯ ЗАЯВОК
# ------------------------------------------------------------------------

@app.route ( '/api/wagons/<wagon_id>/requests' , methods = [ 'GET' ] )
@token_required
def get_requests_for_wagon ( wagon_id ) :
    """Получает заявки для вагона"""
    requests = db.fetch_requests_for_wagon ( wagon_id )
    return jsonify ( { 'success' : True , 'requests' : requests } )


@app.route ( '/api/wagons/<wagon_id>/requests' , methods = [ 'POST' ] )
@token_required
@role_required ( 'create_requests' )
def create_request ( wagon_id ) :
    """Создает новую заявку"""
    data = request.json
    pem_type = data.get ( 'pem_type' )
    system = data.get ( 'system' )
    description = data.get ( 'description' )

    if not pem_type or not system or not description :
        return jsonify ( { 'success' : False , 'message' : 'Заполните все поля' } ) , 400

    result = db.create_request (
        wagon_id ,
        pem_type ,
        system ,
        description ,
        g.user_info [ 'full_name' ] ,
        g.user_info [ 'role' ]
    )

    if result.get ( 'success' ) :
        db._log_audit ( "create_request" , f"Создана заявка №{result.get ( 'request_number' )}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/requests/<request_id>/comments' , methods = [ 'GET' ] )
@token_required
def get_comments ( request_id ) :
    """Получает комментарии к заявке"""
    comments = db.get_request_comments ( request_id )
    return jsonify ( { 'success' : True , 'comments' : comments } )


@app.route ( '/api/requests/<request_id>/comments' , methods = [ 'POST' ] )
@token_required
@role_required ( 'create_comments' )
def add_comment ( request_id ) :
    """Добавляет комментарий к заявке"""
    data = request.json
    comment = data.get ( 'comment' )

    if not comment :
        return jsonify ( { 'success' : False , 'message' : 'Введите комментарий' } ) , 400

    result = db.add_comment_to_request (
        request_id ,
        comment ,
        g.user_info [ 'full_name' ] ,
        g.user_info [ 'role' ]
    )

    if result.get ( 'success' ) :
        db._log_audit ( "add_comment" , f"Добавлен комментарий к заявке ID: {request_id}" , g.user_info )

    return jsonify ( result )


@app.route ( '/api/requests/<request_id>/status' , methods = [ 'PUT' ] )
@token_required
@role_required ( 'edit_requests' )
def update_request_status ( request_id ) :
    """Обновляет статус заявки"""
    data = request.json
    new_status = data.get ( 'status' )
    comment = data.get ( 'comment' , '' )

    if not new_status :
        return jsonify ( { 'success' : False , 'message' : 'Выберите статус' } ) , 400

    comment_author = g.user_info [ 'full_name' ] if comment else None

    result = db.update_request_status (
        request_id ,
        new_status ,
        comment if comment else None ,
        comment_author ,
        g.user_info [ 'role' ]
    )

    if result.get ( 'success' ) :
        db._log_audit ( "update_request_status" , f"Обновлен статус заявки ID: {request_id}" , g.user_info )

    return jsonify ( result )


# ------------------------------------------------------------------------
# МАРШРУТЫ ДЛЯ ОТЦЕПЛЕННЫХ ВАГОНОВ
# ------------------------------------------------------------------------

@app.route ( '/api/detached-wagons' , methods = [ 'GET' ] )
@token_required
def get_detached_wagons ( ) :
    """Получает список отцепленных вагонов"""
    wagons = db.get_detached_wagons ( )
    return jsonify ( { 'success' : True , 'wagons' : wagons } )


@app.route ( '/api/detached-wagons/<detached_id>' , methods = [ 'DELETE' ] )
@token_required
@role_required ( 'delete_detached' )
def delete_detached_wagon ( detached_id ) :
    """Удаляет вагон из Отцепа навсегда"""
    result = db.permanently_delete_detached_wagon ( detached_id )

    if result.get ( 'success' ) :
        db._log_audit ( "delete_detached_wagon" , f"Удален вагон из Отцепа ID: {detached_id}" , g.user_info )

    return jsonify ( result )


# ------------------------------------------------------------------------
# ЗАПУСК СЕРВЕРА
# ------------------------------------------------------------------------

if __name__ == '__main__' :
    port = int ( os.environ.get ( 'PORT' , 5000 ) )
    app.run ( host = '0.0.0.0' , port = port , debug = False )