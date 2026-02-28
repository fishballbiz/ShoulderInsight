from django.urls import path, re_path, include
from django.conf import settings
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path('diagnosis/', include('diagnosis.urls')),
    path('', RedirectView.as_view(url='/diagnosis/upload/', permanent=False)),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
