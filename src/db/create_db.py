from src.db.db_session import database_exists, create_database, drop_database, init_db

if __name__ == "__main__":
    if not database_exists():
        print("База данных не найдена. Создаю новую...")
        create_database()
    else:
        answer = input("База данных существует. Хотите удалить её и создать заново? (y/N): ").strip().lower()
        if answer == 'y':
            drop_database()
            create_database()
        else:
            print("Используется существующая база данных.")

    print("Инициализирую таблицы...")
    init_db()
    print("База данных готова.")