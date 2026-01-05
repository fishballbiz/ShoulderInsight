from django.urls import path
from . import views

app_name = 'diagnosis'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('analyzing/<uuid:examination_id>/', views.analyzing_view, name='analyzing'),
    path('api/analyze/<uuid:examination_id>/', views.analyze_api, name='analyze_api'),
    path('result/<uuid:examination_id>/', views.result_view, name='result'),
    path('diseases/', views.diseases_view, name='diseases'),
    path('grid-poc/', views.grid_poc_view, name='grid_poc'),
]
