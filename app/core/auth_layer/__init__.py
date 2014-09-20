
from database import AuthDatabaseWrapper


db = None

def init(client=None, dbname=None):
    global db
    db = AuthDatabaseWrapper(client, dbname)
    return db