from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from .views import Home
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", Home.as_view(), name="home"),
    path("accounts/", include("django.contrib.auth.urls")),


    #incluir las urls condiguradas en pos.urls
    path("pos/",include('pos.urls', namespace="pos")),
]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

