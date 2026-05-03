from django.contrib import admin
from .models import (
    Trip,
    TripMember,
    Vote,
    VoteOption,
    VoteAnswer,
    Expense,
    TripComment,
    DayPlan
)

admin.site.register(Trip)
admin.site.register(TripMember)
admin.site.register(Vote)
admin.site.register(VoteOption)
admin.site.register(VoteAnswer)
admin.site.register(Expense)
admin.site.register(TripComment)
admin.site.register(DayPlan)