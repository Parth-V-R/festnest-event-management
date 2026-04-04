from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


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
