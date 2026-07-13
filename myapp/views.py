from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm # <-- 회원가입을 위한 도구 추가
from django.contrib.auth import login # <-- 가입 후 자동 로그인을 위한 도구 추가
from .models import Store, Shelf
import json
import time
import requests
from django.http import JsonResponse

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