from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=120, blank=True)
    college = models.CharField(max_length=180, blank=True)
    department = models.CharField(max_length=120, blank=True)
    year_of_study = models.CharField(max_length=20, blank=True)
    section = models.CharField(max_length=20, blank=True)
    roll_no = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    phone_otp_code = models.CharField(max_length=128, blank=True)
    phone_otp_expires_at = models.DateTimeField(blank=True, null=True)
    password_reset_otp_code = models.CharField(max_length=128, blank=True)
    password_reset_otp_expires_at = models.DateTimeField(blank=True, null=True)
    email_reset_otp_code = models.CharField(max_length=128, blank=True)
    email_reset_otp_expires_at = models.DateTimeField(blank=True, null=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f'Profile of {self.user.username}'
