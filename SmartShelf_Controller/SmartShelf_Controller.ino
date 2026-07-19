#include <WiFiS3.h> 
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h> 
#include <Servo.h>

// --- 1. 사용자 설정 (TODO: 환경에 맞게 수정) ---
char ssid[] = "YOUR_WIFI_SSID";     
char pass[] = "YOUR_WIFI_PASSWORD"; 
char mqtt_server[] = "192.168.0.100"; 
int mqtt_port = 1883;                 

char subscribeTopic[] = "ae_fs/shelf_1_control"; // 웹 -> 아두이노 명령 수신
char publishTopic[] = "ae_fs/shelf_1_status";    // 아두이노 -> 서버 상태 보고

// --- 2. 하드웨어 핀 및 동작 설정 ---
const int servoPin = 9;              
const int trigPin = 10;
const int echoPin = 11;

int pushStartAngle = 0;       
int pushEndAngle = 180;      
unsigned long pushDuration = 1000; 
const int EMPTY_THRESHOLD = 10; // 10cm 이상이면 비어있음으로 판단

// --- 3. 전역 변수 ---
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);
Servo pushServo;

// 타이머 및 상태 관리용 변수
unsigned long lastSensorCheck = 0;
const long sensorInterval = 2000; // 2초(2000ms)마다 거리 측정
bool lastEmptyState = false;      // 이전 상태 저장 (서버 중복 전송 방지용)

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // 핀 초기화
  pushServo.attach(servoPin);
  pushServo.write(pushStartAngle); 
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  Serial.println("System Initialization Started...");

  // WiFi 연결
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");

  // MQTT 연결
  if (!mqttClient.connect(mqtt_server, mqtt_port)) {
    Serial.println("MQTT connection failed!");
    while (1); 
  }
  Serial.println("MQTT Connected!");

  mqttClient.subscribe(subscribeTopic);
  mqttClient.onMessage(onMqttMessage);
}

void loop() {
  // 1. MQTT 통신 유지 및 수신 확인 (가장 중요)
  mqttClient.poll();

  if (WiFi.status() != WL_CONNECTED) {
    reconnectWiFi();
  }

  // 2. Non-blocking 방식으로 2초마다 초음파 센서 확인
  unsigned long currentMillis = millis();
  if (currentMillis - lastSensorCheck >= sensorInterval) {
    lastSensorCheck = currentMillis;
    
    float distance = getDistance();
    bool currentEmptyState = (distance > EMPTY_THRESHOLD);

    // 디버깅용 출력
    Serial.print("Current Distance: ");
    Serial.print(distance);
    Serial.println(" cm");

    // 3. 상태가 변했을 때만 서버로 상태 전송 (예: 채워져 있다가 비워졌을 때)
    if (currentEmptyState != lastEmptyState) {
      lastEmptyState = currentEmptyState;
      if (currentEmptyState) {
        Serial.println("Event: Shelf is Empty!");
        publishStatus("empty"); // 백엔드에 "비었음" 알림
      } else {
        Serial.println("Event: Shelf is Restocked.");
        publishStatus("occupied"); // 백엔드에 "채워짐" 알림
      }
    }
  }
}

// --- 사용자 정의 함수 ---

float getDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000); // 30ms 타임아웃 추가 (블로킹 방지)
  if (duration == 0) return 999.0; // 감지 범위를 벗어난 경우 무한대(999) 처리
  
  return (duration * 0.034) / 2;
}

void onMqttMessage(int messageSize) {
  String payload = "";
  while (mqttClient.available()) {
    payload += (char)mqttClient.read();
  }
  Serial.print("Received MQTT Payload: ");
  Serial.println(payload);

  JsonDocument doc;
  deserializeJson(doc, payload);

  String conValue = doc["m2m:cin"]["con"]; 

  if (conValue == "forward_push_start") {
    Serial.println("Command: Starting Forward Push...");
    performForwardPush();
  }
}

void performForwardPush() {
  // 전진
  for (int angle = pushStartAngle; angle <= pushEndAngle; angle += 2) {
    pushServo.write(angle);
    delay(15);
  }
  
  delay(pushDuration); 
  
  // 후진
  for (int angle = pushEndAngle; angle >= pushStartAngle; angle -= 2) {
    pushServo.write(angle);
    delay(15);
  }

  Serial.println("Push Completed.");
  publishStatus("forward_push_done"); // 완료 상태를 서버에 전송
}

void publishStatus(String statusValue) {
  JsonDocument doc;
  doc["status"] = statusValue; // 플랫폼 규격에 맞게 수정 필요

  String payload;
  serializeJson(doc, payload);

  mqttClient.beginMessage(publishTopic);
  mqttClient.print(payload);
  mqttClient.endMessage();
  
  Serial.print("Published to server: ");
  Serial.println(payload);
}

void reconnectWiFi() {
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }
}