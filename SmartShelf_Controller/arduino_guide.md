# 🛒 AI 스마트 매대 하드웨어 제어 (전진진열 시스템)

AI 스마트 매대 시스템(`FS_ai-smart-shelf`)의 하드웨어 구동부(Actuator) 및 센서(Sensor) 제어를 위한 아두이노 펌웨어입니다. 웹 기반의 플랫폼과 연동하여 **자동 전진진열 기능**을 수행하고, 매대의 **빈 공간(재고 소진) 상태를 실시간으로 모니터링**합니다.

** 레일형 전진진열 시스템을 제작하려했는데 가진게 서보모터 밖에 없어서 슬라이더-크랭크 메커니즘을 사용했습니다 **
자세한 모양은 사진 참조
---

## ⚙️ 하드웨어 구성 요소 (Hardware Components)

* **MCU:** Arduino Uno R4 WiFi
* **Actuator:** SG90 Micro Servo Motor (슬라이더-크랭크 메커니즘을 이용한 전진 푸셔 구동)
* **Sensor:** HC-SR04 초음파 센서 (매대 앞 상품 유무 감지)
* **기타 재료:** 폼보드, 골판지 (매대 기구물 및 크랭크 제작용), 브레드보드, 점퍼 와이어

---

## 🔌 핀 맵 및 배선 (Pin Map)

| 부품명 | 아두이노 핀 | 역할 설명 |
|---|---|---|
| **SG90 Servo** | `5V`, `GND` | 모터 전원 공급 |
| | `D9` (PWM) | 서보모터 제어 신호 |
| **HC-SR04** | `5V`, `GND` | 센서 전원 공급 |
| | `D10` | 초음파 송신 (Trig) |
| | `D11` | 초음파 수신 (Echo) |

> ⚠️ **주의 (하드웨어 조립 팁):** > 초음파 센서 장착 시, 좁은 매대 양옆 폼보드 벽면의 초음파 난반사를 막기 위해 송수신부에 종이나 폼보드로 원통형 가이드(깔때기)를 씌우는 것을 권장합니다.

---

## 💻 개발 환경 및 라이브러리 (Software Setup)

1. **IDE:** Arduino IDE 2.x 사용
2. **보드 매니저:** `Arduino UNO R4 Boards` 설치 필수 (상단 메뉴 `Tools` > `Board` > `Arduino UNO R4 WiFi` 선택)
3. **필수 라이브러리:** 아두이노 라이브러리 매니저에서 아래 패키지들을 설치해야 합니다.
   * `WiFiS3` (내장 WiFi 모듈 제어용)
   * `ArduinoMqttClient` (MQTT 프로토콜 통신용)
   * `ArduinoJson` (JSON 데이터 파싱 및 생성, v7 이상 권장)
   * `Servo` (서보모터 구동용)

---

## 📡 통신 규격 (MQTT Protocol)

COSS (oneM2M) 플랫폼과 MQTT 방식으로 통신하며, JSON 페이로드를 주고받습니다.

### 1. 명령 수신 (Subscribe : 백엔드 ➡️ 하드웨어)
* **Topic:** `ae_fs/shelf_1_control`
* **Payload (JSON):**
  ```json
  {
    "m2m:cin": {
      "con": "forward_push_start",
      "lbl": [ "전진진열_명령" ]
    }
  }