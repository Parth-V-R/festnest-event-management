from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from .models import Profile


class AccountsViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_signup_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse('signup'),
            {'username': 'alice', 'password': 'safePass123!'},
        )

        self.assertRedirects(response, reverse('login'))
        self.assertTrue(self.user_model.objects.filter(username='alice').exists())

    def test_signup_duplicate_username_redirects_back(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')

        response = self.client.post(
            reverse('signup'),
            {'username': 'alice', 'password': 'otherPass123!'},
        )

        self.assertRedirects(response, reverse('signup'))
    
    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            reverse('signup'),
            {'username': 'bob', 'password': '123'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user_model.objects.filter(username='bob').exists())

    def test_login_with_invalid_credentials_shows_error(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')

        response = self.client.post(
            reverse('login'),
            {'username': 'alice', 'password': 'wrong-password'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_page_renders_for_logged_in_user(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Profile')
        self.assertTrue(Profile.objects.filter(user__username='alice').exists())

    def test_edit_profile_updates_section_roll_and_email(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(
            reverse('edit_profile'),
            {
                'username': 'alice_new',
                'full_name': 'Alice R',
                'email': 'alice@example.com',
                'college': 'FestNest College',
                'department': 'CSE',
                'year_of_study': '2nd Year',
                'section': 'B',
                'roll_no': '23CS211',
                'phone': '9999999999',
                'bio': 'Event enthusiast',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        user.refresh_from_db()
        profile = Profile.objects.get(user=user)
        self.assertEqual(user.username, 'alice_new')
        self.assertEqual(user.email, 'alice@example.com')
        self.assertEqual(profile.section, 'B')
        self.assertEqual(profile.roll_no, '23CS211')

    def test_request_email_verification_requires_email(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.get(reverse('request_email_verification'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add an Email ID first to verify it.')

    def test_confirm_email_verification_marks_verified(self):
        user = self.user_model.objects.create_user(
            username='alice',
            password='safePass123!',
            email='alice@example.com',
        )
        profile = Profile.objects.create(user=user)
        self.client.login(username='alice', password='safePass123!')
        user.refresh_from_db()

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(reverse('confirm_email_verification', args=[uidb64, token]))

        self.assertRedirects(response, reverse('profile'))
        profile.refresh_from_db()
        self.assertTrue(profile.email_verified)

    def test_request_phone_verification_requires_phone(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(reverse('request_phone_verification'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add a mobile number first to verify it.')

    def test_request_phone_verification_sets_otp(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        profile = Profile.objects.create(user=user, phone='9999999999')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(reverse('request_phone_verification'))

        self.assertRedirects(response, reverse('profile'))
        profile.refresh_from_db()
        self.assertTrue(bool(profile.phone_otp_code))
        self.assertIsNotNone(profile.phone_otp_expires_at)

    def test_verify_phone_otp_marks_verified(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        profile = Profile.objects.create(
            user=user,
            phone='9999999999',
            phone_otp_code=make_password('123456'),
            phone_otp_expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(reverse('verify_phone_otp'), {'otp': '123456'})

        self.assertRedirects(response, reverse('profile'))
        profile.refresh_from_db()
        self.assertTrue(profile.phone_verified)

    def test_verify_phone_otp_rejects_expired_code(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        Profile.objects.create(
            user=user,
            phone='9999999999',
            phone_otp_code=make_password('123456'),
            phone_otp_expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(reverse('verify_phone_otp'), {'otp': '123456'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OTP expired. Request a new OTP.')

    def test_edit_profile_changing_phone_resets_phone_verified(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        profile = Profile.objects.create(user=user, phone='9999999999', phone_verified=True)
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(
            reverse('edit_profile'),
            {
                'username': 'alice',
                'full_name': '',
                'email': '',
                'college': '',
                'department': '',
                'year_of_study': '',
                'section': '',
                'roll_no': '',
                'phone': '8888888888',
                'bio': '',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '8888888888')
        self.assertFalse(profile.phone_verified)

    def test_change_password_requires_login(self):
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 302)

    def test_change_password_updates_user_password(self):
        self.user_model.objects.create_user(username='alice', password='safePass123!')
        self.client.login(username='alice', password='safePass123!')

        response = self.client.post(
            reverse('change_password'),
            {
                'old_password': 'safePass123!',
                'new_password1': 'NewSafePass123!',
                'new_password2': 'NewSafePass123!',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        self.client.logout()
        login_ok = self.client.login(username='alice', password='NewSafePass123!')
        self.assertTrue(login_ok)

    def test_forgot_password_options_page_loads(self):
        response = self.client.get(reverse('forgot_password_options'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Password')

    def test_mobile_forgot_password_sends_otp_for_verified_phone(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        profile = Profile.objects.create(user=user, phone='9999999999', phone_verified=True)

        response = self.client.post(reverse('forgot_password_mobile'), {'identifier': 'alice'})

        self.assertRedirects(response, reverse('forgot_password_mobile_verify'))
        profile.refresh_from_db()
        self.assertTrue(bool(profile.password_reset_otp_code))
        self.assertIsNotNone(profile.password_reset_otp_expires_at)

    def test_mobile_forgot_password_verify_resets_password(self):
        user = self.user_model.objects.create_user(username='alice', password='safePass123!')
        profile = Profile.objects.create(
            user=user,
            phone='9999999999',
            phone_verified=True,
            password_reset_otp_code=make_password('222333'),
            password_reset_otp_expires_at=timezone.now() + timedelta(minutes=10),
        )
        session = self.client.session
        session['password_reset_mobile_user_id'] = user.id
        session.save()

        response = self.client.post(
            reverse('forgot_password_mobile_verify'),
            {
                'otp': '222333',
                'new_password1': 'BrandNewPass123!',
                'new_password2': 'BrandNewPass123!',
            },
        )

        self.assertRedirects(response, reverse('login'))
        profile.refresh_from_db()
        self.assertFalse(bool(profile.password_reset_otp_code))
        self.assertIsNone(profile.password_reset_otp_expires_at)
        self.assertTrue(self.client.login(username='alice', password='BrandNewPass123!'))

    def test_email_forgot_password_sends_otp(self):
        user = self.user_model.objects.create_user(
            username='alice',
            password='safePass123!',
            email='alice@example.com',
        )
        profile = Profile.objects.create(user=user)

        response = self.client.post(reverse('forgot_password_email'), {'identifier': 'alice'})

        self.assertRedirects(response, reverse('forgot_password_email_verify'))
        profile.refresh_from_db()
        self.assertTrue(bool(profile.email_reset_otp_code))
        self.assertIsNotNone(profile.email_reset_otp_expires_at)

    def test_email_forgot_password_verify_resets_password(self):
        user = self.user_model.objects.create_user(
            username='alice',
            password='safePass123!',
            email='alice@example.com',
        )
        profile = Profile.objects.create(
            user=user,
            email_reset_otp_code=make_password('111222'),
            email_reset_otp_expires_at=timezone.now() + timedelta(minutes=10),
        )
        session = self.client.session
        session['password_reset_email_user_id'] = user.id
        session.save()

        response = self.client.post(
            reverse('forgot_password_email_verify'),
            {
                'otp': '111222',
                'new_password1': 'AnotherNewPass123!',
                'new_password2': 'AnotherNewPass123!',
            },
        )

        self.assertRedirects(response, reverse('login'))
        profile.refresh_from_db()
        self.assertFalse(bool(profile.email_reset_otp_code))
        self.assertIsNone(profile.email_reset_otp_expires_at)
        self.assertTrue(self.client.login(username='alice', password='AnotherNewPass123!'))

    def test_logged_in_email_reset_redirects_to_profile(self):
        user = self.user_model.objects.create_user(
            username='alice',
            password='safePass123!',
            email='alice@example.com',
        )
        Profile.objects.create(
            user=user,
            email_reset_otp_code=make_password('333444'),
            email_reset_otp_expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.client.login(username='alice', password='safePass123!')
        session = self.client.session
        session['password_reset_email_user_id'] = user.id
        session.save()

        response = self.client.post(
            reverse('forgot_password_email_verify'),
            {
                'otp': '333444',
                'new_password1': 'LatestPass123!',
                'new_password2': 'LatestPass123!',
            },
        )

        self.assertRedirects(response, reverse('profile'))
