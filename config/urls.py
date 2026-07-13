from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from myapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # 로그인/로그아웃 (장고 기본 기능 사용)
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # 메인 대시보드 및 초기 설정
    path('', views.dashboard, name='dashboard'),
    path('setup/', views.setup_store, name='setup_store'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('api/coss/forward-push/', views.coss_forward_push, name='coss_forward_push'),
]

