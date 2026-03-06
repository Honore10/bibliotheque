from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("catalogue.urls")),
    path("", include("membres.urls")),
    path("staff/", include("staff.urls")),
    path("administration/", include("administration.urls")),
    path("debug/me/", core_views.debug_me, name="debug_me"),
]
