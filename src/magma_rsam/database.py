from playhouse.migrate import *
import os


def database(db_name: str = 'rsam.db'):
    db_path = os.path.join(os.getcwd(), 'output', 'database')
    os.makedirs(db_path, exist_ok=True)
    return os.path.join(db_path, db_name)


db = SqliteDatabase(database())


class RsamCSV(Model):
    nslc = CharField(index=True)
    date = DateField()
    file_location = CharField()

    class Meta:
        database = db
        table_name = 'rsam_csvs'
        indexes = (
            (('nslc', 'date'), True),
        )
