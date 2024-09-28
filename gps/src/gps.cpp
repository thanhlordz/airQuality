#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

#define RXPin D5
#define TXPin D6
const char* ssid = "AetLab";                //Name and Password Wifi
const char* password = "123456799z";
const char* mqttServer = "192.168.8.130";          //Ip MQTT Server

WiFiClient espClient;
PubSubClient client(espClient);

void connectMQTT(){
  while (!client.connected()){
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void wifiConnect(){
  if(WiFi.status() != WL_CONNECTED) {
    Serial.print("Connecting to WiFi ");
    WiFi.begin(ssid, password);
    while(WiFi.status() != WL_CONNECTED){
      Serial.print(".");
      delay(200);
    }
    Serial.println("Connected");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  }
}

TinyGPSPlus gps;
SoftwareSerial ss(RXPin, TXPin);
struct pms5003data {
  uint16_t framelen;
  uint16_t pm10_standard, pm25_standard, pm100_standard;
  uint16_t pm10_env, pm25_env, pm100_env;
  uint16_t particles_03um, particles_05um, particles_10um, particles_25um, particles_50um, particles_100um;
  uint16_t unused;
  uint16_t checksum;
};

struct Location{
  double latitude;
  double longitude;
};

Location loca;
struct pms5003data data;

boolean readPMSdata(Stream *s) {
  if (! s->available()) {
    return false;
  }
  // Read a byte at a time until we get to the special '0x42' start-byte
  if (s->peek() != 0x42) {
    s->read();
    return false;
  }
  // Now read all 32 bytes
  if (s->available() < 32) {
    return false;
  }
  uint8_t buffer[32];    
  uint16_t sum = 0;
  s->readBytes(buffer, 32);
  // get checksum ready
  for (uint8_t i=0; i<30; i++) {
    sum += buffer[i];
  }
  /* debugging
  for (uint8_t i=2; i<32; i++) {
    Serial.print("0x"); Serial.print(buffer[i], HEX); Serial.print(", ");
  }
  Serial.println();
  */
  // The data comes in endian'd, this solves it so it works on all platforms
  uint16_t buffer_u16[15];
  for (uint8_t i=0; i<15; i++) {
    buffer_u16[i] = buffer[2 + i*2 + 1];
    buffer_u16[i] += (buffer[2 + i*2] << 8);
  }
  // put it into a nice struct :)
  memcpy((void *)&data, (void *)buffer_u16, 30);
  if (sum != data.checksum) {
    Serial.println("Checksum failure");
    return false;
  }
  // success!
  return true;
}

void setup(){
  Serial.begin(9600);
  ss.begin(9600);
  wifiConnect();
  client.setServer(mqttServer, 1883);
  delay(200); 
}


void loop(){
  connectMQTT();
  wifiConnect();
  while(ss.available() > 0){
    char c = ss.read();
    gps.encode(c);
  }

  if(gps.location.isValid()){
    loca.latitude = gps.location.lat();
    Serial.print("Latitude: ");
    Serial.println(gps.location.lat(), 6); 

    loca.longitude = gps.location.lng();
    Serial.print("Longitude: ");
    Serial.println(gps.location.lng(), 6);
  } else {
    Serial.println("Location Invalid");
  }

  if (readPMSdata(&Serial)) {
    // Serial.println("---------------------------------------");
    // Serial.println("Concentration Units (standard)");
    // Serial.print("PM 1.0: "); Serial.print(data.pm10_standard);
    // Serial.print("\t\tPM 2.5: "); Serial.print(data.pm25_standard);
    // Serial.print("\t\tPM 10: "); Serial.println(data.pm100_standard);
    // Serial.println("---------------------------------------");
    // Serial.println("Concentration Units (environmental)");
    // Serial.print("PM 1.0: "); Serial.print(data.pm10_env);
    // Serial.print("\t\tPM 2.5: "); Serial.print(data.pm25_env);
    // Serial.print("\t\tPM 10: "); Serial.println(data.pm100_env);
    // Serial.println("---------------------------------------");
    // Serial.print("Particles > 0.3um / 0.1L air:"); Serial.println(data.particles_03um);
    // Serial.print("Particles > 0.5um / 0.1L air:"); Serial.println(data.particles_05um);
    // Serial.print("Particles > 1.0um / 0.1L air:"); Serial.println(data.particles_10um);
    // Serial.print("Particles > 2.5um / 0.1L air:"); Serial.println(data.particles_25um);
    // Serial.print("Particles > 5.0um / 0.1L air:"); Serial.println(data.particles_50um);
    // Serial.print("Particles > 10.0 um / 0.1L air:"); Serial.println(data.particles_100um);
    // Serial.println("---------------------------------------");
    
    StaticJsonDocument<200> doc;
    char msg[100];
    doc["pm2_5"] = data.pm25_standard;
    doc["latitude"] = loca.latitude;
    doc["longitude"] = loca.longitude;
  
    serializeJson(doc, msg);
    Serial.print("Package: ");
    Serial.println(msg);
    client.publish("home_sensor/air", msg);
    delay(10000);
  }
}
