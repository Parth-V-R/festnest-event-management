from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date

from .models import Event


class EventRegistrationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='student1',
            password='safePass123!',
        )
        self.event = Event.objects.create(
            title='Hackathon 2026',
            category='technical',
            date=date(2026, 4, 20),
            description='A 24 hour coding challenge.',
        )

    def test_register_requires_login(self):
        register_url = reverse('register_event', args=[self.event.id])

        response = self.client.post(register_url)

        self.assertRedirects(response, f"{reverse('login')}?next={register_url}")

    def test_register_is_post_only(self):
        self.client.login(username='student1', password='safePass123!')

        response = self.client.get(reverse('register_event', args=[self.event.id]))

        self.assertEqual(response.status_code, 405)

    def test_register_adds_user_once(self):
        self.client.login(username='student1', password='safePass123!')
        register_url = reverse('register_event', args=[self.event.id])

        response_1 = self.client.post(register_url)
        response_2 = self.client.post(register_url)

        self.assertRedirects(response_1, reverse('event_detail', args=[self.event.id]))
        self.assertRedirects(response_2, reverse('event_detail', args=[self.event.id]))
        self.assertEqual(self.event.attendees.filter(pk=self.user.pk).count(), 1)


class EventSearchTests(TestCase):
    def setUp(self):
        Event.objects.create(
            title='Hackathon 2026',
            category='technical',
            date=date(2026, 4, 20),
            description='A 24 hour coding challenge.',
        )
        Event.objects.create(
            title='Classical Dance Night',
            category='cultural',
            date=date(2026, 4, 25),
            description='Inter-college dance performances.',
        )

    def test_home_search_filters_events_by_title(self):
        response = self.client.get(reverse('home'), {'q': 'hack'})

        self.assertEqual(response.status_code, 200)
        searched_titles = [event.title for event in response.context['searched_events']]
        self.assertIn('Hackathon 2026', searched_titles)
        self.assertNotIn('Classical Dance Night', searched_titles)
        self.assertEqual(response.context['result_count'], 1)

    def test_home_search_filters_events_by_category(self):
        response = self.client.get(reverse('home'), {'q': 'cultural'})

        self.assertEqual(response.status_code, 200)
        searched_titles = [event.title for event in response.context['searched_events']]
        self.assertIn('Classical Dance Night', searched_titles)
        self.assertNotIn('Hackathon 2026', searched_titles)
        self.assertEqual(response.context['result_count'], 1)


class MyRegistrationsTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='student2',
            password='safePass123!',
        )
        self.event_registered = Event.objects.create(
            title='Code Relay',
            category='technical',
            date=date(2026, 5, 10),
            description='Team coding relay.',
        )
        self.event_not_registered = Event.objects.create(
            title='Street Play',
            category='cultural',
            date=date(2026, 5, 12),
            description='Drama and stage performance.',
        )
        self.event_registered.attendees.add(self.user)

    def test_my_registrations_requires_login(self):
        response = self.client.get(reverse('my_registrations'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('my_registrations')}",
        )

    def test_my_registrations_shows_only_registered_events(self):
        self.client.login(username='student2', password='safePass123!')
        response = self.client.get(reverse('my_registrations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Code Relay')
        self.assertNotContains(response, 'Street Play')

    def test_unregister_event_removes_registration(self):
        self.client.login(username='student2', password='safePass123!')
        response = self.client.post(
            reverse('unregister_event', args=[self.event_registered.id]),
        )

        self.assertRedirects(response, reverse('my_registrations'))
        self.assertFalse(
            self.event_registered.attendees.filter(pk=self.user.pk).exists(),
        )


class EventManagementAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.student = self.user_model.objects.create_user(
            username='student3',
            password='safePass123!',
        )
        self.staff = self.user_model.objects.create_user(
            username='coordinator1',
            password='safePass123!',
            is_staff=True,
        )
        self.event = Event.objects.create(
            title='Robotics Expo',
            category='technical',
            date=date(2026, 6, 5),
            description='Prototype showcase.',
        )

    def test_manage_events_requires_staff(self):
        self.client.login(username='student3', password='safePass123!')
        response = self.client.get(reverse('manage_events'))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_create_event(self):
        self.client.login(username='coordinator1', password='safePass123!')
        response = self.client.post(
            reverse('create_event'),
            {
                'title': 'Code Sprint',
                'category': 'technical',
                'date': '2026-06-20',
                'description': 'Fast-paced coding competition.',
            },
        )

        self.assertRedirects(response, reverse('manage_events'))
        self.assertTrue(Event.objects.filter(title='Code Sprint').exists())

    def test_staff_can_edit_event(self):
        self.client.login(username='coordinator1', password='safePass123!')
        response = self.client.post(
            reverse('edit_event', args=[self.event.id]),
            {
                'title': 'Robotics Expo Updated',
                'category': 'technical',
                'date': '2026-06-10',
                'description': 'Updated showcase details.',
            },
        )

        self.assertRedirects(response, reverse('manage_events'))
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'Robotics Expo Updated')

    def test_staff_can_delete_event(self):
        self.client.login(username='coordinator1', password='safePass123!')
        response = self.client.post(reverse('delete_event', args=[self.event.id]))

        self.assertRedirects(response, reverse('manage_events'))
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())
