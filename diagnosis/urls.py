from django.urls import path
from . import views

app_name = 'diagnosis'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
]
