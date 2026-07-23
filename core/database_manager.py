from sqlalchemy import create_engine, inspect


class DatabaseManager:


    def connect_postgresql(
        self,
        host,
        port,
        database,
        user,
        password
    ):

        connection = (
            f"postgresql://"
            f"{user}:{password}"
            f"@{host}:{port}/{database}"
        )


        engine = create_engine(
            connection
        )

        return engine



    def get_tables(
        self,
        engine
    ):

        inspector = inspect(
            engine
        )

        return inspector.get_table_names()