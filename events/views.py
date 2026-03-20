from django.shortcuts import render, get_object_or_404, redirect
from .models import Event
from django.contrib.auth.decorators import login_required

# Existing views
def home(request):
    events = Event.objects.all()
    return render(request, 'index.html', {'events': events})

def category_events(request, category):
    events = Event.objects.filter(category=category)
    return render(request, 'category.html', {
        'events': events,
        'category': category
    })

# ✅ ADD THIS
def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'event_detail.html', {'event': event})

# ✅ ADD THIS (VERY IMPORTANT)
@login_required
def register_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.attendees.add(request.user)
    return redirect('event_detail', id=id)