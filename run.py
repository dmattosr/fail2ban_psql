

import maxminddb
import os
import psycopg2

from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), 'app.env')
load_dotenv(dotenv_path)


GEOIP_DATABASE = os.environ.get('GEOIP_DATABASE', 'GeoLite2-City.mmdb')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
DB_DATABASE = os.environ.get('DB_DATABASE', 'fail2ban')
FILENAME_LOG_FAIL2BAN = os.environ.get('FILENAME_LOG_FAIL2BAN', 'fail2ban.log')


SQL_CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS fail2ban (
    time TIMESTAMP NOT NULL,
    jail VARCHAR (50) NOT NULL,
    action VARCHAR (50),
    ip VARCHAR (15),
    country_code VARCHAR (3),
    country VARCHAR (50),
    city_code VARCHAR (10),
    city VARCHAR (50),
    latitude float,
    longitude float,
    created_on TIMESTAMP NOT NULL DEFAULT NOW()
);
'''

SQL_CREATE_TABLE_TMP = '''
CREATE TEMPORARY TABLE tmpfail2ban (
    time TIMESTAMP NOT NULL,
    jail VARCHAR (50) NOT NULL,
    action VARCHAR (50),
    ip VARCHAR (15),
    country_code VARCHAR (3),
    country VARCHAR (50),
    city_code VARCHAR (10),
    city VARCHAR (50),
    latitude float,
    longitude float
);
'''

SQL_INSERT = '''
INSERT INTO fail2ban(time, jail, action, ip, country, country_code, city, latitude, longitude)
    SELECT time, jail, action, ip, country, country_code, city, latitude, longitude FROM tmpfail2ban
    WHERE time > COALESCE((select max(time) from fail2ban), '2022-01-01 00:00:00')
    ORDER BY time;
'''

SQL_INSERT_TMP = '''
INSERT INTO tmpfail2ban(time, jail, action, ip, country, country_code, city, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
'''


connection = None
try:
    # Connect to an existing database
    connection = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
    )

    cursor = connection.cursor()
    # Print PostgreSQL details
    print("PostgreSQL server information")
    print(connection.get_dsn_parameters(), "\n")
    # Executing a SQL query
    cursor.execute("SELECT version();")
    # Fetch result
    record = cursor.fetchone()
    print("You are connected to - ", record, "\n")

except Exception as e:
    print("Error while connecting to PostgreSQL", e)
    exit(0)


cursor.execute(SQL_CREATE_TABLE)
cursor.execute(SQL_CREATE_TABLE_TMP)
geo_reader = maxminddb.open_database(GEOIP_DATABASE)

for line in open(FILENAME_LOG_FAIL2BAN).readlines():
    line = [
        item
        for item in line[:-1].split(' ')
        if item
    ]
    item = {
        'time': '{} {}'.format(*line[0:2])[:-4],
        'type': line[2],
        'jail': line[5][1:-1],
        'action': line[6],
        'ip': line[7],
    }
    try:
        assert all(map(lambda s: s.isdigit(), item['ip'].split('.')))
    except Exception as e:
        continue

    val = geo_reader.get(item['ip']) or {}
    item.update({
        'country': val.get('country', {}).get('names', {}).get('en', ''),
        'country_code': val.get('country', {}).get('iso_code', ''),
        'city': val.get('city', {}).get('names', {}).get('en', ''),
        'latitude': val.get('location', {}).get('latitude', 'null'),
        'longitude': val.get('location', {}).get('longitude', 'null'),
    })

    vals = (
        item['time'],
        item['jail'],
        item['action'],
        item['ip'],
        item['country'],
        item['country_code'],
        item['city'],
        item['latitude'],
        item['longitude'],
    )
    cursor.execute(SQL_INSERT_TMP, vals)
cursor.execute(SQL_INSERT)

connection.commit()

cursor.close()
connection.close()
