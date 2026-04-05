from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from .models import Event, WaitlistEntry


class EventRegistrationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='student1',
            password='safePass123!',
        )
        self.user2 = self.user_model.objects.create_user(
            username='student1b',
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

    def test_register_blocks_past_event(self):
        past_event = Event.objects.create(
            title='Past Seminar',
            category='technical',
            date=date.today() - timedelta(days=1),
            description='Old event.',
        )
        self.client.login(username='student1', password='safePass123!')

        response = self.client.post(reverse('register_event', args=[past_event.id]))

        self.assertRedirects(response, reverse('event_detail', args=[past_event.id]))
        self.assertFalse(past_event.attendees.filter(pk=self.user.pk).exists())

    def test_register_adds_user_to_waitlist_when_event_full(self):
        full_event = Event.objects.create(
            title='Full Event',
            category='technical',
            date=date(2026, 4, 22),
            description='Already full.',
            capacity=1,
            waitlist_enabled=True,
        )
        full_event.attendees.add(self.user)
        self.client.login(username='student1b', password='safePass123!')

        response = self.client.post(reverse('register_event', args=[full_event.id]))

        self.assertRedirects(response, reverse('event_detail', args=[full_event.id]))
        self.assertTrue(WaitlistEntry.objects.filter(event=full_event, user=self.user2).exists())

    def test_unregister_promotes_waitlisted_user(self):
        full_event = Event.objects.create(
            title='Waitlist Promotion Event',
            category='technical',
            date=date(2026, 4, 23),
            description='Promotion test.',
            capacity=1,
            waitlist_enabled=True,
        )
        full_event.attendees.add(self.user)
        WaitlistEntry.objects.create(event=full_event, user=self.user2)
        self.client.login(username='student1', password='safePass123!')

        response = self.client.post(reverse('unregister_event', args=[full_event.id]))

        self.assertRedirects(response, reverse('my_registrations'))
        self.assertFalse(full_event.attendees.filter(pk=self.user.pk).exists())
        self.assertTrue(full_event.attendees.filter(pk=self.user2.pk).exists())
        self.assertFalse(WaitlistEntry.objects.filter(event=full_event, user=self.user2).exists())


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

    def test_unregister_requires_login(self):
        unregister_url = reverse('unregister_event', args=[self.event_registered.id])

        response = self.client.post(unregister_url)

        self.assertRedirects(response, f"{reverse('login')}?next={unregister_url}")

    def test_unregister_is_post_only(self):
        self.client.login(username='student2', password='safePass123!')

        response = self.client.get(reverse('unregister_event', args=[self.event_registered.id]))

        self.assertEqual(response.status_code, 405)


class EventManagementTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.superuser = self.user_model.objects.create_superuser(
            username='admin1',
            email='admin@example.com',
            password='safePass123!',
        )
        self.student = self.user_model.objects.create_user(
            username='student3',
            password='safePass123!',
        )
        self.event = Event.objects.create(
            title='Admin Managed Event',
            category='technical',
            date=date(2026, 6, 10),
            description='Managed by admin.',
        )

    def test_manage_events_requires_superuser(self):
        self.client.login(username='student3', password='safePass123!')
        response = self.client.get(reverse('manage_events'))
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_create_edit_delete_event(self):
        self.client.login(username='admin1', password='safePass123!')

        create_response = self.client.post(
            reverse('create_event'),
            {
                'title': 'New Admin Event',
                'category': 'sports',
                'date': '2026-06-20',
                'description': 'Created by admin.',
                'capacity': 150,
                'waitlist_enabled': True,
            },
        )
        self.assertRedirects(create_response, reverse('manage_events'))
        created = Event.objects.get(title='New Admin Event')
        self.assertEqual(created.capacity, 150)

        edit_response = self.client.post(
            reverse('edit_event', args=[created.id]),
            {
                'title': 'Updated Admin Event',
                'category': 'sports',
                'date': '2026-06-21',
                'description': 'Updated by admin.',
                'capacity': 80,
                'waitlist_enabled': False,
            },
        )
        self.assertRedirects(edit_response, reverse('manage_events'))
        created.refresh_from_db()
        self.assertEqual(created.title, 'Updated Admin Event')
        self.assertEqual(created.capacity, 80)
        self.assertFalse(created.waitlist_enabled)

        delete_response = self.client.post(reverse('delete_event', args=[created.id]))
        self.assertRedirects(delete_response, reverse('manage_events'))
        self.assertFalse(Event.objects.filter(id=created.id).exists())
