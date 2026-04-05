from django.contrib import admin
from .models import Event, WaitlistEntry, Team


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'date',
        'capacity_limited',
        'capacity',
        'waitlist_enabled',
        'is_team_event',
    )
    list_filter = ('category', 'capacity_limited', 'waitlist_enabled', 'is_team_event')
    search_fields = ('title', 'description')


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'created_at')
    list_filter = ('event',)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'leader', 'join_code', 'is_submitted', 'created_at')
    list_filter = ('event', 'is_submitted')
    search_fields = ('name', 'join_code', 'leader__username')
