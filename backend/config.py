import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
# Это работает только при локальной разработке
# На Render переменные будут браться из Environment Variables
load_dotenv ( )


class Config :
    # Supabase configuration
    SUPABASE_URL = os.getenv ( "SUPABASE_URL" )
    SUPABASE_KEY = os.getenv ( "SUPABASE_ANON_KEY" )

    # Security keys
    SECRET_KEY = os.getenv ( "SECRET_KEY" , "dev-secret-key-change-in-production" )
    JWT_SECRET = os.getenv ( "JWT_SECRET" , "jwt-secret-change-in-production" )

    # Debug mode (always False in production)
    DEBUG = os.getenv ( "DEBUG" , "False" ).lower ( ) == "true"

    # Server settings (Render will provide PORT via environment variable)
    PORT = int ( os.getenv ( "PORT" , 5000 ) )
    HOST = os.getenv ( "HOST" , "0.0.0.0" )

    # Constants from your original code
    VALID_WAGON_TYPES = [ "Купейный" , "Плацкарт" , "Сидячий" , "СВ" , "Штабной" , "Ресторан" ]
    SYSTEMS_CONFIG = [ 'IM' , 'SKDU' , 'SVNR' , 'SKBiSPP' ]

    @classmethod
    def validate ( cls ) :
        """Проверяет, что все необходимые переменные окружения установлены"""
        missing_vars = [ ]

        if not cls.SUPABASE_URL :
            missing_vars.append ( "SUPABASE_URL" )
        if not cls.SUPABASE_KEY :
            missing_vars.append ( "SUPABASE_ANON_KEY" )
        if not cls.SECRET_KEY or cls.SECRET_KEY == "dev-secret-key-change-in-production" :
            missing_vars.append ( "SECRET_KEY (должен быть изменен с дефолтного)" )
        if not cls.JWT_SECRET or cls.JWT_SECRET == "jwt-secret-change-in-production" :
            missing_vars.append ( "JWT_SECRET (должен быть изменен с дефолтного)" )

        if missing_vars :
            print ( "⚠️ ВНИМАНИЕ: Отсутствуют или не изменены следующие переменные окружения:" )
            for var in missing_vars :
                print ( f"   - {var}" )
            print ( "Убедитесь, что они установлены в .env файле или в Environment Variables на Render" )
            return False
        return True


# Создаем объект конфигурации для удобного импорта
config = Config ( )

# При импорте модуля проверяем конфигурацию
if __name__ != "__main__" :
    config.validate ( )