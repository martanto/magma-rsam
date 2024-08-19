from playhouse.migrate import *
import os
import datetime


def database(db_name: str = 'magma.db'):
    """Database location

    Args:
        db_name: database name. Default magma.db

    Returns:
        str: Database location
    """
    user_dir: str = os.path.expanduser('~')
    magma_user_dir: str = os.path.join(user_dir, '.magma')
    os.makedirs(magma_user_dir, exist_ok=True)
    return os.path.join(user_dir, db_name)


db = SqliteDatabase(database())


class RsamCSV(Model):
    key = CharField(unique=True, index=True)
    nslc = CharField(index=True)
    date = DateField(index=True)
    resample = CharField()
    freq_min = FloatField(null=True)
    freq_max = FloatField(null=True)
    file_location = CharField()
    created_at = DateTimeField(default=datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = DateTimeField(default=datetime.datetime.now(tz=datetime.timezone.utc))

    class Meta:
        database = db
        table_name = 'rsam_csvs'
