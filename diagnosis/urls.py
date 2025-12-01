from django.urls import path
from . import views

app_name = 'diagnosis'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('analyzing/<uuid:examination_id>/', views.analyzing_view, name='analyzing'),
    path('result/<uuid:examination_id>/', views.result_view, name='result'),
]
