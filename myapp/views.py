from django.shortcuts import render

# Create your views here.
def dashboard(request):
    # request가 들어오면 dashboard.html 템플릿을 응답으로 돌려줍니다.
    return render(request, 'dashboard.html')