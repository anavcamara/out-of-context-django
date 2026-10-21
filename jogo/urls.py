from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/partida/nova/", views.nova_partida, name="nova_partida"),
    path("api/partida/<int:partida_id>/tentativa/", views.tentativa, name="tentativa"),
]