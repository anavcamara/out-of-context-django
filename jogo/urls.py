from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/partida/nova/", views.nova_partida, name="nova_partida"),
    path("api/partida/<int:partida_id>/tentativa/", views.tentativa, name="tentativa"),
    path("api/partida/<int:partida_id>/dica/", views.dica, name="dica"),
    path("api/obras/", views.obras, name="obras"),
    path("contas/cadastro/", views.cadastro, name="cadastro"),
    path("contas/", include("django.contrib.auth.urls")),
]