from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "public/home.html")

from django.shortcuts import render


def home(request):
    return render(request, "public/home.html")


def features(request):
    return render(request, "public/features.html")


def pricing(request):
    return render(request, "public/pricing.html")


def about(request):
    return render(request, "public/about.html")


def contact(request):
    return render(request, "public/contact.html")