# [START cloud_sql_sqlserver_sqlalchemy_connect_tcp]
# [START cloud_sql_sqlserver_sqlalchemy_sslcerts]
# [START cloud_sql_sqlserver_sqlalchemy_connect_tcp_sslcerts]
import os

#from flask_sqlalchemy import SQLAlchemy
import sqlalchemy


def connect_tcp_socket() -> sqlalchemy.engine.base.Engine:
    """Initializes a TCP connection pool for a Cloud SQL instance of SQL Server."""
    db_host = os.environ.get("INSTANCE_HOST")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")

    # [END cloud_sql_sqlserver_sqlalchemy_connect_tcp]
    # [START_EXCLUDE]
    connect_args = {}
    # [END_EXCLUDE]
    # For deployments that connect directly to a Cloud SQL instance without
    # using the Cloud SQL Proxy, configuring SSL certificates will ensure the
    # connection is encrypted.

    # If your SQL Server instance requires SSL, you need to download the CA
    # certificate for your instance and include cafile={path to downloaded
    # certificate} and validate_host=False, even when using the proxy.
    # This is a workaround for a known issue.
    if os.environ.get("DB_ROOT_CERT"):  # e.g. '/path/to/my/server-ca.pem'
        connect_args = {
            "cafile": os.environ["DB_ROOT_CERT"],
            "validate_host": False,
        }

    # [START cloud_sql_sqlserver_sqlalchemy_connect_tcp]
    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # mssql+pytds://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL.create(
            drivername="mssql+pytds",
            username=db_user,
            password=db_pass,
            database=db_name,
            host=db_host,
            port=db_port,
        ),
        # [END cloud_sql_sqlserver_sqlalchemy_connect_tcp]
        connect_args=connect_args,
        # [START cloud_sql_sqlserver_sqlalchemy_connect_tcp]
        # [START_EXCLUDE]
        # [START cloud_sql_sqlserver_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # [END cloud_sql_sqlserver_sqlalchemy_limit]
        # [START cloud_sql_sqlserver_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection attempts,
        # but provides no arguments for configuration.
        # [END cloud_sql_sqlserver_sqlalchemy_backoff]
        # [START cloud_sql_sqlserver_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # [END cloud_sql_sqlserver_sqlalchemy_timeout]
        # [START cloud_sql_sqlserver_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=1800,  # 30 minutes
        # [END cloud_sql_sqlserver_sqlalchemy_lifetime]
        # [END_EXCLUDE]
    )

    return pool


# [END cloud_sql_sqlserver_sqlalchemy_connect_tcp_sslcerts]
# [END cloud_sql_sqlserver_sqlalchemy_sslcerts]
# [END cloud_sql_sqlserver_sqlalchemy_connect_tcp]
