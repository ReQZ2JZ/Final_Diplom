from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from .models import Trip, Vote, Expense, TripComment


def notifications_count(request):
    if not request.user.is_authenticated:
        return {"notifications_count": 0}

    user_trips = Trip.objects.filter(
        Q(owner=request.user) | Q(tripmember__user=request.user)
    ).distinct()

    last_view = request.session.get('last_notifications_view')

    if last_view:
        last_view = datetime.fromisoformat(last_view)
    else:
        last_view = timezone.now()

    votes = Vote.objects.filter(trip__in=user_trips, created_at__gt=last_view)
    expenses = Expense.objects.filter(trip__in=user_trips, created_at__gt=last_view)
    comments = TripComment.objects.filter(trip__in=user_trips, created_at__gt=last_view)

    count = votes.count() + expenses.count() + comments.count()

    return {
        "notifications_count": count
    }