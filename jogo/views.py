from django.shortcuts import render

def home(request):
    return render(request, "jogo/index.html")

# Create your views here.
