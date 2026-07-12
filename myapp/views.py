from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm # <-- 회원가입을 위한 도구 추가
from django.contrib.auth import login # <-- 가입 후 자동 로그인을 위한 도구 추가
from .models import Store, Shelf

# @login_required는 로그인이 안 된 사용자를 로그인 창으로 튕겨냅니다.
@login_required(login_url='/login/')
def dashboard(request):
    store, created = Store.objects.get_or_create(user=request.user)
    
    # 정보 입력이 안 되어 있다면 초기 설정 페이지로 보냅니다.
    if not store.is_setup_complete:
        return redirect('setup_store')
    
    return render(request, 'dashboard.html')

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