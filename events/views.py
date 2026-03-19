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
    
def event_detail(request, id):
    event = Event.objects.get(id=id)
    return render(request, 'event_detail.html', {'event': event})