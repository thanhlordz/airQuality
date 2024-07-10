import json
from influxdb_client_3 import InfluxDBClient3, Point, WriteOptions, write_client_options, InfluxDBError
import datetime
import paho.mqtt.client as mqtt
import time

# InfluxDB configuration
host = "us-east-1-1.aws.cloud2.influxdata.com"
org = "51a6cb984cf08bb3"
token = "xHVxWKf0txy2X1umnPU5re4ngroMNYFOI3J3zyxVqt3BbWEXWlpnCS5Wbu35hq48K2zo8OWPiuH-tmFYpjWIDA=="
database = "air_data"


# MQTT broker information
broker_address = "localhost"
broker_port = 1883
topic = "home_sensor/air"

# Define callbacks for write responses
def success(self, data: str):
    status = "Success writing batch: data: {data}"
    assert status.startsWith('Success'), f"Expected {status} to be success"

def error(self, data: str, err: InfluxDBError):
    status = f"Error writing batch: config: {self}, data: {data}, error: {err}"
    assert status.startsWith('Success'), f"Expected {status} to be success"


def retry(self, data: str, err: InfluxDBError):
    status = f"Retry error writing batch: config: {self}, data: {data}, error: {err}"
    assert status.startsWith('Success'), f"Expected {status} to be success"
    
# Configure batching options
write_options = WriteOptions(batch_size=20, flush_interval=10_000, jitter_interval=2_000, retry_interval=5_000)
wco = write_client_options(success_callback=success,
                            error_callback=error,
                            retry_callback=retry,
                            write_options=write_options)

influx_client = InfluxDBClient3(
    token=token,
    host=host,
    org=org,
    database=database,
    write_client_options=wco)

def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print("Received message:", payload)

    # Parse JSON payload
    try:
        data = json.loads(payload)
        pm1 = data.get("pm1")
        pm2_5 = data.get("pm2_5")
        pm10 = data.get("pm10")
        
        if pm1 is not None and pm2_5 is not None and pm10 is not None:
            # Get current time
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Create a point
            point = Point("air_quality") \
                .field("PM1", pm1) \
                .field("PM2_5", pm2_5) \
                .field("PM10", pm10) \
                .time(current_time)

            # Write the point to InfluxDB with retry logic
            retry_attempts = 3
            while retry_attempts > 0:
                try:
                    write_api = influx_client.write()
                    write_api.write(point)
                    print("Data written to InfluxDB:", data)
                    break  # Exit loop on successful write
                except Exception as e:
                    print(f"Error writing to InfluxDB: {e}")
                    retry_attempts -= 1
                    print(f"Retrying... Attempts left: {retry_attempts}")
                    time.sleep(1)  # Wait before retrying
            else:
                print("Failed to write data after retries. Skipping data:", data)
        else:
            print("Invalid data format:", data)
    except json.JSONDecodeError:
        print("Error decoding JSON:", payload)

# Create MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

# Connect to broker
mqtt_client.connect(broker_address, broker_port)

# Subscribe to topic
mqtt_client.subscribe(topic)

# Start loop to listen for incoming messages
mqtt_client.loop_forever()
