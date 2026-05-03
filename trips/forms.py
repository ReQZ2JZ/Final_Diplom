from django import forms
from django.contrib.auth.models import User
from .models import Trip, Vote, Expense, TripComment, DayPlan


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['title', 'description', 'destination', 'start_date', 'end_date', 'budget', 'image_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: https://images.unsplash.com/...'
            }),
        }


class AddMemberForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите username пользователя'
        })
    )


class VoteForm(forms.ModelForm):
    option_1 = forms.CharField(label='Вариант 1', widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_2 = forms.CharField(label='Вариант 2', widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_3 = forms.CharField(label='Вариант 3', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_4 = forms.CharField(label='Вариант 4', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Vote
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'expense_type', 'paid_by']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'expense_type': forms.Select(attrs={'class': 'form-control'}),
            'paid_by': forms.Select(attrs={'class': 'form-control'}),
        }


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class TripCommentForm(forms.ModelForm):
    class Meta:
        model = TripComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Напишите комментарий...'
            })
        }


class DayPlanForm(forms.ModelForm):
    class Meta:
        model = DayPlan
        fields = ['day_number', 'title', 'description']
        widgets = {
            'day_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'День'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control auto-resize',
                'rows': 1,
                'placeholder': 'Описание'
            }),
        }