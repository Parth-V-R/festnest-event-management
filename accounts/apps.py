from django.apps import AppConfig
import os


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        bootstrap_enabled = os.getenv('DJANGO_BOOTSTRAP_ADMIN', 'false').lower() in (
            '1',
            'true',
            'yes',
            'on',
        )
        if not bootstrap_enabled:
            return

        username = os.getenv('DJANGO_BOOTSTRAP_ADMIN_USERNAME', '').strip()
        email = os.getenv('DJANGO_BOOTSTRAP_ADMIN_EMAIL', '').strip()
        password = os.getenv('DJANGO_BOOTSTRAP_ADMIN_PASSWORD', '')
        if not username or not password:
            return

        try:
            from django.contrib.auth import get_user_model
            from django.db.utils import OperationalError, ProgrammingError

            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': True,
                    'is_superuser': True,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
                return

            updated_fields = []
            if email and user.email != email:
                user.email = email
                updated_fields.append('email')
            if not user.is_staff:
                user.is_staff = True
                updated_fields.append('is_staff')
            if not user.is_superuser:
                user.is_superuser = True
                updated_fields.append('is_superuser')
            if updated_fields:
                user.save(update_fields=updated_fields)
        except (OperationalError, ProgrammingError):
            # Database/table may not be ready during startup of management commands.
            return
