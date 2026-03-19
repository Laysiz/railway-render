import sys
import os
import traceback
import json
import ssl
import uuid
import hashlib
import base64
import re
from datetime import datetime , date , timedelta
from supabase import create_client , Client
from config import Config


# 🔥 Создаем кастомный контекст SSL для обхода ошибок
def create_ssl_context ( ) :
    """Создает SSL контекст с более гибкими настройками"""
    context = ssl.create_default_context ( )
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers ( 'DEFAULT:@SECLEVEL=1' )
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


# 🔥 Инициализируем Supabase
try :
    supabase: Client = create_client ( Config.SUPABASE_URL , Config.SUPABASE_KEY )
    print ( "✅ Supabase клиент создан" )
except Exception as e :
    print ( f"❌ Критическая ошибка подключения: {e}" )
    supabase = None


class SupabaseDatabase :
    """Основной класс для работы с Supabase - все операции с БД"""

    def __init__ ( self , user_manager = None ) :
        self.user_manager = user_manager
        self._field_map = {
            'IM' : 'im' , 'SKDU' : 'skdu' , 'SVNR' : 'svnr' , 'SKBiSPP' : 'skbispp'
        }
        self._systems_default = { "im" : 1 , "skdu" : 1 , "svnr" : 1 , "skbispp" : 1 }
        self._data_cache = { }
        self._cache_timeout = 300  # 5 минут

    # ------------------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------------

    def _check_connection ( self ) :
        """Проверяет подключение к Supabase"""
        if supabase is None :
            print ( "❌ Supabase клиент не инициализирован" )
            return False

        try :
            result = supabase.table ( "poezda" ).select ( "id" , count = "exact" ).limit ( 1 ).execute ( )
            return True
        except Exception as e :
            print ( f"❌ Ошибка проверки подключения: {str ( e )}" )
            return False

    def _safe_execute ( self , operation , *args , **kwargs ) :
        """Безопасное выполнение операций с Supabase"""
        try :
            if not self._check_connection ( ) :
                print ( f"⚠️ Нет подключения к БД для операции: {operation.__name__}" )
                return None

            result = operation ( *args , **kwargs )
            return result

        except Exception as e :
            print ( f"❌ Ошибка в операции {operation.__name__}: {str ( e )}" )
            traceback.print_exc ( )
            return None

    def _log_audit ( self , action: str , details: str = "" , user_info = None ) :
        """Логирование действий пользователя"""
        if not user_info :
            return

        try :
            audit_data = {
                "user_login" : user_info.get ( 'login' , 'unknown' ) ,
                "user_role" : user_info.get ( 'role' , 'unknown' ) ,
                "action" : action ,
                "details" : details [ :500 ] ,
                "created_at" : datetime.now ( ).isoformat ( )
            }

            supabase.table ( "users_audit" ).insert ( audit_data ).execute ( )
        except :
            pass

    def _generate_request_number ( self ) :
        """Генерирует уникальный номер заявки"""

        def _generate ( ) :
            try :
                prefix = datetime.now ( ).strftime ( "%y%m%d" )
                result = supabase.table ( "zayavki" ) \
                    .select ( "request_number" ) \
                    .ilike ( "request_number" , f"{prefix}-%" ) \
                    .order ( "created_at" , desc = True ) \
                    .limit ( 1 ) \
                    .execute ( )

                if result.data and len ( result.data ) > 0 :
                    last_number = result.data [ 0 ] [ 'request_number' ]
                    try :
                        last_seq = int ( last_number.split ( '-' ) [ -1 ] )
                        new_seq = last_seq + 1
                    except :
                        new_seq = 1
                else :
                    new_seq = 1

                return f"{prefix}-{new_seq:04d}"
            except Exception as e :
                print ( f"⚠️ Ошибка при получении последнего номера: {str ( e )}" )
                return f"{datetime.now ( ).strftime ( '%y%m%d' )}-{uuid.uuid4 ( ).hex [ :4 ]}"

        return self._safe_execute (
            _generate ) or f"{datetime.now ( ).strftime ( '%y%m%d' )}-{uuid.uuid4 ( ).hex [ :4 ]}"

    def _update_wagon_system_status ( self , wagon_id , system , is_working ) :
        """Обновляет статус системы вагона"""
        try :
            wagon_result = supabase.table ( "vagony" ).select ( "systems" ).eq ( "id" , wagon_id ).execute ( )

            if wagon_result and wagon_result.data :
                current_systems = dict ( wagon_result.data [ 0 ] [ "systems" ] )
                field = self._field_map.get ( system )

                if field :
                    current_systems [ field ] = 1 if is_working else 0
                    supabase.table ( "vagony" ).update ( { "systems" : current_systems } ).eq ( "id" ,
                                                                                                wagon_id ).execute ( )
                    return True
        except Exception as e :
            print ( f"⚠️ Не удалось обновить системы вагона: {str ( e )}" )
        return False

    def _save_wagon_to_detached_batch ( self , wagons_data , reason ) :
        """Пакетное сохранение вагонов в отцеп"""

        def _save ( ) :
            try :
                detached_data = [ ]
                for wagon_data in wagons_data :
                    detached_data.append ( {
                        "wagon_id" : str ( wagon_data.get ( 'id' , '' ) ) ,
                        "wagon_number" : wagon_data.get ( 'number' , '' ) ,
                        "wagon_type" : wagon_data.get ( 'type' , '' ) ,
                        "train_id" : str ( wagon_data.get ( 'train_id' , '' ) ) ,
                        "train_name" : wagon_data.get ( 'train_name' , 'Неизвестный поезд' ) ,
                        "reason" : reason ,
                        "wagon_data" : wagon_data.get ( 'wagon_data' , { } ) ,
                        "requests" : wagon_data.get ( 'requests' , [ ] ) ,
                        "detached_date" : datetime.now ( ).isoformat ( )
                    } )

                if detached_data :
                    result = supabase.table ( "detached_wagons" ).insert ( detached_data ).execute ( )
                    return len ( result.data ) if result and result.data else 0
                return 0
            except Exception as e :
                print ( f"❌ Ошибка пакетного сохранения в отцеп: {str ( e )}" )
                return 0

        return self._safe_execute ( _save ) or 0

    def _delete_wagons_batch ( self , wagon_ids ) :
        """Пакетное удаление вагонов"""

        def _delete ( ) :
            try :
                if wagon_ids :
                    # Пакетное удаление заявок
                    supabase.table ( "zayavki" ).delete ( ).in_ ( "vagony_id" , wagon_ids ).execute ( )
                    # Пакетное удаление вагонов
                    supabase.table ( "vagony" ).delete ( ).in_ ( "id" , wagon_ids ).execute ( )
                    return len ( wagon_ids )
                return 0
            except Exception as e :
                print ( f"❌ Ошибка пакетного удаления вагонов: {str ( e )}" )
                return 0

        return self._safe_execute ( _delete ) or 0

    def _find_wagon_in_detached ( self , wagon_number ) :
        """Ищет вагон в отцепе по номеру"""

        def _find ( ) :
            try :
                result = supabase.table ( "detached_wagons" ) \
                    .select ( "*" ) \
                    .eq ( "wagon_number" , wagon_number ) \
                    .order ( "detached_date" , desc = True ) \
                    .limit ( 1 ) \
                    .execute ( )

                if result.data and len ( result.data ) > 0 :
                    return result.data [ 0 ]
                return None
            except Exception as e :
                print ( f"❌ Ошибка поиска в Отцепе: {str ( e )}" )
                return None

        return self._safe_execute ( _find )

    def _delete_wagon_from_detached ( self , detached_id ) :
        """Удаляет вагон из отцепа"""

        def _delete ( ) :
            try :
                supabase.table ( "detached_wagons" ).delete ( ).eq ( "id" , detached_id ).execute ( )
                print ( f"🗑️ Вагон удален из Отцепа (ID: {detached_id})" )
                return True
            except Exception as e :
                print ( f"❌ Ошибка удаления из Отцепа: {str ( e )}" )
                return False

        return self._safe_execute ( _delete )

    def _restore_requests_from_detached ( self , new_wagon_id , requests ) :
        """Восстанавливает заявки из отцепа"""

        def _restore ( ) :
            try :
                if not requests :
                    return

                restored_count = 0
                for request in requests :
                    request_data = dict ( request )
                    request_data [ 'vagony_id' ] = new_wagon_id
                    request_data.pop ( 'id' , None )
                    request_data.pop ( 'created_at' , None )
                    request_data.pop ( 'updated_at' , None )

                    result = supabase.table ( "zayavki" ).insert ( request_data ).execute ( )
                    if result and result.data :
                        restored_count += 1

                print ( f"✅ Восстановлено {restored_count} заявок из Отцепа" )

            except Exception as e :
                print ( f"❌ Ошибка восстановления заявки: {str ( e )}" )

        return self._safe_execute ( _restore )

    # ------------------------------------------------------------------------
    # МЕТОДЫ ДЛЯ РАБОТЫ С ПОЕЗДАМИ
    # ------------------------------------------------------------------------

    def fetch_trains ( self ) :
        """Получает все поезда"""

        def _fetch ( ) :
            try :
                result = supabase.table ( "poezda" ).select ( "*" ).order ( "depot_date" , desc = True ).execute ( )
                return result.data or [ ]
            except Exception as e :
                print ( f"❌ Ошибка получения поездов: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _fetch ) or [ ]

    def add_train ( self , name , pem_fio = "" , depot_date_param = None , trip_days = 7 ) :
        """Добавляет новый поезд"""

        def _add ( ) :
            dep_date = depot_date_param if depot_date_param is not None else date.today ( )

            data = {
                "name" : name ,
                "pem_fio" : pem_fio or None ,
                "depot_date" : dep_date.isoformat ( ) ,
                "trip_days" : trip_days
            }
            try :
                result = supabase.table ( "poezda" ).insert ( data ).execute ( )
                if result.data and len ( result.data ) > 0 :
                    return { "success" : True , "id" : result.data [ 0 ] [ "id" ] , "message" : "Поезд добавлен" }
                return { "success" : False , "message" : "Не удалось добавить поезд" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _add ) or { "success" : False , "message" : "Ошибка выполнения" }

    def update_train ( self , train_id , name , pem_fio = "" , depot_date_param = None , trip_days = None ) :
        """Обновляет данные поезда"""

        def _update ( ) :
            data = {
                "name" : name ,
                "pem_fio" : pem_fio or None
            }

            if depot_date_param :
                if isinstance ( depot_date_param , date ) :
                    data [ "depot_date" ] = depot_date_param.isoformat ( )
                else :
                    data [ "depot_date" ] = depot_date_param

            if trip_days is not None :
                data [ "trip_days" ] = trip_days

            try :
                if data :
                    result = supabase.table ( "poezda" ).update ( data ).eq ( "id" , train_id ).execute ( )
                    if result.data and len ( result.data ) > 0 :
                        return { "success" : True , "message" : "Поезд обновлен" }
                return { "success" : False , "message" : "Не удалось обновить поезд" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _update ) or { "success" : False , "message" : "Ошибка выполнения" }

    def update_train_dates ( self , train_id , depot_date_param = None , trip_days = None ) :
        """Обновляет только даты поезда"""

        def _update ( ) :
            data = { }

            if depot_date_param :
                if isinstance ( depot_date_param , date ) :
                    data [ "depot_date" ] = depot_date_param.isoformat ( )
                else :
                    data [ "depot_date" ] = depot_date_param

            if trip_days is not None :
                data [ "trip_days" ] = trip_days

            try :
                if data :
                    result = supabase.table ( "poezda" ).update ( data ).eq ( "id" , train_id ).execute ( )
                    if result.data and len ( result.data ) > 0 :
                        return { "success" : True , "message" : "График поезда обновлен" }
                return { "success" : False , "message" : "Не удалось обновить график" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _update ) or { "success" : False , "message" : "Ошибка выполнения" }

    def delete_train ( self , train_id ) :
        """Удаляет поезд"""

        def _delete ( ) :
            try :
                wagons_result = supabase.table ( "vagony" ).select ( "id" ).eq ( "poezda_id" , train_id ).execute ( )
                wagon_ids = [ w [ "id" ] for w in wagons_result.data or [ ] ]

                if wagon_ids :
                    # Пакетное сохранение в отцеп
                    wagons_data = [ ]
                    for wagon_id in wagon_ids :
                        wagon_result = supabase.table ( "vagony" ).select ( "*" ).eq ( "id" , wagon_id ).execute ( )
                        if wagon_result.data :
                            wagon = wagon_result.data [ 0 ]
                            requests_result = supabase.table ( "zayavki" ).select ( "*" ).eq ( "vagony_id" ,
                                                                                               wagon_id ).execute ( )

                            wagons_data.append ( {
                                'id' : wagon_id ,
                                'number' : wagon.get ( 'number' , '' ) ,
                                'type' : wagon.get ( 'type' , '' ) ,
                                'train_id' : train_id ,
                                'train_name' : '' ,
                                'wagon_data' : wagon ,
                                'requests' : requests_result.data or [ ]
                            } )

                    if wagons_data :
                        self._save_wagon_to_detached_batch ( wagons_data , "delete_train" )

                    # Пакетное удаление
                    self._delete_wagons_batch ( wagon_ids )

                supabase.table ( "poezda" ).delete ( ).eq ( "id" , train_id ).execute ( )
                return { "success" : True , "message" : "Поезд удален, вагоны сохранены в Отцеп" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _delete ) or { "success" : False , "message" : "Ошибка выполнения" }

    def calculate_train_schedule ( self , depot_date , trip_days , selected_date ) :
        """Рассчитывает, находится ли поезд в депо на выбранную дату"""
        if not depot_date or not trip_days :
            return False , 0 , "unknown"

        delta_days = (selected_date - depot_date).days

        if delta_days < 0 :
            return False , delta_days , "future"

        cycle_days = trip_days
        position_in_cycle = delta_days % (cycle_days)
        is_in_depot = (position_in_cycle == 0)
        days_in_trip = position_in_cycle

        return is_in_depot , days_in_trip , "in_depot" if is_in_depot else "in_trip"

    def fetch_trains_by_date ( self , selected_date ) :
        """Получает поезда для конкретной даты"""

        def _fetch ( ) :
            try :
                result = supabase.table ( "poezda" ).select ( "*" ).execute ( )
                all_trains = result.data or [ ]
                trains_for_date = [ ]

                for train in all_trains :
                    depot_date_str = train.get ( 'depot_date' )
                    if not depot_date_str :
                        continue

                    try :
                        if isinstance ( depot_date_str , str ) :
                            depot_date = datetime.strptime ( depot_date_str , "%Y-%m-%d" ).date ( )
                        elif isinstance ( depot_date_str , datetime ) :
                            depot_date = depot_date_str.date ( )
                        else :
                            continue

                        trip_days = train.get ( 'trip_days' , 7 )
                        is_in_depot , days_in_trip , status = self.calculate_train_schedule (
                            depot_date , trip_days , selected_date
                        )

                        train_copy = train.copy ( )
                        if is_in_depot :
                            train_copy [ 'depot_date' ] = depot_date.isoformat ( )
                            train_copy [ 'trip_days' ] = trip_days
                            train_copy [ 'status' ] = 'depot'
                            train_copy [ 'days_in_trip' ] = 0
                            train_copy [ 'next_depot_date' ] = selected_date.isoformat ( )
                            train_copy [ 'next_trip_start' ] = (selected_date + timedelta ( days = 1 )).isoformat ( )
                            train_copy [ 'cycle_info' ] = f"Цикл: {trip_days} дн."
                            trains_for_date.append ( train_copy )
                        else :
                            delta_days = (selected_date - depot_date).days
                            train_copy [ 'depot_date' ] = depot_date.isoformat ( )
                            train_copy [ 'trip_days' ] = trip_days
                            train_copy [ 'status' ] = 'trip'
                            train_copy [ 'days_in_trip' ] = days_in_trip
                            cycles_completed = delta_days // trip_days
                            next_depot = depot_date + timedelta ( days = (cycles_completed + 1) * trip_days )
                            train_copy [ 'next_depot_date' ] = next_depot.isoformat ( )
                            train_copy [ 'cycle_info' ] = f"В рейсе: {days_in_trip}/{trip_days} дн."
                            train_copy [ 'days_until_depot' ] = (next_depot - selected_date).days
                            trains_for_date.append ( train_copy )

                    except Exception as e :
                        print ( f"❌ Ошибка обработки даты поезда {train.get ( 'name' )}: {e}" )
                        continue

                return trains_for_date
            except Exception as e :
                print ( f"❌ Ошибка получения поездов по дате: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _fetch ) or [ ]

    # ------------------------------------------------------------------------
    # МЕТОДЫ ДЛЯ РАБОТЫ С ВАГОНАМИ
    # ------------------------------------------------------------------------

    def fetch_wagons_for_train ( self , train_id ) :
        """Получает вагоны для поезда"""

        def _fetch ( ) :
            try :
                result = supabase.table ( "vagony" ).select ( "*" ).eq ( "poezda_id" , train_id ).order (
                    "created_at" ).execute ( )
                wagons = result.data or [ ]

                for wagon in wagons :
                    wagon [ 'train_id' ] = train_id
                    systems = wagon.get ( 'systems' , self._systems_default )
                    has_systems = wagon.get ( 'has_systems' , self._systems_default )

                    for sys_name in [ 'im' , 'skdu' , 'svnr' , 'skbispp' ] :
                        wagon [ f'has_{sys_name}' ] = has_systems.get ( sys_name , 1 )
                        wagon [ sys_name ] = systems.get ( sys_name , 1 )
                return wagons
            except Exception as e :
                print ( f"❌ Ошибка получения вагонов: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _fetch ) or [ ]

    def add_wagon ( self , train_id , number , w_type ) :
        """Добавляет вагон"""

        def _add ( ) :
            # Проверка уникальности
            try :
                check_result = supabase.table ( "vagony" ).select ( "id, number, poezda_id" ).eq ( "number" ,
                                                                                                   number ).execute ( )

                if check_result.data and len ( check_result.data ) > 0 :
                    existing_wagon = check_result.data [ 0 ]
                    existing_train_id = existing_wagon.get ( 'poezda_id' )
                    train_result = supabase.table ( "poezda" ).select ( "name" ).eq ( "id" ,
                                                                                      existing_train_id ).execute ( )
                    train_name = train_result.data [ 0 ] [ 'name' ] if train_result.data else "неизвестный поезд"
                    return { "success" : False ,
                             "message" : f"Вагон с номером {number} уже существует в поезде '{train_name}'" }
            except Exception as e :
                print ( f"⚠️ Ошибка проверки уникальности номера вагона: {str ( e )}" )

            # Проверка отцепа
            detached_wagon = self._find_wagon_in_detached ( number )
            if detached_wagon :
                print ( f"📦 Найден вагон в Отцепе: {number}" )
                wagon_data = detached_wagon [ 'wagon_data' ]
                wagon_data [ 'poezda_id' ] = train_id
                wagon_data [ 'number' ] = number
                wagon_data [ 'type' ] = w_type

                try :
                    result = supabase.table ( "vagony" ).insert ( wagon_data ).execute ( )
                    if result and result.data and len ( result.data ) > 0 :
                        wagon_id = result.data [ 0 ] [ "id" ]
                        self._restore_requests_from_detached ( wagon_id , detached_wagon.get ( 'requests' , [ ] ) )
                        self._delete_wagon_from_detached ( detached_wagon [ 'id' ] )
                        return { "success" : True , "id" : wagon_id ,
                                 "message" : f"Вагон #{number} восстановлен из Отцепа" }
                except Exception as e :
                    return { "success" : False , "message" : f"Ошибка восстановления вагона: {str ( e )}" }

            # Создание нового вагона
            data = {
                "poezda_id" : train_id ,
                "number" : number ,
                "type" : w_type ,
                "systems" : self._systems_default.copy ( ) ,
                "has_systems" : self._systems_default.copy ( ) ,
                "comment" : ""
            }

            try :
                result = supabase.table ( "vagony" ).insert ( data ).execute ( )
                if result and result.data and len ( result.data ) > 0 :
                    wagon_id = result.data [ 0 ] [ "id" ]
                    return { "success" : True , "id" : wagon_id , "message" : f"Вагон #{number} добавлен" }
                else :
                    return { "success" : False , "message" : "Не удалось добавить вагон" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _add ) or { "success" : False , "message" : "Ошибка выполнения" }

    def delete_wagon ( self , wagon_id ) :
        """Удаляет вагон"""

        def _delete ( ) :
            try :
                wagon_result = supabase.table ( "vagony" ).select ( "*" ).eq ( "id" , wagon_id ).execute ( )
                if not wagon_result.data or len ( wagon_result.data ) == 0 :
                    return { "success" : False , "message" : f"Вагон {wagon_id} не найден" }

                wagon_data = wagon_result.data [ 0 ]
                requests_result = supabase.table ( "zayavki" ).select ( "*" ).eq ( "vagony_id" , wagon_id ).execute ( )
                requests = requests_result.data or [ ]
                train_id = wagon_data.get ( 'poezda_id' )

                # Сохраняем в отцеп
                wagons_data = [ {
                    'id' : wagon_id ,
                    'number' : wagon_data.get ( 'number' , '' ) ,
                    'type' : wagon_data.get ( 'type' , '' ) ,
                    'train_id' : train_id ,
                    'train_name' : '' ,
                    'wagon_data' : wagon_data ,
                    'requests' : requests
                } ]
                self._save_wagon_to_detached_batch ( wagons_data , "delete_wagon" )

                # Удаляем
                self._delete_wagons_batch ( [ wagon_id ] )

                return { "success" : True , "message" : f"Вагон удален и сохранен в Отцеп" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _delete ) or { "success" : False , "message" : "Ошибка выполнения" }

    def update_wagon_number ( self , wagon_id , new_number ) :
        """Обновляет номер вагона"""

        def _update ( ) :
            try :
                check_result = supabase.table ( "vagony" ).select ( "id, poezda_id" ).eq ( "number" ,
                                                                                           new_number ).execute ( )

                if check_result.data and len ( check_result.data ) > 0 :
                    existing_wagon = check_result.data [ 0 ]
                    if existing_wagon [ 'id' ] != wagon_id :
                        train_result = supabase.table ( "poezda" ).select ( "name" ).eq ( "id" , existing_wagon.get (
                            'poezda_id' ) ).execute ( )
                        train_name = train_result.data [ 0 ] [ 'name' ] if train_result.data else "неизвестный поезд"
                        return { "success" : False ,
                                 "message" : f"Вагон с номером {new_number} уже существует в поезде '{train_name}'" }

                result = supabase.table ( "vagony" ).update ( { "number" : new_number } ).eq ( "id" ,
                                                                                               wagon_id ).execute ( )

                if result and result.data :
                    return { "success" : True , "message" : f"Номер вагона изменен на {new_number}" }
                return { "success" : False , "message" : "Не удалось обновить номер" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _update ) or { "success" : False , "message" : "Ошибка выполнения" }

    def update_wagon_systems ( self , wagon_id , systems , has_systems , comment ) :
        """Обновляет системы вагона"""

        def _update ( ) :
            try :
                update_data = {
                    "systems" : {
                        "im" : int ( 1 if systems.get ( 'IM' , False ) else 0 ) ,
                        "skdu" : int ( 1 if systems.get ( 'SKDU' , False ) else 0 ) ,
                        "svnr" : int ( 1 if systems.get ( 'SVNR' , False ) else 0 ) ,
                        "skbispp" : int ( 1 if systems.get ( 'SKBiSPP' , False ) else 0 )
                    } ,
                    "has_systems" : {
                        "im" : int ( 1 if has_systems.get ( 'IM' , False ) else 0 ) ,
                        "skdu" : int ( 1 if has_systems.get ( 'SKDU' , False ) else 0 ) ,
                        "svnr" : int ( 1 if has_systems.get ( 'SVNR' , False ) else 0 ) ,
                        "skbispp" : int ( 1 if has_systems.get ( 'SKBiSPP' , False ) else 0 )
                    } ,
                    "comment" : comment or ""
                }

                result = supabase.table ( "vagony" ).update ( update_data ).eq ( "id" , wagon_id ).execute ( )
                if result and hasattr ( result , 'data' ) and result.data :
                    return { "success" : True , "message" : "Системы вагона обновлены" }
                return { "success" : False , "message" : "Не удалось обновить системы" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _update ) or { "success" : False , "message" : "Ошибка выполнения" }

    def search_wagon_by_number ( self , wagon_number ) :
        """Ищет вагон по номеру"""

        def _search ( ) :
            try :
                results = {
                    'in_trains' : [ ] ,
                    'in_detached' : [ ] ,
                    'found_count' : 0
                }

                try :
                    train_search_result = supabase.table ( "vagony" ) \
                        .select ( "*, poezda(name)" ) \
                        .ilike ( "number" , f"%{wagon_number}%" ) \
                        .execute ( )

                    if train_search_result.data :
                        for wagon in train_search_result.data :
                            train_info = wagon.get ( 'poezda' , { } )
                            train_name = train_info.get ( 'name' , 'Неизвестный поезд' ) if isinstance ( train_info ,
                                                                                                         dict ) else 'Неизвестный поезд'
                            train_id = wagon.get ( 'poezda_id' )

                            results [ 'in_trains' ].append ( {
                                'id' : wagon [ 'id' ] ,
                                'number' : wagon.get ( 'number' , '' ) ,
                                'type' : wagon.get ( 'type' , '' ) ,
                                'train_id' : train_id ,
                                'train_name' : train_name ,
                                'systems' : wagon.get ( 'systems' , { } ) ,
                                'has_systems' : wagon.get ( 'has_systems' , { } ) ,
                                'comment' : wagon.get ( 'comment' , '' ) ,
                                'location' : 'В составе поезда'
                            } )
                except Exception as e :
                    print ( f"⚠️ Ошибка поиска вагонов в поездах: {str ( e )}" )

                try :
                    detached_search_result = supabase.table ( "detached_wagons" ) \
                        .select ( "*" ) \
                        .ilike ( "wagon_number" , f"%{wagon_number}%" ) \
                        .execute ( )

                    if detached_search_result.data :
                        for wagon in detached_search_result.data :
                            results [ 'in_detached' ].append ( {
                                'id' : wagon [ 'id' ] ,
                                'number' : wagon.get ( 'wagon_number' , '' ) ,
                                'type' : wagon.get ( 'wagon_type' , '' ) ,
                                'train_name' : wagon.get ( 'train_name' , 'Неизвестный поезд' ) ,
                                'detached_date' : wagon.get ( 'detached_date' , '' ) ,
                                'reason' : wagon.get ( 'reason' , '' ) ,
                                'location' : 'В отцепе' ,
                                'wagon_data' : wagon.get ( 'wagon_data' , { } )
                            } )
                except Exception as e :
                    print ( f"⚠️ Ошибка поиска вагонов в отцепе: {str ( e )}" )

                results [ 'found_count' ] = len ( results [ 'in_trains' ] ) + len ( results [ 'in_detached' ] )
                return results

            except Exception as e :
                print ( f"❌ Ошибка поиска вагона: {str ( e )}" )
                return {
                    'in_trains' : [ ] ,
                    'in_detached' : [ ] ,
                    'found_count' : 0
                }

        return self._safe_execute ( _search ) or {
            'in_trains' : [ ] ,
            'in_detached' : [ ] ,
            'found_count' : 0
        }

    # ------------------------------------------------------------------------
    # МЕТОДЫ ДЛЯ РАБОТЫ С ЗАЯВКАМИ
    # ------------------------------------------------------------------------

    def create_request ( self , wagon_id , pem_type , system , description , created_by , user_role ) :
        """Создает новую заявку с уникальным номером"""

        def _create ( ) :
            try :
                request_number = self._generate_request_number ( )

                data = {
                    "vagony_id" : wagon_id ,
                    "request_number" : request_number ,
                    "pem_type" : pem_type ,
                    "system" : system ,
                    "description" : description [ :1000 ] ,
                    "status" : "В работе" ,
                    "created_by" : created_by ,
                    "created_by_role" : user_role ,
                    "updated_at" : datetime.now ( ).isoformat ( )
                }

                result = supabase.table ( "zayavki" ).insert ( data ).execute ( )

                if result and hasattr ( result , 'data' ) and result.data :
                    self._update_wagon_system_status ( wagon_id , system , False )
                    return { "success" : True , "request_number" : request_number ,
                             "message" : f"Заявка №{request_number} создана" }

                return { "success" : False , "message" : "Не удалось создать заявку" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _create ) or { "success" : False , "message" : "Ошибка выполнения" }

    def fetch_requests_for_wagon ( self , wagon_id ) :
        """Получает заявки для вагона"""

        def _fetch ( ) :
            try :
                result = supabase.table ( "zayavki" ) \
                    .select ( "*" ) \
                    .eq ( "vagony_id" , wagon_id ) \
                    .order ( "created_at" , desc = True ) \
                    .execute ( )

                requests = result.data or [ ]

                for req in requests :
                    request_id = req [ 'id' ]

                    try :
                        comments_result = supabase.table ( "request_comments" ) \
                            .select ( "id" , count = "exact" ) \
                            .eq ( "request_id" , request_id ) \
                            .execute ( )

                        if hasattr ( comments_result , 'count' ) :
                            req [ 'comments_count' ] = comments_result.count
                        else :
                            req [ 'comments_count' ] = 0
                    except :
                        req [ 'comments_count' ] = 0

                    try :
                        attachments_result = supabase.table ( "request_attachments" ) \
                            .select ( "id" , count = "exact" ) \
                            .eq ( "request_id" , request_id ) \
                            .execute ( )

                        if hasattr ( attachments_result , 'count' ) :
                            req [ 'attachments_count' ] = attachments_result.count
                        else :
                            req [ 'attachments_count' ] = 0
                    except :
                        req [ 'attachments_count' ] = 0

                    created_at = req.get ( 'created_at' )
                    if created_at :
                        if isinstance ( created_at , str ) :
                            try :
                                dt = datetime.fromisoformat ( created_at.replace ( 'Z' , '+00:00' ) )
                                req [ 'created_at_formatted' ] = dt.strftime ( "%d.%m.%Y %H:%M" )
                            except :
                                req [ 'created_at_formatted' ] = created_at
                        else :
                            req [ 'created_at_formatted' ] = created_at.strftime (
                                "%d.%m.%Y %H:%M" ) if created_at else ""

                    updated_at = req.get ( 'updated_at' )
                    if updated_at :
                        if isinstance ( updated_at , str ) :
                            try :
                                dt = datetime.fromisoformat ( updated_at.replace ( 'Z' , '+00:00' ) )
                                req [ 'updated_at_formatted' ] = dt.strftime ( "%d.%m.%Y %H:%M" )
                            except :
                                req [ 'updated_at_formatted' ] = updated_at
                        else :
                            req [ 'updated_at_formatted' ] = updated_at.strftime (
                                "%d.%m.%Y %H:%M" ) if updated_at else ""

                return requests
            except Exception as e :
                print ( f"❌ Ошибка получения заявки: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _fetch ) or [ ]

    def update_request_status ( self , request_id , new_status , comment = None , comment_author = None ,
                                user_role = None ) :
        """Обновляет статус заявки и добавляет комментарий"""

        def _update ( ) :
            try :
                test_result = supabase.table ( "zayavki" ).select ( "*, vagony_id" ).eq ( "id" , request_id ).limit (
                    1 ).execute ( )
                if not test_result.data :
                    return { "success" : False , "message" : f"Заявка {request_id} не найдена" }

                request_data = test_result.data [ 0 ]
                wagon_id = request_data.get ( 'vagony_id' )
                system = request_data.get ( 'system' )

                update_data = {
                    "status" : new_status ,
                    "updated_at" : datetime.now ( ).isoformat ( )
                }

                result = supabase.table ( "zayavki" ).update ( update_data ).eq ( "id" , request_id ).execute ( )

                if result and result.data :
                    if new_status == "Выполнено" and wagon_id and system :
                        print ( f"🔄 Обновляем систему {system} вагона {wagon_id} на исправную" )
                        self._update_wagon_system_status ( wagon_id , system , True )

                    if comment and comment_author :
                        try :
                            comment_data = {
                                "request_id" : request_id ,
                                "comment" : comment ,
                                "created_by" : comment_author ,
                                "created_by_role" : user_role
                            }
                            supabase.table ( "request_comments" ).insert ( comment_data ).execute ( )
                        except Exception as e :
                            print ( f"⚠️ Не удалось добавить комментарий: {str ( e )}" )

                    return { "success" : True , "message" : f"Статус заявки изменен на '{new_status}'" }
                return { "success" : False , "message" : "Не удалось обновить статус" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _update ) or { "success" : False , "message" : "Ошибка выполнения" }

    # ------------------------------------------------------------------------
    # МЕТОДЫ ДЛЯ РАБОТЫ С КОММЕНТАРИЯМИ
    # ------------------------------------------------------------------------

    def add_comment_to_request ( self , request_id , comment , author , user_role ) :
        """Добавляет комментарий к заявке"""

        def _add ( ) :
            try :
                data = {
                    "request_id" : request_id ,
                    "comment" : comment ,
                    "created_by" : author ,
                    "created_by_role" : user_role
                }

                result = supabase.table ( "request_comments" ).insert ( data ).execute ( )

                if result and result.data :
                    try :
                        supabase.table ( "zayavki" ).update ( { "updated_at" : datetime.now ( ).isoformat ( ) } ).eq (
                            "id" , request_id ).execute ( )
                    except Exception as e :
                        print ( f"⚠️ Не удалось обновить время заявки: {str ( e )}" )

                    return { "success" : True , "message" : "Комментарий добавлен" }
                else :
                    return { "success" : False , "message" : "Не удалось добавить комментарий" }
            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _add ) or { "success" : False , "message" : "Ошибка выполнения" }

    def get_request_comments ( self , request_id ) :
        """Получает список комментариев к заявке"""

        def _get ( ) :
            try :
                result = supabase.table ( "request_comments" ) \
                    .select ( "*" ) \
                    .eq ( "request_id" , request_id ) \
                    .order ( "created_at" , desc = False ) \
                    .execute ( )

                return result.data or [ ]
            except Exception as e :
                print ( f"❌ Ошибка получения комментариев: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _get ) or [ ]

    # ------------------------------------------------------------------------
    # МЕТОДЫ ДЛЯ РАБОТЫ С ОТЦЕПЛЕННЫМИ ВАГОНАМИ
    # ------------------------------------------------------------------------

    def get_detached_wagons ( self ) :
        """Получает список отцепленных вагонов"""

        def _get ( ) :
            try :
                result = supabase.table ( "detached_wagons" ) \
                    .select ( "*" ) \
                    .order ( "detached_date" , desc = True ) \
                    .execute ( )

                detached_wagons = [ ]
                for wagon in result.data or [ ] :
                    requests = wagon.get ( 'requests' , [ ] )
                    detached_wagons.append ( {
                        'id' : wagon [ 'id' ] ,
                        'wagon_number' : wagon.get ( 'wagon_number' , '' ) ,
                        'wagon_type' : wagon.get ( 'wagon_type' , '' ) ,
                        'train_name' : wagon.get ( 'train_name' , '' ) ,
                        'detached_date' : wagon.get ( 'detached_date' , '' ) ,
                        'reason' : wagon.get ( 'reason' , '' ) ,
                        'has_requests' : len ( requests ) > 0 ,
                        'requests_count' : len ( requests ) ,
                        'wagon_data' : wagon.get ( 'wagon_data' , { } )
                    } )

                return detached_wagons

            except Exception as e :
                print ( f"❌ Ошибка получения списка Отцепа: {str ( e )}" )
                return [ ]

        return self._safe_execute ( _get ) or [ ]

    def permanently_delete_detached_wagon ( self , detached_id ) :
        """Удаляет вагон из Отцепа"""

        def _delete ( ) :
            try :
                result = supabase.table ( "detached_wagons" ) \
                    .select ( "wagon_number" ) \
                    .eq ( "id" , detached_id ) \
                    .execute ( )

                if result.data and len ( result.data ) > 0 :
                    wagon_number = result.data [ 0 ].get ( 'wagon_number' , 'unknown' )

                    supabase.table ( "detached_wagons" ).delete ( ).eq ( "id" , detached_id ).execute ( )

                    return { "success" : True , "message" : f"Вагон {wagon_number} удален из Отцепа" }
                else :
                    return { "success" : False , "message" : f"Вагон с ID {detached_id} не найден в Отцепе" }

            except Exception as e :
                return { "success" : False , "message" : str ( e ) }

        return self._safe_execute ( _delete ) or { "success" : False , "message" : "Ошибка выполнения" }