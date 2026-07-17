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
            data = json.loads(request.body)
            target_shelf = data.get('target_shelf', '알 수 없는 매대')
            
            # TODO: 1. DB에서 해당 매대의 통계 데이터 조회
            # TODO: 2. OpenAI / Claude API 호출 및 프롬프트 전송
            # TODO: 3. LLM의 답변 수신
            
            # 임시 더미 데이터 (LLM 응답 시뮬레이션)
            mock_llm_response = f"분석 완료! {target_shelf}의 체류시간이 길지만 구매 전환율이 낮습니다. 상품이 뒤로 밀려있을 가능성이 높으니 전진진열을 추천합니다."
            
            return JsonResponse({"insight": mock_llm_response}, status=200)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "잘못된 요청입니다."}, status=405)

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
                current_shelves_data[sensor_id]["dwell_time_seconds"] = dwell_time
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
