import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Trip, TripMember


class ExcursionE2ETests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='e2e_user', password='password123')
        self.client.login(username='e2e_user', password='password123')

        # Создаем первую поездку, чтобы тестовый маршрут был с id=2 (как в ручном сценарии).
        trip1 = Trip.objects.create(
            title='Trip 1',
            description='First trip',
            destination='Москва',
            start_date=datetime.date(2026, 5, 10),
            end_date=datetime.date(2026, 5, 12),
            budget=10000,
            owner=self.user,
        )
        TripMember.objects.create(trip=trip1, user=self.user, role='owner')

        self.trip = Trip.objects.create(
            title='Trip 2',
            description='Second trip',
            destination='Санкт-Петербург',
            start_date=datetime.date(2026, 6, 10),
            end_date=datetime.date(2026, 6, 12),
            budget=15000,
            owner=self.user,
        )
        TripMember.objects.create(trip=self.trip, user=self.user, role='owner')

    @patch('trips.views._get_gigachat_token', return_value='fake-token')
    @patch('trips.views._geocode_place', return_value=None)
    @patch('trips.views._ask_gigachat')
    def test_build_route_post_renders_places_for_map(self, mock_ask_gigachat, _mock_geocode, _mock_get_token):
        mock_ask_gigachat.return_value = (
            '{'
            '"route_text":"1. Эрмитаж — крупнейший музей города.\\n'
            '2. Исаакиевский собор — одна из архитектурных доминант.",'
            '"places":['
            '"Санкт-Петербург, Эрмитаж, Дворцовая площадь, 2",'
            '"Санкт-Петербург, Исаакиевский собор, Исаакиевская площадь, 4"'
            ']'
            '}'
        )

        url = reverse('excursion', args=[self.trip.id])
        response = self.client.post(url, data={
            'city': 'Санкт-Петербург',
            'duration': '3',
            'interests': 'музеи, история',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Маршрут от GigaChat')
        self.assertContains(response, 'Эрмитаж')
        self.assertContains(response, 'Исаакиевский собор')
        self.assertContains(response, 'const placesData =')
        self.assertContains(response, 'Санкт-Петербург, Эрмитаж, Дворцовая площадь, 2')
        self.assertContains(response, 'Санкт-Петербург, Исаакиевский собор, Исаакиевская площадь, 4')

    def test_excursion_page_get_loads(self):
        url = reverse('excursion', args=[self.trip.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ИИ-экскурсия')
        self.assertContains(response, 'Построить маршрут')
