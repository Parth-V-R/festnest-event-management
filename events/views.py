from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import Event, WaitlistEntry, Team
from .forms import EventForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.contrib.auth.models import User
import csv


def build_team_state(user, events_qs=None):
    if not user.is_authenticated:
        return {}, set(), set()

    team_qs = Team.objects.filter(members=user).select_related('leader')
    if events_qs is not None:
        team_qs = team_qs.filter(event__in=events_qs)

    team_map = {team.event_id: team for team in team_qs}
    team_event_ids = set(team_map.keys())
    submitted_team_event_ids = {event_id for event_id, team in team_map.items() if team.is_submitted}
    return team_map, team_event_ids, submitted_team_event_ids


def replace_flash(request, level, text):
    list(messages.get_messages(request))
    messages.add_message(request, level, text)


def _missing_profile_fields_for_enrollment(user):
    missing = []
    profile = getattr(user, 'profile', None)

    if not (user.username or '').strip():
        missing.append('Username')
    if profile is None or not (profile.full_name or '').strip():
        missing.append('Full Name')
    if profile is None or not (profile.roll_no or '').strip():
        missing.append('Roll No')
    if profile is None or not (profile.department or '').strip():
        missing.append('Department')
    if profile is None or not (profile.year_of_study or '').strip():
        missing.append('Year')
    if profile is None or not (profile.section or '').strip():
        missing.append('Section')
    return missing


def _enrollment_profile_gate(request, event_id):
    missing_fields = _missing_profile_fields_for_enrollment(request.user)
    if not missing_fields:
        return None

    replace_flash(
        request,
        messages.ERROR,
        'Complete profile before enrollment. Required fields: '
        + ', '.join(missing_fields)
        + '.',
    )
    next_url = reverse('event_detail', args=[event_id])
    return redirect(f"{reverse('edit_profile')}?next={next_url}")


def home(request):
    today = timezone.localdate()
    search_query = request.GET.get('q', '').strip()
    upcoming_events = Event.objects.filter(date__gte=today).order_by('date')
    searched_events = Event.objects.none()
    result_count = 0
    registered_event_ids = set()
    waitlisted_event_ids = set()
    user_team_event_ids = set()
    submitted_team_event_ids = set()

    if search_query:
        searched_events = upcoming_events.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__icontains=search_query)
        )
        result_count = searched_events.count()

    if request.user.is_authenticated:
        registered_event_ids = set(
            Event.objects.filter(attendees=request.user).values_list('id', flat=True),
        )
        waitlisted_event_ids = set(
            WaitlistEntry.objects.filter(user=request.user).values_list('event_id', flat=True),
        )
        _, user_team_event_ids, submitted_team_event_ids = build_team_state(request.user, upcoming_events)

    return render(
        request,
        'index.html',
        {
            'upcoming_events': upcoming_events,
            'searched_events': searched_events,
            'search_query': search_query,
            'result_count': result_count,
            'registered_event_ids': registered_event_ids,
            'waitlisted_event_ids': waitlisted_event_ids,
            'user_team_event_ids': user_team_event_ids,
            'submitted_team_event_ids': submitted_team_event_ids,
        },
    )


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    today = timezone.localdate()

    suggestions_qs = (
        Event.objects
        .filter(
            (Q(title__icontains=query) | Q(category__icontains=query)),
            date__gte=today,
        )
        .order_by('date')
        .values('title', 'category', 'date')[:8]
    )
    category_map = dict(Event.CATEGORY_CHOICES)
    suggestions = [
        {
            'title': row['title'],
            'category': category_map.get(row['category'], row['category'].title()),
            'date': row['date'].strftime('%b %d, %Y'),
        }
        for row in suggestions_qs
    ]
    return JsonResponse({'suggestions': suggestions})


def category_events(request, category):
    today = timezone.localdate()
    events = Event.objects.filter(category=category, date__gte=today).order_by('date')
    category_titles = {
        'cultural': 'Cultural Events',
        'technical': 'Technical Events',
        'sports': 'Sports',
        'nss': 'NSS',
        'other': 'Other',
    }
    category_label = category_titles.get(category, category.title())
    registered_event_ids = set()
    waitlisted_event_ids = set()
    user_team_event_ids = set()
    submitted_team_event_ids = set()
    if request.user.is_authenticated:
        registered_event_ids = set(
            Event.objects.filter(attendees=request.user).values_list('id', flat=True),
        )
        waitlisted_event_ids = set(
            WaitlistEntry.objects.filter(user=request.user).values_list('event_id', flat=True),
        )
        _, user_team_event_ids, submitted_team_event_ids = build_team_state(request.user, events)
    return render(request, 'category.html', {
        'events': events,
        'category': category,
        'category_label': category_label,
        'registered_event_ids': registered_event_ids,
        'waitlisted_event_ids': waitlisted_event_ids,
        'user_team_event_ids': user_team_event_ids,
        'submitted_team_event_ids': submitted_team_event_ids,
        'today': today,
    })


def event_detail(request, id):
    today = timezone.localdate()
    event = get_object_or_404(Event, id=id)
    is_registered = False
    is_waitlisted = False
    user_team = None
    is_team_leader = False
    if request.user.is_authenticated:
        is_registered = event.attendees.filter(pk=request.user.pk).exists()
        is_waitlisted = WaitlistEntry.objects.filter(event=event, user=request.user).exists()
        if event.is_team_event:
            user_team = (
                Team.objects
                .filter(event=event, members=request.user)
                .select_related('leader')
                .prefetch_related('members')
                .first()
            )
            is_team_leader = bool(user_team and user_team.leader_id == request.user.id)

    return render(
        request,
        'event_detail.html',
        {
            'event': event,
            'is_registered': is_registered,
            'is_waitlisted': is_waitlisted,
            'waitlist_count': event.waitlist_entries.count(),
            'is_full': event.is_full,
            'is_past': event.date < today,
            'user_team': user_team,
            'is_team_leader': is_team_leader,
            'submitted_team_count': event.teams.filter(is_submitted=True).count(),
        },
    )


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def manage_events(request):
    events_qs = (
        Event.objects
        .all()
        .prefetch_related(
            Prefetch(
                'attendees',
                queryset=User.objects.select_related('profile').order_by('username'),
            ),
            Prefetch(
                'teams',
                queryset=(
                    Team.objects
                    .select_related('leader', 'leader__profile')
                    .prefetch_related(
                        Prefetch(
                            'members',
                            queryset=User.objects.select_related('profile').order_by('username'),
                        ),
                    )
                    .order_by('name')
                ),
            ),
        )
        .order_by('date')
    )
    events = list(events_qs)
    for event in events:
        event.submitted_team_count = sum(1 for team in event.teams.all() if team.is_submitted)
        for attendee in event.attendees.all():
            attendee.admin_profile = getattr(attendee, 'profile', None)
        for team in event.teams.all():
            team.leader.admin_profile = getattr(team.leader, 'profile', None)
            for member in team.members.all():
                member.admin_profile = getattr(member, 'profile', None)
    return render(request, 'manage_events.html', {'events': events})


@login_required
@user_passes_test(is_superuser)
def export_event_registrations_csv(request, id):
    event = (
        Event.objects
        .filter(id=id)
        .prefetch_related(
            Prefetch(
                'attendees',
                queryset=User.objects.select_related('profile').order_by('username'),
            ),
            Prefetch(
                'teams',
                queryset=(
                    Team.objects
                    .select_related('leader', 'leader__profile')
                    .prefetch_related(
                        Prefetch(
                            'members',
                            queryset=User.objects.select_related('profile').order_by('username'),
                        ),
                    )
                    .order_by('name')
                ),
            ),
        )
        .first()
    )
    if not event:
        return redirect('manage_events')

    response = HttpResponse(content_type='text/csv')
    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in event.title).strip('_') or f'event_{event.id}'
    response['Content-Disposition'] = f'attachment; filename="{safe_title}_registrations.csv"'
    writer = csv.writer(response)
    _write_registration_csv(writer, [event])
    return response


@login_required
@user_passes_test(is_superuser)
def export_all_registrations_csv(request):
    events = (
        Event.objects
        .all()
        .prefetch_related(
            Prefetch(
                'attendees',
                queryset=User.objects.select_related('profile').order_by('username'),
            ),
            Prefetch(
                'teams',
                queryset=(
                    Team.objects
                    .select_related('leader', 'leader__profile')
                    .prefetch_related(
                        Prefetch(
                            'members',
                            queryset=User.objects.select_related('profile').order_by('username'),
                        ),
                    )
                    .order_by('name')
                ),
            ),
        )
        .order_by('date', 'title')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_events_registrations.csv"'
    writer = csv.writer(response)
    _write_registration_csv(writer, events)
    return response


def _write_registration_csv(writer, events):
    writer.writerow(
        [
            'Event ID',
            'Event Title',
            'Category',
            'Event Date',
            'Event Type',
            'Team Name',
            'Team Status',
            'User Role',
            'Username',
            'Full Name',
            'Email',
            'Phone',
            'Roll No',
            'Section',
            'Department',
            'Year',
        ],
    )

    def profile_value(user_obj, field_name):
        profile = getattr(user_obj, 'profile', None)
        if not profile:
            return ''
        return getattr(profile, field_name, '') or ''

    for event in events:
        event_type = 'Team Event' if event.is_team_event else 'Individual Event'

        if event.is_team_event:
            for team in event.teams.all():
                team_status = 'Submitted' if team.is_submitted else 'In Progress'
                for member in team.members.all():
                    role = 'Leader' if member.id == team.leader_id else 'Member'
                    writer.writerow(
                        [
                            event.id,
                            event.title,
                            event.get_category_display(),
                            event.date,
                            event_type,
                            team.name,
                            team_status,
                            role,
                            member.username,
                            profile_value(member, 'full_name'),
                            member.email or '',
                            profile_value(member, 'phone'),
                            profile_value(member, 'roll_no'),
                            profile_value(member, 'section'),
                            profile_value(member, 'department'),
                            profile_value(member, 'year_of_study'),
                        ],
                    )
        else:
            for attendee in event.attendees.all():
                writer.writerow(
                    [
                        event.id,
                        event.title,
                        event.get_category_display(),
                        event.date,
                        event_type,
                        '',
                        '',
                        'Attendee',
                        attendee.username,
                        profile_value(attendee, 'full_name'),
                        attendee.email or '',
                        profile_value(attendee, 'phone'),
                        profile_value(attendee, 'roll_no'),
                        profile_value(attendee, 'section'),
                        profile_value(attendee, 'department'),
                        profile_value(attendee, 'year_of_study'),
                    ],
                )


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
    today = timezone.localdate()
    registered_events = Event.objects.filter(attendees=request.user).order_by('date')
    active_registered_events = registered_events.filter(date__gte=today)
    past_registered_events = registered_events.filter(date__lt=today)
    waitlisted_entries = (
        WaitlistEntry.objects
        .filter(user=request.user, event__date__gte=today)
        .select_related('event')
        .order_by('event__date', 'created_at')
    )
    team_registrations = (
        Team.objects
        .filter(members=request.user, is_submitted=True)
        .select_related('event', 'leader')
        .prefetch_related('members')
        .order_by('event__date')
    )
    active_team_registrations = [team for team in team_registrations if team.event.date >= today]
    past_team_registrations = [team for team in team_registrations if team.event.date < today]
    active_teams_in_progress = (
        Team.objects
        .filter(members=request.user, is_submitted=False, event__date__gte=today)
        .select_related('event', 'leader')
        .prefetch_related('members')
        .order_by('event__date', 'created_at')
    )
    return render(
        request,
        'my_registrations.html',
        {
            'active_events': active_registered_events,
            'past_events': past_registered_events,
            'waitlisted_entries': waitlisted_entries,
            'active_team_registrations': active_team_registrations,
            'past_team_registrations': past_team_registrations,
            'active_teams_in_progress': active_teams_in_progress,
        },
    )


@login_required
@require_POST
def register_event(request, id):
    event = get_object_or_404(Event, id=id)
    gate_response = _enrollment_profile_gate(request, id)
    if gate_response:
        return gate_response

    if event.is_team_event:
        replace_flash(
            request,
            messages.INFO,
            'This is a team event. Please create or join a team from event details.',
        )
        return redirect('event_detail', id=id)

    if event.date < timezone.localdate():
        replace_flash(request, messages.ERROR, 'Registration is closed for past events.')
        return redirect('event_detail', id=id)

    if event.attendees.filter(pk=request.user.pk).exists():
        replace_flash(request, messages.INFO, 'You are already registered for this event.')
    elif WaitlistEntry.objects.filter(event=event, user=request.user).exists():
        replace_flash(request, messages.INFO, 'You are already on the waitlist for this event.')
    else:
        if not event.capacity_limited:
            event.attendees.add(request.user)
            replace_flash(request, messages.SUCCESS, 'Enrollment successful.')
        elif event.seats_left > 0:
            event.attendees.add(request.user)
            replace_flash(request, messages.SUCCESS, 'Enrollment successful.')
        elif event.waitlist_enabled:
            WaitlistEntry.objects.create(event=event, user=request.user)
            replace_flash(request, messages.INFO, 'Event is full. You have been added to the waitlist.')
        else:
            replace_flash(request, messages.ERROR, 'Event is full and waitlist is disabled.')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def unregister_event(request, id):
    today = timezone.localdate()
    event = get_object_or_404(Event, id=id)
    if event.is_team_event:
        replace_flash(request, messages.INFO, 'For team events, use team actions from event details.')
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('event_detail', id=id)

    if event.date < today:
        replace_flash(request, messages.INFO, 'Past events are kept as history and cannot be dropped.')
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('my_registrations')

    was_registered = event.attendees.filter(pk=request.user.pk).exists()
    if was_registered:
        event.attendees.remove(request.user)
        message_text = 'You have been removed from this event.'

        promoted = event.waitlist_entries.select_related('user').first()
        if promoted:
            event.attendees.add(promoted.user)
            promoted.delete()
            message_text = 'Dropped successfully. A waitlisted participant has been promoted.'
        replace_flash(request, messages.SUCCESS, message_text)
    elif WaitlistEntry.objects.filter(event=event, user=request.user).exists():
        WaitlistEntry.objects.filter(event=event, user=request.user).delete()
        replace_flash(request, messages.SUCCESS, 'You have been removed from the waitlist.')
    else:
        replace_flash(request, messages.INFO, 'You are not enrolled for this event.')
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect('my_registrations')


@login_required
@require_POST
def create_team(request, id):
    event = get_object_or_404(Event, id=id)
    gate_response = _enrollment_profile_gate(request, id)
    if gate_response:
        return gate_response

    if not event.is_team_event:
        messages.error(request, 'This event does not support team registration.')
        return redirect('event_detail', id=id)
    if event.date < timezone.localdate():
        messages.error(request, 'Team creation is closed for past events.')
        return redirect('event_detail', id=id)

    team_name = request.POST.get('team_name', '').strip()
    if len(team_name) < 3:
        messages.error(request, 'Team name must be at least 3 characters long.')
        return redirect('event_detail', id=id)
    if Team.objects.filter(event=event, members=request.user).exists():
        messages.info(request, 'You are already part of a team for this event.')
        return redirect('event_detail', id=id)
    if Team.objects.filter(event=event, name__iexact=team_name).exists():
        messages.error(request, 'A team with this name already exists for this event.')
        return redirect('event_detail', id=id)

    team = Team.objects.create(event=event, name=team_name, leader=request.user)
    team.members.add(request.user)
    messages.success(request, f'Team created. Share invite code: {team.join_code}')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def join_team(request, id):
    event = get_object_or_404(Event, id=id)
    gate_response = _enrollment_profile_gate(request, id)
    if gate_response:
        return gate_response

    if not event.is_team_event:
        messages.error(request, 'This event does not support team registration.')
        return redirect('event_detail', id=id)
    if event.date < timezone.localdate():
        messages.error(request, 'Joining teams is closed for past events.')
        return redirect('event_detail', id=id)
    if Team.objects.filter(event=event, members=request.user).exists():
        messages.info(request, 'You are already part of a team for this event.')
        return redirect('event_detail', id=id)

    join_code = request.POST.get('join_code', '').strip().upper()
    if not join_code:
        messages.error(request, 'Enter a valid invite code.')
        return redirect('event_detail', id=id)

    team = Team.objects.filter(event=event, join_code=join_code).prefetch_related('members').first()
    if not team:
        messages.error(request, 'No team found with that invite code.')
        return redirect('event_detail', id=id)
    if team.is_submitted:
        messages.info(request, 'This team is already submitted.')
        return redirect('event_detail', id=id)
    if team.member_count >= event.max_team_size:
        messages.error(request, 'This team is already full.')
        return redirect('event_detail', id=id)

    team.members.add(request.user)
    messages.success(request, f'Joined team "{team.name}".')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def leave_team(request, id):
    event = get_object_or_404(Event, id=id)
    team = Team.objects.filter(event=event, members=request.user).prefetch_related('members').first()
    if not team:
        messages.info(request, 'You are not part of a team for this event.')
        return redirect('event_detail', id=id)
    if team.is_submitted:
        messages.info(request, 'Submitted teams cannot be modified.')
        return redirect('event_detail', id=id)

    team.members.remove(request.user)
    remaining_members = list(team.members.all())
    if not remaining_members:
        team.delete()
        messages.success(request, 'Team deleted because it has no remaining members.')
        return redirect('event_detail', id=id)

    if team.leader_id == request.user.id:
        team.leader = remaining_members[0]
        team.save(update_fields=['leader'])
        messages.success(request, 'You left the team. Leadership was transferred.')
    else:
        messages.success(request, 'You left the team.')
    return redirect('event_detail', id=id)


@login_required
@require_POST
def submit_team(request, id):
    event = get_object_or_404(Event, id=id)
    gate_response = _enrollment_profile_gate(request, id)
    if gate_response:
        return gate_response

    if not event.is_team_event:
        messages.error(request, 'This event does not support team registration.')
        return redirect('event_detail', id=id)
    if event.date < timezone.localdate():
        messages.error(request, 'Submission is closed for past events.')
        return redirect('event_detail', id=id)

    team = Team.objects.filter(event=event, leader=request.user).prefetch_related('members').first()
    if not team:
        messages.error(request, 'Only team leaders can submit a team.')
        return redirect('event_detail', id=id)
    if team.is_submitted:
        messages.info(request, 'This team is already submitted.')
        return redirect('event_detail', id=id)

    member_count = team.member_count
    if member_count < event.min_team_size or member_count > event.max_team_size:
        messages.error(
            request,
            f'Team size must be between {event.min_team_size} and {event.max_team_size}.',
        )
        return redirect('event_detail', id=id)

    team.is_submitted = True
    team.save(update_fields=['is_submitted'])
    messages.success(request, 'Team registration submitted successfully.')
    return redirect('event_detail', id=id)
