# 🛒 AI 스마트 매대 시스템 (FS_ai-smart-shelf)

AI 비전 및 데이터를 활용하여 오프라인 매대의 재고 및 유통기한을 효율적으로 관리하기 위한 웹 시스템입니다. (Django 기반)

---

## 🚀 로컬 환경 세팅 및 실행 방법

팀원들이 처음 프로젝트를 로컬에 세팅하고 실행하기 위한 가이드입니다. 터미널(PowerShell 또는 CMD)을 열고 아래 순서대로 진행해 주세요.

### 1. 프로젝트 가져오기 및 폴더 이동
```bash
git clone [https://github.com/ts030930/FS_ai-smart-shelf.git](https://github.com/ts030930/FS_ai-smart-shelf.git)
cd FS_ai-smart-shelf

2. 가상환경 생성 및 활성화
파이썬 패키지 충돌을 막기 위해 프로젝트 전용 가상환경을 만듭니다.

Windows 사용자:

Bash
python -m venv venv
venv\Scripts\activate
Mac/Linux 사용자:

Bash
python3 -m venv venv
source venv/bin/activate

주의: 명령어 입력 후 터미널 줄 맨 앞에 (venv)가 생겼는지 꼭 확인

3. 필수 패키지 한 번에 설치하기
requirements.txt에 기록된 장고(Django) 등의 패키지를 설치합니다.

Bash
pip install -r requirements.txt

4. 데이터베이스 뼈대 만들기
로컬 개발용 데이터베이스(db.sqlite3)를 초기화합니다.

Bash
python manage.py migrate

5. 장고 개발 서버 실행하기

Bash
python manage.py runserver
서버가 정상적으로 켜졌다면, 웹 브라우저를 열고 http://127.0.0.1:8000/ 으로 접속하여 확인합니다.

