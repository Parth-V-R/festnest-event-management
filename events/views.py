from django.shortcuts import render
from .models import Event

def home(request):
    events = Event.objects.all()
    return render(request, 'index.html', {'events': events})

def category_events(request, category):
    events = Event.objects.filter(category=category)
    return render(request, 'category.html', {
        'events': events,
        'category': category
    })