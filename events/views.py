from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, WaitlistEntry
from .forms import EventForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone


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
    events = Event.objects.filter(category=category).order_by('date')
    return render(request, 'category.html', {
        'events': events,
        'category': category
    })


def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    is_registered = False
    is_waitlisted = False
    if request.user.is_authenticated:
        is_registered = event.attendees.filter(pk=request.user.pk).exists()
        is_waitlisted = WaitlistEntry.objects.filter(event=event, user=request.user).exists()

    return render(
        request,
        'event_detail.html',
        {
            'event': event,
            'is_registered': is_registered,
            'is_waitlisted': is_waitlisted,
            'waitlist_count': event.waitlist_entries.count(),
            'is_full': event.seats_left == 0,
        },
    )


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def manage_events(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'manage_events.html', {'events': events})


@login_required
@user_passes_test(is_superuser)
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
@user_passes_test(is_superuser)
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
@user_passes_test(is_superuser)
@require_POST
def delete_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.delete()
    messages.success(request, 'Event deleted successfully.')
    return redirect('manage_events')


@login_required
def my_registrations(request):
    registered_events = Event.objects.filter(attendees=request.user).order_by('date')
    waitlisted_entries = (
        WaitlistEntry.objects
        .filter(user=request.user)
        .select_related('event')
        .order_by('event__date', 'created_at')
    )
    return render(
        request,
        'my_registrations.html',
        {'events': registered_events, 'waitlisted_entries': waitlisted_entries},
    )


@login_required
@require_POST
def register_event(request, id):
    event = get_object_or_404(Event, id=id)
    if event.date < timezone.localdate():
        messages.error(request, 'Registration is closed for past events.')
        return redirect('event_detail', id=id)

    if event.attendees.filter(pk=request.user.pk).exists():
        messages.info(request, 'You are already registered for this event.')
    elif WaitlistEntry.objects.filter(event=event, user=request.user).exists():
        messages.info(request, 'You are already on the waitlist for this event.')
    else:
        if event.seats_left > 0:
            event.attendees.add(request.user)
            messages.success(request, 'Registration successful.')
        elif event.waitlist_enabled:
            WaitlistEntry.objects.create(event=event, user=request.user)
            messages.info(request, 'Event is full. You have been added to the waitlist.')
        else:
            messages.error(request, 'Event is full and waitlist is disabled.')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def unregister_event(request, id):
    event = get_object_or_404(Event, id=id)
    was_registered = event.attendees.filter(pk=request.user.pk).exists()
    if was_registered:
        event.attendees.remove(request.user)
        messages.success(request, 'You have been removed from this event.')

        promoted = event.waitlist_entries.select_related('user').first()
        if promoted:
            event.attendees.add(promoted.user)
            promoted.delete()
            messages.info(request, 'A waitlisted participant has been promoted.')
    elif WaitlistEntry.objects.filter(event=event, user=request.user).exists():
        WaitlistEntry.objects.filter(event=event, user=request.user).delete()
        messages.success(request, 'You have been removed from the waitlist.')
    else:
        messages.info(request, 'You are not registered for this event.')

    return redirect('my_registrations')
