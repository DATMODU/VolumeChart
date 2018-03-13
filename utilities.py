import sqlalchemy

class Utilities(object):
    def __init__(self):
        pass

    def set_db_engine(self, DB_ID, DB_PWD, DB_IP, DB_PORT, DB_NAME):
        """
        :param DB_ID: user id for db
        :param DB_PWD: user password for db and id
        :param DB_IP: address
        :param DB_PORT: port
        :param DB_NAME: specific db name
        :return: DB engine to use sql query
        """
        conn_str = "mysql+pymysql://{0}:{1}@{2}:{3}/{4}?charset={5}". \
            format(DB_ID, DB_PWD, DB_IP, DB_PORT, DB_NAME, 'utf8')
        engine = sqlalchemy.create_engine(conn_str)
        return engine
