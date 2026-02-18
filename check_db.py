from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Проверка подключения к базе данных
def test_db_connection():
    try:
        engine = create_engine("postgresql://casino_hack_user:your_password@localhost/casino_hack_polish_db")
        Session = sessionmaker(bind=engine)
        session = Session()
        # Используем text() для явного объявления SQL-запроса
        session.execute(text("SELECT 1"))
        print("✅ Подключение к базе данных успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")

test_db_connection()
