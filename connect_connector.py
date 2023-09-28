import os
import pytds

from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy


def connect_with_connector() -> sqlalchemy.engine.base.Engine:

    # Initializes a connection pool for a Cloud SQL instance of SQL Server.
    # Uses the Cloud SQL Python Connector package.
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector = Connector(ip_type)

    connect_args = {}
    # If your SQL Server instance requires SSL, you need to download the CA
    # certificate for your instance and include cafile={path to downloaded
    # certificate} and validate_host=False. This is a workaround for a known issue.
    if os.environ.get("DB_ROOT_CERT"):  # e.g. '/path/to/my/server-ca.pem'
        connect_args = {
            "cafile": os.environ["DB_ROOT_CERT"],
            "validate_host": False,
        }

    def getconn() -> pytds.Connection:
        conn = connector.connect(
            instance_connection_name,
            "pytds",
            user=db_user,
            password=db_pass,
            db=db_name,
            **connect_args
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mssql+pytds://",
        creator=getconn,
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=600,  # 10 minutes
    )
    return pool