from django.db import models
from django.contrib.auth.models import User


class Trip(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    destination = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.IntegerField(default=0)
    image_url = models.URLField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TripMember(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('member', 'Member'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')

    def __str__(self):
        return f"{self.user.username} — {self.trip.title}"


class Vote(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='votes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class VoteOption(models.Model):
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, related_name='options')
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class VoteAnswer(models.Model):
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, related_name='answers')
    option = models.ForeignKey(VoteOption, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vote', 'user')

    def __str__(self):
        return f"{self.user.username} — {self.option.title}"


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('housing', 'Проживание'),
        ('transport', 'Транспорт'),
        ('food', 'Еда'),
        ('entertainment', 'Развлечения'),
        ('other', 'Другое'),
    ]

    EXPENSE_TYPE_CHOICES = [
        ('shared', 'Общий расход'),
        ('personal', 'Личный расход'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=255)
    amount = models.IntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES, default='shared')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.amount} ₽"


class TripComment(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:30]}"


class DayPlan(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='day_plans')
    day_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"День {self.day_number}: {self.title}"