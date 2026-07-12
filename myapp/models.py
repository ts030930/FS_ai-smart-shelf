from django.db import models
from django.contrib.auth.models import User

# 1. 점포(사용자) 정보
class Store(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_setup_complete = models.BooleanField(default=False) # 초기 세팅 완료 여부

# 2. 매대 정보
class Shelf(models.Model):
    CATEGORY_CHOICES = [
        ('라면', '라면'),
        ('FF', 'FF (프레시푸드)'),
        ('빵', '빵'),
        ('과자', '과자'),
        ('음료수', '음료수'),
        ('주류', '주류'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    shelf_number = models.IntegerField() # 1번, 2번 매대...
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)