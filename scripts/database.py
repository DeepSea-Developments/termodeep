import os
import sys
from flask import g
import sqlite3


# DATABASE = 'database.db'
DATABASE = 'database_v2.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def _dict_helper(desc, row):
    # Returns a dictionary for the given cursor.description and result row.
    return dict([(desc[col[0]][0], col[1]) for col in enumerate(row)])


def dictfetchone(cursor):
    # Returns a row from the cursor as a dict
    row = cursor.fetchone()
    if not row:
        return None
    return _dict_helper(cursor.description, row)


def dictfetchall(cursor):
    # Returns all rows from a cursor as a dict
    desc = cursor.description
    return [_dict_helper(desc, row) for row in cursor.fetchall()]


def init_db(app):
    with app.app_context():
        db = get_db()
        if getattr(sys, 'frozen', False):
            schema_path = os.path.join(sys._MEIPASS, 'schema.sql')
        else:
            schema_path = 'schema.sql'
        with app.open_resource(schema_path, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
