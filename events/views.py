from django.shortcuts import render, get_object_or_404, redirect
from .models import Event
from .forms import EventForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q


def home(request):
    search_query = request.GET.get('q', '').strip()
    upcoming_events = Event.objects.all().order_by('date')
    searched_events = Event.objects.none()
    result_count = 0

    if search_query:
        searched_events = upcoming_events.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__icontains=search_query)
        )
        result_count = searched_events.count()

    return render(
        request,
        'index.html',
        {
            'upcoming_events': upcoming_events,
            'searched_events': searched_events,
            'search_query': search_query,
            'result_count': result_count,
        },
    )

def category_events(request, category):
    events = Event.objects.filter(category=category)
    return render(request, 'category.html', {
        'events': events,
        'category': category
    })

def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    is_registered = False
    if request.user.is_authenticated:
        is_registered = event.attendees.filter(pk=request.user.pk).exists()

    return render(
        request,
        'event_detail.html',
        {'event': event, 'is_registered': is_registered},
    )


def is_staff_user(user):
    return user.is_staff


@login_required
def my_registrations(request):
    events = Event.objects.filter(attendees=request.user).order_by('date')
    return render(request, 'my_registrations.html', {'events': events})


@login_required
@require_POST
def register_event(request, id):
    event = get_object_or_404(Event, id=id)
    if event.attendees.filter(pk=request.user.pk).exists():
        messages.info(request, 'You are already registered for this event.')
    else:
        event.attendees.add(request.user)
        messages.success(request, 'Registration successful.')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def unregister_event(request, id):
    event = get_object_or_404(Event, id=id)
    if event.attendees.filter(pk=request.user.pk).exists():
        event.attendees.remove(request.user)
        messages.success(request, 'You have been removed from this event.')
    else:
        messages.info(request, 'You are not registered for this event.')

    return redirect('my_registrations')


@login_required
@user_passes_test(is_staff_user)
def manage_events(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'manage_events.html', {'events': events})


@login_required
@user_passes_test(is_staff_user)
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created successfully.')
            return redirect('manage_events')
    else:
        form = EventForm()

    return render(
        request,
        'event_form.html',
        {'form': form, 'page_title': 'Create Event', 'button_label': 'Create Event'},
    )


@login_required
@user_passes_test(is_staff_user)
def edit_event(request, id):
    event = get_object_or_404(Event, id=id)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            return redirect('manage_events')
    else:
        form = EventForm(instance=event)

    return render(
        request,
        'event_form.html',
        {'form': form, 'page_title': 'Edit Event', 'button_label': 'Update Event'},
    )


@login_required
@user_passes_test(is_staff_user)
@require_POST
def delete_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.delete()
    messages.success(request, 'Event deleted successfully.')
    return redirect('manage_events')
