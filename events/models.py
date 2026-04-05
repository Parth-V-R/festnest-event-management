from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    CATEGORY_CHOICES = [
        ('cultural', 'Cultural'),
        ('technical', 'Technical'),
        ('sports', 'Sports'),
        ('nss', 'NSS'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField()
    description = models.TextField()
    capacity = models.PositiveIntegerField(default=100)
    waitlist_enabled = models.BooleanField(default=True)

    attendees = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.title

    @property
    def seats_left(self):
        return max(self.capacity - self.attendees.count(), 0)


class WaitlistEntry(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='waitlist_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_waitlist_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} - {self.event.title}'
