#include <WiFiS3.h>        // Arduino Uno R4 WiFi용 라이브러리
#include <PubSubClient.h>  // MQTT 통신 라이브러리
#include <Servo.h>         // 서보모터 제어 라이브러리

// ==========================================
// [TODO] 네트워크 및 플랫폼 설정 (현준님과 확인 후 입력)
// ==========================================
const char* ssid = "iPhone";           // 와이파이 이름
const char* password = "pmit6331!";   // 와이파이 비밀번호
const char* mqtt_server = "172.20.10.5";       // COSS/oneM2M 서버(브로커) IP
const int mqtt_port = 1883;                    // MQTT 포트 (기본 1883)

// 구독(Sub)할 토픽: 웹에서 이 토픽으로 명령을 발행합니다.
const char* sub_topic = "ae_fs/shelf_1_control"; 
// 발행(Pub)할 토픽: 동작 완료 후 웹으로 상태를 알려줍니다. (옵션)
const char* pub_topic = "ae_fs/shelf_1_status";  

// ==========================================
// 핀 맵핑 및 전역 객체 선언
// ==========================================
const int servoPin = 9;   // SG90 서보모터 PWM 핀
Servo pusherServo;

WiFiClient espClient;
PubSubClient client(espClient);

// ==========================================
// 함수 선언
// ==========================================
void setupWiFi();
void reconnectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void executeForwardPush();

void setup() {
  Serial.begin(9600);
  
  // 1. 하드웨어 초기화
  pusherServo.attach(servoPin);
  pusherServo.write(0); // 초기 위치(0도)로 셋팅
  
  // 2. 통신 초기화
  setupWiFi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback); // 메시지 수신 시 실행될 콜백 함수 등록
}

void loop() {
  // MQTT 연결 유지 및 수신 대기
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop(); 
}

// ==========================================
// 1. MQTT 수신 콜백 함수 (웹 명령 캐치)
// ==========================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("✅ 메시지 수신 [Topic: ");
  Serial.print(topic);
  Serial.print("] Payload: ");
  Serial.println(message);

  // Payload 안에 "forward_push_start" 문자열이 포함되어 있는지 검사
  // (ArduinoJson 라이브러리를 써도 되지만, 가벼운 구현을 위해 String 검색 사용)
  if (message.indexOf("forward_push_start") >= 0) {
    Serial.println("웹 명령 확인: 전진진열 메커니즘을 가동합니다.");
    executeForwardPush();
  }
}

// ==========================================
// 2. 전진진열 기구부 구동 함수 (슬라이더-크랭크)
// ==========================================
void executeForwardPush() {
  // 모터 동작 중에는 다른 명령이 들어와도 꼬이지 않도록 주의 (필요시 flag 변수 사용)
  Serial.println("--> 서보모터 전진 (0도 -> 180도)");
  pusherServo.write(180); // 상품을 미는 각도 (기구물에 맞게 각도 조절 필요)
  delay(1000);            // 밀고 있는 상태 유지 (1초)
  
  Serial.println("--> 서보모터 복귀 (180도 -> 0도)");
  pusherServo.write(0);   // 원위치로 복귀
  delay(1000);            // 복귀 완료 대기

  Serial.println("전진진열 완료.");

  // (선택사항) 백엔드로 동작이 완료되었음을 알려줌
  // client.publish(pub_topic, "{\"status\": \"forward_push_done\"}");
}

// ==========================================
// 3. WiFi 및 MQTT 연결 함수 (기본 보일러플레이트)
// ==========================================
void setupWiFi() {
  delay(10);
  Serial.print("\nConnecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // 기존 코드 어딘가에 있는 WiFi 연결 완료 부분
  Serial.println("WiFi connected.");
  // ⭐ 여기에 2초 대기 시간을 추가해 보세요!
  delay(2000); 
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // 랜덤 클라이언트 ID 생성
    String clientId = "UnoR4Client-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      // 연결 성공 시 지정된 토픽 구독
      client.subscribe(sub_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
} 