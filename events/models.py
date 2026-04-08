from django.db import models
from django.contrib.auth.models import User
import secrets
import string


class Event(models.Model):
    CATEGORY_CHOICES = [
        ('cultural', 'Cultural'),
        ('technical', 'Technical'),
        ('sports', 'Sports'),
        ('nss', 'NSS'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    capacity_limited = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=100)
    waitlist_enabled = models.BooleanField(default=True)
    is_team_event = models.BooleanField(default=False)
    min_team_size = models.PositiveIntegerField(default=1)
    max_team_size = models.PositiveIntegerField(default=4)

    attendees = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.title

    @property
    def seats_left(self):
        if not self.capacity_limited:
            return None
        return max(self.capacity - self.attendees.count(), 0)

    @property
    def is_full(self):
        return self.capacity_limited and self.seats_left == 0


class WaitlistEntry(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='waitlist_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_waitlist_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} - {self.event.title}'


class Team(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=120)
    leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='led_teams')
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    join_code = models.CharField(max_length=8, unique=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'name')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} ({self.event.title})'

    @property
    def member_count(self):
        return self.members.count()

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self.generate_join_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_join_code(length=6):
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not Team.objects.filter(join_code=code).exists():
                return code
