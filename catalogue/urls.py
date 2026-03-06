from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("book/<int:id_livre>/", views.book_detail, name="book_detail"),
    path("reserve/", views.reserve_view, name="reserve"),
]