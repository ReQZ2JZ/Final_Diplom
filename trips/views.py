from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.cache import cache
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.conf import settings as django_settings

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import requests
import uuid
import json
import re
import time

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

from .forms import (
    TripForm,
    AddMemberForm,
    VoteForm,
    ExpenseForm,
    ProfileSettingsForm,
    TripCommentForm,
    DayPlanForm
)


def user_has_access(user, trip):
    return TripMember.objects.filter(trip=trip, user=user).exists() or trip.owner == user


def get_user_trips(user):
    return Trip.objects.filter(
        Q(owner=user) | Q(tripmember__user=user)
    ).distinct()


def calculate_debts(trip):
    members = TripMember.objects.filter(trip=trip)
    expenses = Expense.objects.filter(trip=trip, expense_type='shared')

    users = []

    for member in members:
        if member.user not in users:
            users.append(member.user)

    for expense in expenses:
        if expense.paid_by not in users:
            users.append(expense.paid_by)

    if len(users) == 0:
        return []

    total_spent = sum(e.amount for e in expenses)
    share = total_spent / len(users)

    balances = {}

    for user in users:
        balances[user] = 0

    for expense in expenses:
        balances[expense.paid_by] += expense.amount

    for user in balances:
        balances[user] -= share

    debtors = []
    creditors = []

    for user, balance in balances.items():
        if balance < 0:
            debtors.append([user, -balance])
        elif balance > 0:
            creditors.append([user, balance])

    debts = []
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor, debt_amount = debtors[i]
        creditor, credit_amount = creditors[j]

        amount = min(debt_amount, credit_amount)

        debts.append({
            'from': debtor,
            'to': creditor,
            'amount': round(amount)
        })

        debtors[i][1] -= amount
        creditors[j][1] -= amount

        if round(debtors[i][1]) == 0:
            i += 1

        if round(creditors[j][1]) == 0:
            j += 1

    return debts


def get_category_stats(expenses):
    categories = []

    for value, label in Expense.CATEGORY_CHOICES:
        total = sum(e.amount for e in expenses if e.category == value)

        if total > 0:
            categories.append({
                'name': label,
                'amount': total
            })

    return categories


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", {
        "form": form
    })


@login_required
def dashboard(request):
    trips = get_user_trips(request.user)

    return render(request, "trips/dashboard.html", {
        "trips": trips
    })


@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    members = TripMember.objects.filter(trip=trip)
    votes = Vote.objects.filter(trip=trip).order_by('-created_at')
    expenses = Expense.objects.filter(trip=trip).order_by('-created_at')
    comments = TripComment.objects.filter(trip=trip).order_by('-created_at')
    day_plans = DayPlan.objects.filter(trip=trip).order_by('day_number')

    spent = sum(e.amount for e in expenses)
    left = trip.budget - spent

    if trip.budget > 0:
        budget_percent = round((spent / trip.budget) * 100)
    else:
        budget_percent = 0

    debts = calculate_debts(trip)
    debts_you_owe = []
    debts_owed_to_you = []
    other_debts = []

    for debt in debts:
        if debt['from'] == request.user:
            debts_you_owe.append(debt)
        elif debt['to'] == request.user:
            debts_owed_to_you.append(debt)
        else:
            other_debts.append(debt)

    category_stats = get_category_stats(expenses)

    comment_form = TripCommentForm()
    day_plan_form = DayPlanForm()

    members_spending = []

    members = TripMember.objects.filter(trip=trip)

    for member in members:
        total = Expense.objects.filter(
            trip=trip,
            paid_by=member.user
        ).aggregate(sum=Sum('amount'))['sum'] or 0

        members_spending.append({
            'user': member.user,
            'amount': total
        })

    members_spending = sorted(
        members_spending,
        key=lambda x: x['amount'],
        reverse=True
    )

    return render(request, "trips/trip_detail.html", {
        "trip": trip,
        "votes": votes,
        "expenses": expenses,
        "spent": spent,
        "left": left,
        "budget_percent": budget_percent,
        "members": members,
        "debts": debts,
        "category_stats": category_stats,
        "comments": comments,
        "day_plans": day_plans,
        "comment_form": comment_form,
        "day_plan_form": day_plan_form,
        "debts_you_owe": debts_you_owe,
        "debts_owed_to_you": debts_owed_to_you,
        "other_debts": other_debts,
        "members_spending": members_spending,
    })


@login_required
def create_trip(request):
    if request.method == 'POST':
        form = TripForm(request.POST)

        if form.is_valid():
            trip = form.save(commit=False)
            trip.owner = request.user
            trip.save()

            TripMember.objects.create(
                trip=trip,
                user=request.user,
                role='owner'
            )

            return redirect('dashboard')
    else:
        form = TripForm()

    return render(request, "trips/create_trip.html", {
        "form": form
    })

@login_required
def edit_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if trip.owner != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip)

        if form.is_valid():
            form.save()
            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = TripForm(instance=trip)

    return render(request, "trips/edit_trip.html", {
        "form": form,
        "trip": trip
    })

@login_required
def delete_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if trip.owner != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        trip.delete()
        return redirect('dashboard')

    return redirect('trip_detail', trip_id=trip.id)


@login_required
def add_member(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    if request.method == 'POST':
        form = AddMemberForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']

            try:
                user = User.objects.get(username=username)

                if not TripMember.objects.filter(trip=trip, user=user).exists():
                    TripMember.objects.create(
                        trip=trip,
                        user=user,
                        role='member'
                    )

                return redirect('trip_detail', trip_id=trip.id)

            except User.DoesNotExist:
                form.add_error('username', 'Пользователь не найден')
    else:
        form = AddMemberForm()

    return render(request, "trips/add_member.html", {
        "form": form,
        "trip": trip
    })


@login_required
def create_vote(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    if request.method == 'POST':
        form = VoteForm(request.POST)

        if form.is_valid():
            vote = form.save(commit=False)
            vote.trip = trip
            vote.save()

            options = [
                form.cleaned_data['option_1'],
                form.cleaned_data['option_2'],
                form.cleaned_data.get('option_3'),
                form.cleaned_data.get('option_4'),
            ]

            for option_title in options:
                if option_title:
                    VoteOption.objects.create(
                        vote=vote,
                        title=option_title
                    )

            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = VoteForm()

    return render(request, "trips/create_vote.html", {
        "form": form,
        "trip": trip
    })


@login_required
def vote_detail(request, vote_id):
    vote = get_object_or_404(Vote, id=vote_id)

    if not user_has_access(request.user, vote.trip):
        return redirect('dashboard')

    options = vote.options.all()
    total_answers = VoteAnswer.objects.filter(vote=vote).count()

    user_answer = VoteAnswer.objects.filter(
        vote=vote,
        user=request.user
    ).first()

    option_stats = []

    for option in options:
        count = VoteAnswer.objects.filter(option=option).count()

        if total_answers > 0:
            percent = round((count / total_answers) * 100)
        else:
            percent = 0

        option_stats.append({
            'option': option,
            'count': count,
            'percent': percent
        })

    return render(request, "trips/vote_detail.html", {
        "vote": vote,
        "option_stats": option_stats,
        "user_answer": user_answer,
    })


@login_required
def submit_vote(request, vote_id):
    vote = get_object_or_404(Vote, id=vote_id)

    if not user_has_access(request.user, vote.trip):
        return redirect('dashboard')

    if request.method == 'POST':
        option_id = request.POST.get('option_id')
        option = get_object_or_404(VoteOption, id=option_id, vote=vote)

        VoteAnswer.objects.update_or_create(
            vote=vote,
            user=request.user,
            defaults={'option': option}
        )

    return redirect('vote_detail', vote_id=vote.id)


@login_required
def create_expense(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    members = TripMember.objects.filter(trip=trip)

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        form.fields['paid_by'].queryset = User.objects.filter(
            id__in=[member.user.id for member in members]
        )

        if form.is_valid():
            expense = form.save(commit=False)
            expense.trip = trip
            expense.save()

            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = ExpenseForm()
        form.fields['paid_by'].queryset = User.objects.filter(
            id__in=[member.user.id for member in members]
        )

    return render(request, "trips/create_expense.html", {
        "form": form,
        "trip": trip
    })


@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    trip = expense.trip

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    if request.method == 'POST':
        expense.delete()

    return redirect('trip_detail', trip_id=trip.id)


@login_required
def add_comment(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    if request.method == 'POST':
        form = TripCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.trip = trip
            comment.user = request.user
            comment.save()

    return redirect('trip_detail', trip_id=trip.id)


@login_required
def add_day_plan(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    if request.method == 'POST':
        form = DayPlanForm(request.POST)

        if form.is_valid():
            day_plan = form.save(commit=False)
            day_plan.trip = trip
            day_plan.save()

    return redirect('trip_detail', trip_id=trip.id)


@login_required
def trip_pdf_report(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    expenses = Expense.objects.filter(trip=trip)
    members = TripMember.objects.filter(trip=trip)
    debts = calculate_debts(trip)

    spent = sum(e.amount for e in expenses)
    left = trip.budget - spent

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="trip_{trip.id}_report.pdf"'

    # Подключаем Arial с поддержкой русского языка
    font_path = "C:/Windows/Fonts/arial.ttf"
    bold_font_path = "C:/Windows/Fonts/arialbd.ttf"

    pdfmetrics.registerFont(TTFont("Arial", font_path))
    pdfmetrics.registerFont(TTFont("Arial-Bold", bold_font_path))

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50

    p.setFont("Arial-Bold", 18)
    p.drawString(50, y, f"Отчёт по поездке: {trip.title}")

    y -= 35
    p.setFont("Arial", 11)
    p.drawString(50, y, f"Направление: {trip.destination}")
    y -= 18
    p.drawString(50, y, f"Даты: {trip.start_date} — {trip.end_date}")
    y -= 18
    p.drawString(50, y, f"Бюджет: {trip.budget} ₽")
    y -= 18
    p.drawString(50, y, f"Потрачено: {spent} ₽")
    y -= 18
    p.drawString(50, y, f"Осталось: {left} ₽")

    y -= 35
    p.setFont("Arial-Bold", 14)
    p.drawString(50, y, "Участники")

    p.setFont("Arial", 11)
    y -= 22

    for member in members:
        p.drawString(60, y, f"- {member.user.username} ({member.role})")
        y -= 16

    y -= 20
    p.setFont("Arial-Bold", 14)
    p.drawString(50, y, "Расходы")

    p.setFont("Arial", 11)
    y -= 22

    for expense in expenses:
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Arial", 11)

        p.drawString(
            60,
            y,
            f"- {expense.title}: {expense.amount} ₽, оплатил {expense.paid_by.username}"
        )
        y -= 16

    y -= 20
    p.setFont("Arial-Bold", 14)
    p.drawString(50, y, "Долги")

    p.setFont("Arial", 11)
    y -= 22

    if debts:
        for debt in debts:
            if y < 80:
                p.showPage()
                y = height - 50
                p.setFont("Arial", 11)

            p.drawString(
                60,
                y,
                f"- {debt['from'].username} должен {debt['to'].username}: {debt['amount']} ₽"
            )
            y -= 16
    else:
        p.drawString(60, y, "Долгов нет")

    p.save()

    return response


@login_required
def notifications(request):
    user_trips = get_user_trips(request.user)

    from django.utils import timezone
    request.session['last_notifications_view'] = str(timezone.now())

    recent_votes = Vote.objects.filter(trip__in=user_trips).order_by('-created_at')[:5]
    recent_expenses = Expense.objects.filter(trip__in=user_trips).order_by('-created_at')[:5]
    recent_comments = TripComment.objects.filter(trip__in=user_trips).order_by('-created_at')[:5]

    return render(request, "trips/notifications.html", {
        "recent_votes": recent_votes,
        "recent_expenses": recent_expenses,
        "recent_comments": recent_comments,
    })

@login_required
def profile(request):
    user_trips = get_user_trips(request.user)

    return render(request, "trips/profile.html", {
        "user_trips": user_trips,
        "trips_count": user_trips.count(),
    })


@login_required
def settings_page(request):
    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileSettingsForm(instance=request.user)

    return render(request, "trips/settings.html", {
        "form": form
    })


@login_required
def statistics(request):
    user_trips = get_user_trips(request.user)
    expenses = Expense.objects.filter(trip__in=user_trips)

    total_trips = user_trips.count()
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    total_votes = Vote.objects.filter(trip__in=user_trips).count()
    total_comments = TripComment.objects.filter(trip__in=user_trips).count()

    if total_trips > 0:
        average_budget = round(sum(trip.budget for trip in user_trips) / total_trips)
    else:
        average_budget = 0

    category_stats = get_category_stats(expenses)

    return render(request, "trips/statistics.html", {
        "total_trips": total_trips,
        "total_expenses": total_expenses,
        "total_votes": total_votes,
        "total_comments": total_comments,
        "average_budget": average_budget,
        "category_stats": category_stats,
    })


def _get_gigachat_token():
    cached = cache.get("gigachat_access_token")
    if cached:
        return cached

    last_error = None
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {django_settings.GIGACHAT_KEY}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                verify=False,
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            token = payload["access_token"]
            expires_at = int(payload.get("expires_at", 0))

            # В API часто приходит expires_at в миллисекундах epoch.
            if expires_at > 0:
                now_ms = int(time.time() * 1000)
                ttl_seconds = max(60, (expires_at - now_ms) // 1000 - 120)
            else:
                ttl_seconds = 25 * 60

            cache.set("gigachat_access_token", token, timeout=ttl_seconds)
            return token
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))

    raise RuntimeError(f"Не удалось получить токен GigaChat после 3 попыток: {last_error}")


def _ask_gigachat(token, prompt):
    last_error = None
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"model": "GigaChat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
                verify=False,
                timeout=35,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))

    raise RuntimeError(f"Не удалось получить ответ GigaChat после 3 попыток: {last_error}")


def _extract_first_json_object(text):
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or start >= end:
        return None
    return text[start:end + 1]


def _normalize_place_query(city, place):
    value = str(place).strip()
    if not value:
        return ''

    value = re.sub(r'^\d+[\).\s-]*', '', value).strip()
    value = re.split(r'\s[—:-]\s', value, maxsplit=1)[0].strip()
    value = value.strip('.,;: ')
    if not value:
        return ''

    if value.lower().startswith(city.lower()):
        return value
    return f"{city}, {value}"


def _extract_places_from_text(route_text, city):
    places = []

    # Частый случай: "1. ... 2. ... 3. ..." в одной строке.
    numbered_chunks = re.split(r'(?:^|\s)(?:\d+[\)\.])\s+', route_text)
    candidates = [chunk.strip() for chunk in numbered_chunks if chunk.strip()]

    if not candidates:
        candidates = [line.strip() for line in route_text.splitlines() if line.strip()]

    for raw in candidates:
        # Берем только заголовок места до первого предложения/длинного тире.
        head = re.split(r'[.!?]', raw, maxsplit=1)[0].strip()
        if ' — ' in head:
            head = head.split(' — ', 1)[0].strip()
        if ' - ' in head:
            head = head.split(' - ', 1)[0].strip()

        candidate = _normalize_place_query(city, head or raw)
        if candidate:
            places.append(candidate)

    # Убираем дубли, сохраняя порядок.
    return list(dict.fromkeys(places))[:7]


def _parse_place_item(city, item):
    if isinstance(item, str):
        query = _normalize_place_query(city, item)
        return query, None

    if isinstance(item, dict):
        title = (
            item.get("title")
            or item.get("name")
            or item.get("place")
            or item.get("address")
            or ""
        )
        query = _normalize_place_query(city, title)

        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None:
            lat = item.get("latitude")
        if lon is None:
            lon = item.get("longitude")

        try:
            if lat is not None and lon is not None:
                return query, [float(lat), float(lon)]
        except (TypeError, ValueError):
            pass

        return query, None

    return "", None


def _geocode_place_nominatim(place_query):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": place_query,
                "format": "jsonv2",
                "limit": 1,
            },
            headers={"User-Agent": "trip_together/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None

        first = data[0]
        lat = float(first.get("lat"))
        lon = float(first.get("lon"))
        return [lat, lon]
    except Exception:
        return None


def _geocode_place_yandex(place_query):
    yandex_key = getattr(
        django_settings,
        "YANDEX_MAPS_API_KEY",
        "ec2ace5f-0db6-4222-a1e0-d621c581ec15",
    )
    if not yandex_key:
        return None

    try:
        resp = requests.get(
            "https://geocode-maps.yandex.ru/1.x/",
            params={
                "apikey": yandex_key,
                "format": "json",
                "geocode": place_query,
                "results": 1,
                "lang": "ru_RU",
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        members = (
            data.get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        if not members:
            return None

        pos = (
            members[0]
            .get("GeoObject", {})
            .get("Point", {})
            .get("pos", "")
            .split()
        )
        if len(pos) != 2:
            return None

        lon, lat = float(pos[0]), float(pos[1])
        return [lat, lon]
    except Exception:
        return None


def _geocode_place(place_query):
    # Сначала Яндекс (лучше для российских адресов), затем Nominatim как резерв.
    coords = _geocode_place_yandex(place_query)
    if coords:
        return coords
    return _geocode_place_nominatim(place_query)


@login_required
def geocode_place_api(request):
    query = (request.GET.get('q') or '').strip()
    if not query:
        return JsonResponse({"ok": False, "coords": None, "error": "empty_query"}, status=400)

    coords = _geocode_place(query)
    return JsonResponse({"ok": bool(coords), "coords": coords})


@login_required
def excursion(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not user_has_access(request.user, trip):
        return redirect('dashboard')

    route_text = None
    places = []
    places_coords = []
    error = None
    city = trip.destination

    if request.method == 'POST':
        city = request.POST.get('city', trip.destination)
        interests = request.POST.get('interests', '')
        duration = request.POST.get('duration', '3')

        prompt = (
            f"Ты локальный гид по городу {city}. "
            f"Составь пеший экскурсионный маршрут на {duration} часа(ов). "
            f"Интересы: {interests if interests else 'общие достопримечательности'}. "
            f"Выбери 5-7 реальных мест в этом городе.\n\n"
            f"Верни ответ СТРОГО в JSON и больше ничего (без markdown и комментариев) в формате:\n"
            f"{{\n"
            f"  \"route_text\": \"нумерованный маршрут с кратким описанием каждого места (1-2 предложения)\",\n"
            f"  \"places\": [\n"
            f"    {{\"title\": \"<название места>\", \"address\": \"{city}, <улица/номер или район>\", \"lat\": 55.75, \"lon\": 37.61}},\n"
            f"    {{\"title\": \"...\", \"address\": \"...\", \"lat\": ..., \"lon\": ...}}\n"
            f"  ]\n"
            f"}}\n\n"
            f"Требования к places:\n"
            f"- для каждого места обязательно укажи координаты lat/lon;\n"
            f"- координаты должны быть внутри города {city};\n"
            f"- address начинай с города \"{city}\";\n"
            f"- не используй общие формулировки без конкретики."
        )

        try:
            token = _get_gigachat_token()
            full_response = _ask_gigachat(token, prompt)

            try:
                json_payload = full_response
                if not full_response.strip().startswith('{'):
                    extracted = _extract_first_json_object(full_response)
                    if extracted:
                        json_payload = extracted

                data = json.loads(json_payload)
                route_text = str(data.get('route_text', '')).strip()
                raw_places = data.get('places', [])

                if isinstance(raw_places, list):
                    parsed_places = [_parse_place_item(city, p) for p in raw_places]
                    places = []
                    places_coords = []
                    for query, coord in parsed_places:
                        if not query:
                            continue
                        places.append(query)
                        places_coords.append(coord)
                elif isinstance(raw_places, str):
                    places = [_normalize_place_query(city, p) for p in raw_places.split(';')]
                    places = [p for p in places if p]
                else:
                    places = []

                if not route_text:
                    route_text = full_response.strip()

                if not places and route_text:
                    places = _extract_places_from_text(route_text, city)
            except json.JSONDecodeError:
                # Fallback для старого формата, если модель не вернула JSON.
                if 'PLACES:' in full_response:
                    parts = full_response.split('PLACES:')
                    route_text = parts[0].strip()
                    places = [_normalize_place_query(city, p) for p in parts[1].strip().split(';')]
                    places = [p for p in places if p]
                else:
                    route_text = full_response.strip()
                    places = _extract_places_from_text(route_text, city)

            if places:
                if len(places_coords) == len(places) and any(c is not None for c in places_coords):
                    pass
                else:
                    places_coords = [_geocode_place(p) for p in places]
        except Exception as e:
            error = f"Ошибка при обращении к GigaChat: {e}"

    return render(request, 'trips/excursion.html', {
        'trip': trip,
        'city': city,
        'route_text': route_text,
        'places_json': json.dumps(places, ensure_ascii=False),
        'places_coords_json': json.dumps(places_coords, ensure_ascii=False),
        'error': error,
    })
