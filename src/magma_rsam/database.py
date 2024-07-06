from playhouse.migrate import *
import os
import datetime


def database(db_name: str = 'rsam.db'):
    db_path = os.path.join(os.getcwd(), 'output', 'database')
    os.makedirs(db_path, exist_ok=True)
    return os.path.join(db_path, db_name)


db = SqliteDatabase(database())


class RsamCSV(Model):
    nslc = CharField(index=True)
    date = DateField()
    resample = CharField()
    freq_min = FloatField(null=True)
    freq_max = FloatField(null=True)
    file_location = CharField()
    created_at = DateTimeField(default=datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = DateTimeField(default=datetime.datetime.now(tz=datetime.timezone.utc))

    class Meta:
        database = db
        table_name = 'rsam_csvs'
        indexes = (
            (('nslc', 'date', 'freq_min', 'freq_max', 'resample'), True),
        )
