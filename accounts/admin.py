from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'full_name',
        'department',
        'section',
        'roll_no',
        'email_verified',
        'phone_verified',
    )
    search_fields = ('user__username', 'full_name', 'roll_no')
