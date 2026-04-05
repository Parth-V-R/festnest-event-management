from django.contrib import admin
from .models import Event, WaitlistEntry


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date', 'capacity', 'waitlist_enabled')
    list_filter = ('category', 'waitlist_enabled')
    search_fields = ('title', 'description')


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'created_at')
    list_filter = ('event',)
