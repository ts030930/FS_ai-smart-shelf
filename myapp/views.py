from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm # <-- 회원가입을 위한 도구 추가
from django.contrib.auth import login # <-- 가입 후 자동 로그인을 위한 도구 추가
from .models import Store, Shelf
import json
import time
import requests
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import os

# @login_required는 로그인이 안 된 사용자를 로그인 창으로 튕겨냅니다.
@login_required(login_url='/login/')
def dashboard(request):
    store, created = Store.objects.get_or_create(user=request.user)
    
    # 정보 입력이 안 되어 있다면 초기 설정 페이지로 보냅니다.
    if not store.is_setup_complete:
        return redirect('setup_store')
    
    # [추가된 부분] 현재 상점(회원)에 등록된 매대 목록을 번호순으로 가져옵니다.
    shelves = Shelf.objects.filter(store=store).order_by('shelf_number')
    
    # [추가된 부분] HTML 템플릿에서 사용할 수 있도록 context 딕셔너리에 담아 전달합니다.
    context = {
        'shelves': shelves
    }
    
    return render(request, 'dashboard.html', context)

@login_required(login_url='/login/')
def setup_store(request):
    store, _ = Store.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        shelf_count = int(request.POST.get('shelf_count', 0))
        
        # Step 1: 매대 개수 입력받고 카테고리 선택 창 띄우기
        if 'step1' in request.POST:
            return render(request, 'setup.html', {'shelf_count': range(1, shelf_count + 1), 'step': 2})
        
        # Step 2: 카테고리 정보 저장하기
        elif 'step2' in request.POST:
            for i in range(1, shelf_count + 1):
                category = request.POST.get(f'category_{i}')
                Shelf.objects.create(store=store, shelf_number=i, category=category)
            
            store.is_setup_complete = True
            store.save()
            return redirect('dashboard')
            
    return render(request, 'setup.html', {'step': 1})

# 1. 회원가입 기능
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # 회원가입 성공 시 바로 로그인 처리
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

# 2. 회원정보 및 매대 세팅 수정 기능
@login_required(login_url='/login/')
def profile(request):
    store = Store.objects.get(user=request.user)
    shelves = Shelf.objects.filter(store=store).order_by('shelf_number')
    
    if request.method == 'POST':
        if 'reset' in request.POST:
            # [매대 전체 재설정] 기존 매대를 다 지우고 setup 단계로 돌려보냅니다.
            shelves.delete()
            store.is_setup_complete = False
            store.save()
            return redirect('setup_store')
        elif 'update' in request.POST:
            # [매대 품목 수정] 바뀐 품목 정보를 저장합니다.
            for shelf in shelves:
                new_category = request.POST.get(f'category_{shelf.id}')
                if new_category:
                    shelf.category = new_category
                    shelf.save()
            return redirect('profile')
            
    return render(request, 'profile.html', {'store': store, 'shelves': shelves})

def coss_forward_push(request):
    if request.method == "POST":
        data = json.loads(request.body)
        target = data.get("target", "")
        
        # 1. 타겟 AE 이름 변경 (smart_shelf_ae -> ae_fs)
        ae_name = "ae_fs" 
        cnt_name = f"shelf_{target}_control"
        
        # 2. 매뉴얼에 명시된 실제 Mobius API 엔드포인트 주소
        url = f"https://onem2m.iotcoss.ac.kr/Mobius/{ae_name}/{cnt_name}"
            
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;ty=4", 
            "X-M2M-RI": "1234",
            
            # 3. Origin 이름 변경 (SOrigin -> SOrigin_fs)
            "X-M2M-Origin": "SOrigin_fs", 
            
            "X-API-KEY": "oEBJa3qH9kAPRnINwUCGR0UK8zJKs9rq",
            "X-AUTH-CUSTOM-LECTURE": "LCT_20260002",
            "X-AUTH-CUSTOM-CREATOR": "dgu2023110430"
        }
        
        # 3. 전송할 데이터(cin) 구성[cite: 1]
        payload = {
            "m2m:cin": {
                "con": "forward_push_start", # 실제 제어 명령값[cite: 1]
                "lbl": ["전진진열_명령"]
            }
        }
        
        try:
            # 4. json=payload 대신 data=json.dumps()를 사용하여 강제 헤더 덮어쓰기 방지
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            # 5. 실패 시 터미널에 명확한 원인 출력
            if not response.ok:
                print("\n" + "="*40)
                print("🚨 COSS API 전송 실패 🚨")
                print(f"요청 URL: {url}")
                print(f"상태 코드: {response.status_code}")
                print(f"에러 메시지: {response.text}")
                print("="*40 + "\n")
                
                # 프론트엔드로 에러 메시지를 함께 보냄
                return JsonResponse({"error": response.text}, status=response.status_code)

            return JsonResponse({"status": "success"}, status=response.status_code)
            
        except requests.exceptions.RequestException as e:
            print(f"네트워크 에러 발생: {e}")
            return JsonResponse({"error": "Network Error"}, status=500)
        

# 1. LLM 분석을 처리하는 API 뷰 (비동기 통신용)
def llm_analyze(request):
    if request.method == "POST":
            try:
                # 1. 현재 로그인한 유저의 점포 정보 가져오기
                store = Store.objects.get(user=request.user)
                
                # 2. 마르코프 체인 확률 행렬 계산 (기존 get_movement_probability 로직 활용)
                logs = SensorLog.objects.all().order_by('timestamp')
                result_matrix = {}
                if logs.count() >= 2:
                    df = pd.DataFrame(list(logs.values('sensor_id', 'timestamp')))
                    df['next_sensor'] = df['sensor_id'].shift(-1)
                    df = df.dropna(subset=['next_sensor'])
                    try:
                        transition_matrix = pd.crosstab(df['sensor_id'], df['next_sensor'], normalize='index')
                        result_matrix = transition_matrix.to_dict(orient='index')
                    except:
                        result_matrix = {} # 에러 시 빈 값으로 진행

                # 3. 현재 시간(시) 구하기
                from datetime import datetime
                current_hour = datetime.now().hour
                
                # 4. ⭐ 맨 밑에 만든 GPT 분석 함수 호출하기!
                # global current_shelves_data 변수를 그대로 인자로 넘겨줍니다.
                ai_report = analyze_shelf_data_with_gpt(
                    store=store, 
                    current_shelves_data=current_shelves_data, 
                    result_matrix=result_matrix, 
                    current_hour=current_hour
                )
                
                # 5. GPT가 돌려준 JSON 분석 리포트를 그대로 프론트엔드에 반환
                return JsonResponse({"status": "success", "report": ai_report}, status=200)
            
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)
                
    return JsonResponse({"error": "잘못된 요청입니다. POST 메서드만 지원합니다."}, status=405)

# 2. 결과 확인 페이지 렌더링 뷰
def analysis_result_page(request):
    # TODO: 결과 페이지에 보여줄 데이터를 딕셔너리 형태로 context에 담아 템플릿으로 전달합니다.
    context = {
        'page_title': '상세 분석 결과'
    }
    return render(request, 'analysis_result.html', context)

#@login_required(login_url='/login/')
def setup_sensor_subscription(request):
    try:
        my_django_url = "http://127.0.0.1:8000/sensor-receive/"
        
        ae_name = "ae_fs"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;ty=23", 
            "X-M2M-RI": "sub_req_multi",
            "X-M2M-Origin": "SOrigin_fs", 
            "X-API-KEY": "oEBJa3qH9kAPRnINwUCGR0UK8zJKs9rq",
            "X-AUTH-CUSTOM-LECTURE": "LCT_20260002",
            "X-AUTH-CUSTOM-CREATOR": "dgu2023110430"
        }

        total_shelves = [1, 2, 3, 4]#되면 수정하기
        success_count = 0

        for num in total_shelves:
            cnt_name = f"shelf_{num}_sensor" 
            url = f"https://onem2m.iotcoss.ac.kr/Mobius/{ae_name}/{cnt_name}"
            
            payload = {
                "m2m:sub": {
                    "rn": f"django_sub_shelf_{num}", 
                    "nu": [my_django_url],
                    "nct": 2,
                    "enc": {"net": [3]}
                }
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code in [201, 409]: # 성공했거나 이미 등록된 경우
                success_count += 1
                
        return JsonResponse({
            "status": "success", 
            "message": f"총 {len(total_shelves)}개 매대 중 {success_count}개 구독 연동 성공!"
        }, status=200)
            
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
current_shelves_data = {
    "S_01": {"dwell_time_seconds": 0, "timestamp": None, "count":0,"passcount":0},
    "S_02": {"dwell_time_seconds": 0, "timestamp": None, "count":0,"passcount":0},
    "S_03": {"dwell_time_seconds": 0, "timestamp": None, "count":0,"passcount":0},
}
@csrf_exempt
def receive_sensor_data(request):
    global current_shelves_data
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            SensorLog.objects.create(
                sensor_id=payload.get("sensor_id"),
                dwell_time_seconds=payload.get("dwell_time_seconds"),
                timestamp=payload.get("timestamp")
            )
            sensor_id = payload.get("sensor_id") 
            dwell_time = payload.get("dwell_time_seconds")
            timestamp = payload.get("timestamp")
            
            # 2. 해당 센서 ID가 우리 매대 목록에 있다면 그 칸에만 덮어쓰기
            if sensor_id in current_shelves_data:
                current_shelves_data[sensor_id]["dwell_time_seconds"] += dwell_time
                current_shelves_data[sensor_id]["timestamp"] = timestamp
                if dwell_time>3:
                    current_shelves_data[sensor_id]["count"]+=1
                else:
                    current_shelves_data[sensor_id]["passcount"]+=1
            return JsonResponse({"status": "success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

def get_movement_probability(request):

    # 1. DB에서 시간순으로 로그 긁어오기
    logs = SensorLog.objects.all().order_by('timestamp')
    
    if logs.count() < 2:
        return JsonResponse({"error": "동선을 계산하기 위한 로그 데이터가 부족합니다. (최소 2개 필요)"}, status=400)
    
    # 2. 장고 데이터를 판다스 데이터프레임(엑셀 형태)으로 변환
    df = pd.DataFrame(list(logs.values('sensor_id', 'timestamp')))
    
    # 3. 마르코프 체인 적용: 현재 센서 바로 다음에 등장한 센서 매칭하기
    df['next_sensor'] = df['sensor_id'].shift(-1)
    
    # 마지막 행은 다음 동선이 없으므로 제거
    df = df.dropna(subset=['next_sensor'])
    
    # 4. 교차 표(Crosstab)를 생성하고 행(Row) 기준 확률(normalize='index') 계산
    # 예: S_01에 있던 사람들 중 각 센서로 이동한 비율 계산
    try:
        transition_matrix = pd.crosstab(df['sensor_id'], df['next_sensor'], normalize='index')
        
        # 5. 프론트엔드(Vue)나 차트 라이브러리가 읽기 좋은 딕셔너리 형태로 변환
        # 결과 예시: {"S_01": {"S_02": 0.7, "S_03": 0.3}, "S_02": ...}
        result_matrix = transition_matrix.to_dict(orient='index')
        
        return JsonResponse({
            "status": "success",
            "description": "각 매대(Key)에서 다음 매대로 이동할 확률 데이터입니다.",
            "matrix": result_matrix
        }, status=200)
        
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def analyze_shelf_data_with_gpt(store, current_shelves_data, result_matrix, current_hour):
    # 1. OpenAI 클라이언트 초기화
    client = OpenAI()
    
    # 2. 매대 카테고리 정보 동적 조회
    shelves = Shelf.objects.filter(store=store).order_by('shelf_number')
    shelf_mapping = {}
    for shelf in shelves:
        shelf_key = f"S_{str(shelf.shelf_number).zfill(2)}"
        shelf_mapping[shelf_key] = f"{shelf.category} 매대"
        
    if not shelf_mapping:
        for key in current_shelves_data.keys():
            shelf_mapping[key] = f"미등록({key}) 매대"

    # 💡 [추가] DB에서 모든 센서 로그를 시간순으로 조회하여 포맷팅
    raw_logs = SensorLog.objects.all().order_by('timestamp')
    logs_data = [
        {
            "sensor_id": log.sensor_id,
            "dwell_time_seconds": log.dwell_time_seconds,
            "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else ""
        }
        for log in raw_logs
    ]

    # 💡 프롬프트 엔지니어링: 기존 양식 유지 + RAW 로그 데이터 추가 주입
    prompt = f"""
    당신은 데이터 기반 데이터 분석가이자 리테일 매장 관리 전문가입니다.
    현재 시간은 {current_hour}시입니다. 다음 대형마트 스마트 매대 데이터를 분석하여 매장 최적화 솔루션을 제공하세요.

    [매대 ID 설명]
    {json.dumps(shelf_mapping, ensure_ascii=False, indent=2)}

    [분석 대상 데이터]
    1. 매대별 실시간 고객 행동 정보 (현재 시간대 누적):
    {json.dumps(current_shelves_data, ensure_ascii=False, indent=2)}

    2. 마르코프 체인 기반 고객 매대 이동 확률 행렬 (Result Matrix):
    {json.dumps(result_matrix, ensure_ascii=False, indent=2)}
    * 설명: 특정 매대(Row)에서 물건을 본 고객이 다음으로 어떤 매대(Column)로 갈지 확률을 나타냄.

    3. 전체 센서 로그 기록 (Raw Logs - 시간순):
    {json.dumps(logs_data, ensure_ascii=False, indent=2)}
    * 설명: 매장에 쌓인 개별 센서 감지 원본 데이터입니다. 시간대별 유동량 변화 추이를 분석하는 데 활용하세요.

    [상황별 분석 가이드라인]
    - 통행 병목 현상 해소: 특정 매대의 passcount(유동량)는 매우 높은데 count(관심고객) 및 dwell_time_seconds(체류시간)가 극도로 낮다면, 통로 유동성에 방해가 되거나 시인성이 떨어지는 병목/소외 구간입니다. 이동 확률 Matrix를 보고 트래픽이 밀리는 정체 경로를 찾아내어 동선 분산 방안을 제안하세요.
    - 시간별 체류시간 및 할인 추천: 현재 시간({current_hour}시)의 특성을 고려하십시오. 다른 매대에 비해 체류시간이나 관심고객 수가 저조한 매대를 타겟팅하여, 고객을 붙잡을 수 있는 '타임 세일/마감 할인 마케팅 타겟 매대' 및 '적정 할인율'을 제안하세요.
    - 하드웨어 가동 명령 (전진진열 모터): 체류시간이 짧거나 관심도가 떨어진 매대 중, 상품 시인성 개선이 시급한 매대를 딱 하나 지정하여 전진진열 모터 작동 명령(True/False)을 내리세요.

    [출력 포맷 규칙]
    반드시 아래의 JSON 구조와 완벽히 일치하는 데이터만 반환하세요. 코드 블록(```json)을 사용하지 말고 순수 JSON 문자열만 출력해야 합니다.
    {{
        "bottleneck_analysis": "병목 구간 진단 및 동선 분산 해법 기술 (한국어)",
        "time_based_marketing": {{
            "target_shelf_id": "할인이 필요한 매대 ID (예: S_02)",
            "reason": "현재 시간대 및 데이터 기준 타겟 선정 이유",
            "recommended_discount_rate": "추천 할인율 (예: 15%)",
            "strategy_detail": "구체적인 타임세일 방식 제안"
        }},
        "general_marketing_solutions": [
            "연관 진열 제안 1",
            "프로모션 제안 2"
        ],
        "hardware_motor_control": {{
            "trigger_shelf_id": "모터 제어가 필요한 매대 ID",
            "motor_active": true
        }}
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data-driven retail management system. You always respond in strict JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, 
            temperature=0.2 
        )
        
        result_json = json.loads(response.choices[0].message.content)
        return result_json

    except Exception as e:
        return {"error": f"AI 분석 실패: {str(e)}"}