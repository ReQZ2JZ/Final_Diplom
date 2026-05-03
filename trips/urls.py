from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_page, name='settings'),
    path('statistics/', views.statistics, name='statistics'),

    path('trip/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('create/', views.create_trip, name='create_trip'),
    path('trip/<int:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('trip/<int:trip_id>/delete/', views.delete_trip, name='delete_trip'),

    path('trip/<int:trip_id>/add-member/', views.add_member, name='add_member'),
    path('trip/<int:trip_id>/create-vote/', views.create_vote, name='create_vote'),
    path('vote/<int:vote_id>/', views.vote_detail, name='vote_detail'),
    path('vote/<int:vote_id>/submit/', views.submit_vote, name='submit_vote'),

    path('trip/<int:trip_id>/create-expense/', views.create_expense, name='create_expense'),
    path('expense/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),

    path('trip/<int:trip_id>/add-comment/', views.add_comment, name='add_comment'),
    path('trip/<int:trip_id>/add-day-plan/', views.add_day_plan, name='add_day_plan'),

    path('trip/<int:trip_id>/pdf/', views.trip_pdf_report, name='trip_pdf_report'),
    path('trip/<int:trip_id>/excursion/', views.excursion, name='excursion'),
    path('api/geocode-place/', views.geocode_place_api, name='geocode_place_api'),
]