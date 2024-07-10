from influxdb_client_3 import InfluxDBClient3, Point
import datetime

host = "us-east-1-1.aws.cloud2.influxdata.com"
org = "51a6cb984cf08bb3"
token = "xHVxWKf0txy2X1umnPU5re4ngroMNYFOI3J3zyxVqt3BbWEXWlpnCS5Wbu35hq48K2zo8OWPiuH-tmFYpjWIDA=="
database = "air_data"

client = InfluxDBClient3(
    token=token,
    host=host,
    org=org,
    database=database)

