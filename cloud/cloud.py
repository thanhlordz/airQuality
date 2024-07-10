import time
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import paho.mqtt.client as mqtt
import json
import datetime
import csv
import os

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = '/home/phamtung/Desktop/cloud/cloud.json'
PARENT_FOLDER_ID = "13mEVhvLwwe73zL04oeY0CsyAw3dck80l"

def authenticate(retry_attempts=3, retry_delay=5):
    for attempt in range(retry_attempts):
        try:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return creds
        except Exception as e:
            print(f"Error authenticating: {e}")
            if attempt < retry_attempts - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Authentication failed after multiple attempts.")
                raise

def upload_update(file_path, file_name, retry_attempts=3, retry_delay=5):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)
    
    for attempt in range(retry_attempts):
        try:
            # Check if the file already exists
            file_list = service.files().list(
                q=f"name='{file_name}' and parents in '{PARENT_FOLDER_ID}'",
                fields='files(id)'
            ).execute()

            if file_list.get('files', []):
                # File exists, get its ID
                file_id = file_list['files'][0]['id']
                # Update the file's content
                media_body = MediaFileUpload(file_path, resumable=True)
                service.files().update(
                    fileId=file_id,
                    media_body=media_body
                ).execute()
                print("File updated successfully.")
            else:
                # File does not exist, create a new one
                file_metadata = {
                    'name': file_name,
                    'parents': [PARENT_FOLDER_ID]
                }
                media_body = MediaFileUpload(file_path, resumable=True)
                service.files().create(
                    body=file_metadata,
                    media_body=media_body,
                    fields='id'
                ).execute()
                print("File uploaded successfully.")

            # If upload/update succeeded, break out of the loop
            break
            
        except Exception as e:
            print(f"Error uploading file: {e}")
            if attempt < retry_attempts - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Upload failed after multiple attempts.")
                raise


# MQTT broker information
broker_address = "localhost"
broker_port = 1883
topic = "home_sensor/air"

# Callback function to handle incoming messages
def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print("Received message:", payload)
    
    # Parse JSON message
    try:
        data = json.loads(payload)
        # Handle JSON data to python dictionary

        current_time = datetime.datetime.now()
        file_time = current_time.strftime("%d_%m_%Y")
        record_time = current_time.strftime("%d-%m-%Y %H:%M:%S")
        time_year = current_time.strftime("%Y")
        time_month = current_time.strftime("%m")
        time_day = current_time.strftime("%d")
        time_hour = current_time.strftime("%H")

        csv_name = "air_" + file_time
        
        data["timestamp"] = record_time
        data["year"] = time_year
        data["month"] = time_month
        data["day"] = time_day
        data["hour"] = time_hour
        
        # Writing data to a csv file
        csv_file_path = "/home/phamtung/Desktop/Collecting/" + csv_name + ".csv" 
        if not (os.path.exists(csv_file_path)):
            with open(csv_file_path, mode='w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                print("CSV file already exist.")
                writer.writerows[["Timestamp", "Year", "Month", "Day", "Hour", "PM1.0", "PM2.5", "PM10"], #Header
                [data["timestamp"], data["year"], data["month"], data["day"],data["hour"], data["pm1"], data["pm2_5"], data["pm10"]]] #Data 
        else:
            with open(csv_file_path, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                print("Appending data to CSV file.")
                writer.writerow([data["timestamp"], data["year"], data["month"], data["day"], data["hour"], 
                                 data["pm1"], data["pm2_5"], data["pm10"]])
        try:
            upload_update(csv_file_path, csv_name)
        except Exception as e:
            print(f"Failed to upload file: {e}")
            
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)

# Create MQTT client
client = mqtt.Client()
client.on_message = on_message

# Connect to broker
client.connect(broker_address, broker_port)

# Subscribe to topic
client.subscribe(topic)

# Start loop to listen for incoming messages
client.loop_forever()
