# protocol_app/views.py
import json
import calendar
import datetime
import logging

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, View
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from django_ratelimit.decorators import ratelimit

from .models import DailyReport, MotivationQuote
from .forms import DailyReportForm, ProtocolRegistrationForm
from .validators import (
    validate_daily_report,
    validate_registration,
    ValidationError as ProtocolValidationError,
)

logger = logging.getLogger('protocol_app')


# ══════════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════

# SECURITY: Rate limited — 10 login attempts per 5 minutes per IP
@method_decorator(
    ratelimit(key='ip', rate='10/5m', method='POST', block=True),
    name='dispatch'
)
@method_decorator(never_cache, name='dispatch')
class ProtocolLoginView(LoginView):
    template_name = 'protocol_app/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        ip = _get_client_ip(self.request)
        logger.warning(f"Failed login attempt from IP: {ip}")
        return super().form_invalid(form)


# SECURITY: True POST-based logout — no GET logout possible
class ProtocolLogoutView(View):
    """
    GET  → confirmation page
    POST → performs logout + redirects to login
    Prevents accidental logout via link crawlers / prefetch.
    """
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return render(request, 'protocol_app/logout_confirm.html')

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout as auth_logout
        auth_logout(request)
        return redirect('login')


# SECURITY: Rate limited — 5 registrations per hour per IP
@method_decorator(
    ratelimit(key='ip', rate='5/h', method='POST', block=True),
    name='dispatch'
)
@method_decorator(never_cache, name='dispatch')
class RegisterView(CreateView):
    template_name = 'protocol_app/register.html'
    form_class    = ProtocolRegistrationForm
    success_url   = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            validate_registration(request.POST)
        except ProtocolValidationError as e:
            form = self.form_class(request.POST)
            return render(request, self.template_name, {
                'form':             form,
                'validation_error': str(e),
            })
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        logger.info(f"New user registered: {user.username}")
        return redirect(self.success_url)


# ══════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'protocol_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user  = self.request.user
        today = timezone.localdate()

        # Today's report
        try:
            today_report = DailyReport.objects.get(user=user, date=today)
        except DailyReport.DoesNotExist:
            today_report = None

        # Current week heatmap
        week_start  = today - datetime.timedelta(days=today.weekday())
        week_days   = [week_start + datetime.timedelta(days=i) for i in range(7)]
        week_reports = DailyReport.objects.filter(
            user=user,
            date__gte=week_start,
            date__lte=week_days[-1],
        )
        week_report_map = {r.date: r for r in week_reports}

        week_data = []
        for day in week_days:
            report = week_report_map.get(day)
            week_data.append({
                'date':      day,
                'date_str':  day.strftime('%Y-%m-%d'),
                'day_name':  day.strftime('%a').upper(),
                'day_num':   day.day,
                'is_today':  day == today,
                'report':    report,
                'score':     report.discipline_score if report else None,
                'dot_class': _score_to_dot_class(
                    report.discipline_score if report else None
                ),
            })

        # Protocol Shadow
        shadow = _calculate_protocol_shadow(user, today)

        # Streak calculator
        streak     = 0
        check_date = today
        while True:
            if DailyReport.objects.filter(user=user, date=check_date).exists():
                streak    += 1
                check_date -= datetime.timedelta(days=1)
            else:
                break

        form = DailyReportForm(initial={'date': today})

        ctx.update({
            'today':        today,
            'today_report': today_report,
            'week_data':    week_data,
            'shadow':       shadow,
            'streak':       streak,
            'form':         form,
            'month_name':   today.strftime('%b').upper(),
            'weekday':      today.strftime('%A').upper(),
        })
        return ctx


# ══════════════════════════════════════════════════════════════════════
# REPORT VIEWS
# ══════════════════════════════════════════════════════════════════════

class AddReportView(LoginRequiredMixin, View):
    template_name = 'protocol_app/add_report.html'

    def get_initial_date(self):
        date_str = self.kwargs.get('date')
        if date_str:
            try:
                return datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return timezone.localdate()

    def get(self, request, *args, **kwargs):
        target_date = self.get_initial_date()
        try:
            existing = DailyReport.objects.get(user=request.user, date=target_date)
            form = DailyReportForm(instance=existing)
        except DailyReport.DoesNotExist:
            form = DailyReportForm(initial={'date': target_date})

        return render(request, self.template_name, {
            'form':        form,
            'target_date': target_date,
        })

    def post(self, request, *args, **kwargs):
        # SECURITY: Validate and sanitize before touching the DB
        try:
            clean_data = validate_daily_report(request.POST)
        except ProtocolValidationError as e:
            form = DailyReportForm(request.POST)
            return render(request, self.template_name, {
                'form':             form,
                'target_date':      self.get_initial_date(),
                'validation_error': str(e),
            })

        existing = DailyReport.objects.filter(
            user=request.user,
            date=clean_data['date']
        ).first()

        form = DailyReportForm(clean_data, instance=existing)
        if form.is_valid():
            report            = form.save(commit=False)
            report.user       = request.user
            report.ai_comment = ''
            report.save()
            logger.info(
                f"Report saved: user={request.user.username} "
                f"date={clean_data['date']}"
            )
            return redirect('dashboard')

        return render(request, self.template_name, {
            'form':        form,
            'target_date': self.get_initial_date(),
        })


class DeleteReportView(LoginRequiredMixin, View):
    """
    GET  → confirmation page
    POST → delete + redirect
    CSRF protected. Users can only delete their own reports.
    """
    def get(self, request, date, *args, **kwargs):
        try:
            d = datetime.date.fromisoformat(date)
        except ValueError:
            return redirect('dashboard')

        report = get_object_or_404(DailyReport, user=request.user, date=d)
        return render(request, 'protocol_app/delete_confirm.html', {
            'report': report,
            'date':   date,
        })

    def post(self, request, date, *args, **kwargs):
        try:
            d = datetime.date.fromisoformat(date)
        except ValueError:
            return redirect('dashboard')

        report = get_object_or_404(DailyReport, user=request.user, date=d)
        report.delete()
        logger.info(
            f"Report deleted: user={request.user.username} date={date}"
        )
        return redirect('dashboard')


# ══════════════════════════════════════════════════════════════════════
# AJAX VIEWS
# ══════════════════════════════════════════════════════════════════════

# SECURITY: Rate limited — 60 requests/min per user
@method_decorator(
    ratelimit(key='user_or_ip', rate='60/m', method='GET', block=True),
    name='dispatch'
)
class DayCardAjaxView(LoginRequiredMixin, View):
    def get(self, request, date, *args, **kwargs):
        try:
            d = datetime.date.fromisoformat(date)
        except ValueError:
            return JsonResponse({'error': 'Invalid date'}, status=400)

        try:
            report = DailyReport.objects.get(user=request.user, date=d)
            data = {
                'exists':         True,
                'date':           date,
                'date_display':   d.strftime('%B %d, %Y').upper(),
                'it_hours':       report.it_math_hours,
                'pages':          report.pages_read,
                'calories':       report.calories,
                'distance_km':    report.distance_km,
                'score':          report.discipline_score,
                'rank':           report.rank,
                'rank_slug':      report.rank_slug,
                'rank_image_url': report.rank_image_url,
                'rank_progress':  report.rank_progress_pct,
                'next_rank':      (
                    report.next_rank_data[1]
                    if report.next_rank_data else 'MAX'
                ),
                'ai_comment':     report.ai_comment,
                'it_pct':         report.it_progress_pct,
                'books_pct':      report.books_progress_pct,
                'kcal_pct':       report.kcal_progress_pct,
                'km_pct':         report.km_progress_pct,
                'color_class':    report.score_color_class,
                'it_pts':         report.it_points,
                'books_pts':      report.books_points,
                'kcal_pts':       report.kcal_points,
                'km_pts':         report.km_points,
            }
        except DailyReport.DoesNotExist:
            data = {
                'exists':       False,
                'date':         date,
                'date_display': d.strftime('%B %d, %Y').upper(),
            }

        return JsonResponse(data)


# SECURITY: Rate limited — 30 requests/min per user
@method_decorator(
    ratelimit(key='user_or_ip', rate='30/m', method='GET', block=True),
    name='dispatch'
)
class CalendarAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        try:
            year  = int(request.GET.get('year',  today.year))
            month = int(request.GET.get('month', today.month))
        except (TypeError, ValueError):
            year, month = today.year, today.month

        _, days_in_month = calendar.monthrange(year, month)
        month_start = datetime.date(year, month, 1)
        month_end   = datetime.date(year, month, days_in_month)

        reports    = DailyReport.objects.filter(
            user=request.user,
            date__gte=month_start,
            date__lte=month_end,
        )
        report_map = {r.date: r for r in reports}

        days = []
        for day_num in range(1, days_in_month + 1):
            d      = datetime.date(year, month, day_num)
            report = report_map.get(d)
            days.append({
                'date':      d.strftime('%Y-%m-%d'),
                'day':       day_num,
                'weekday':   d.weekday(),
                'is_today':  d == today,
                'is_future': d > today,
                'score':     report.discipline_score if report else None,
                'dot_class': _score_to_dot_class(
                    report.discipline_score if report else None
                ),
            })

        return JsonResponse({
            'year':          year,
            'month':         month,
            'month_name':    month_start.strftime('%B').upper(),
            'days':          days,
            'first_weekday': month_start.weekday(),
        })


# ══════════════════════════════════════════════════════════════════════
# GLOBAL REPORT
# ══════════════════════════════════════════════════════════════════════

class GlobalReportView(LoginRequiredMixin, TemplateView):
    template_name = 'protocol_app/global_report.html'

    PERIODS = {
        'week':     7,
        'month':    30,
        'halfyear': 182,
        'year':     365,
    }
    PERIOD_LABELS = {
        'week':     'This Week',
        'month':    'This Month',
        'halfyear': 'Last 6 Months',
        'year':     'This Year',
    }

    def get_context_data(self, **kwargs):
        ctx    = super().get_context_data(**kwargs)
        user   = self.request.user
        today  = timezone.localdate()
        period = self.request.GET.get('period', 'week')

        if period not in self.PERIODS:
            period = 'week'

        days       = self.PERIODS[period]
        start_date = today - datetime.timedelta(days=days - 1)
        prev_start = start_date - datetime.timedelta(days=days)
        prev_end   = start_date - datetime.timedelta(days=1)

        reports = list(DailyReport.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=today,
        ).order_by('date'))

        prev_reports = list(DailyReport.objects.filter(
            user=user,
            date__gte=prev_start,
            date__lte=prev_end,
        ))

        avg_score  = _average_score(reports)
        prev_score = _average_score(prev_reports)

        if prev_score and prev_score > 0:
            delta_pct = ((avg_score - prev_score) / prev_score) * 100
            if delta_pct > 0:
                comparison = (
                    f"You are {abs(delta_pct):.0f}% more disciplined "
                    f"than last {period}."
                )
            elif delta_pct < 0:
                comparison = (
                    f"You are {abs(delta_pct):.0f}% less disciplined "
                    f"than last {period}. The Protocol does not forgive regression."
                )
            else:
                comparison = "Identical to last period. Stagnation is decline."
        elif reports:
            comparison = "No previous period data. The Protocol begins today."
        else:
            comparison = "No data for this period. Log your first report."

        # FIX: Use %-d on Windows, remove leading zero cross-platform
        trend_data = []
        for r in reports:
            day_str = str(r.date.day)   # cross-platform, no %#d or %-d
            month_str = r.date.strftime('%b')
            trend_data.append({
                'date':  f"{month_str} {day_str}",
                'score': r.discipline_score,
            })

        ctx.update({
            'period':       period,
            'period_label': self.PERIOD_LABELS[period],
            'periods':      self.PERIOD_LABELS,
            'reports':      reports,
            'avg_score':    avg_score,
            'prev_score':   prev_score,
            'comparison':   comparison,
            'trend_data':   json.dumps(trend_data),
            'total_it':     sum(r.it_math_hours for r in reports),
            'total_pages':  sum(r.pages_read    for r in reports),
            'total_kcal':   sum(r.calories      for r in reports),
            'total_km':     round(sum(r.distance_km for r in reports), 1),
            'report_count': len(reports),
        })
        return ctx


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _score_to_dot_class(score):
    if score is None:
        return 'dot-empty'
    if score < 5.84:
        return 'dot-low'
    if score < 13.08:
        return 'dot-mid'
    return 'dot-high'


def _average_score(reports):
    if not reports:
        return 0.0
    return round(
        sum(r.discipline_score for r in reports) / len(reports), 2
    )


def _calculate_protocol_shadow(user, today):
    DAYS_AHEAD = 180
    LOOKBACK   = 7

    start  = today - datetime.timedelta(days=LOOKBACK - 1)
    recent = list(DailyReport.objects.filter(
        user=user,
        date__gte=start,
        date__lte=today,
    ))

    if not recent:
        return {
            'has_data': False,
            'message':  'Log at least one day to unlock the Protocol Shadow.',
            'days_ahead': DAYS_AHEAD,
        }

    # Daily averages (divide by LOOKBACK not len(recent) — gaps count)
    avg_it    = sum(r.it_math_hours for r in recent) / LOOKBACK
    avg_pages = sum(r.pages_read    for r in recent) / LOOKBACK
    avg_kcal  = sum(r.calories      for r in recent) / LOOKBACK
    avg_km    = sum(r.distance_km   for r in recent) / LOOKBACK
    avg_score = _average_score(recent)

    proj_it    = avg_it    * DAYS_AHEAD
    proj_pages = avg_pages * DAYS_AHEAD
    proj_kcal  = avg_kcal  * DAYS_AHEAD
    proj_km    = avg_km    * DAYS_AHEAD

    if avg_score < 5.84:
        rank_proj = "still in Novice territory"
    elif avg_score < 9.46:
        rank_proj = "reaching Apprentice III"
    elif avg_score < 13.08:
        rank_proj = "breaking into Intermediate"
    elif avg_score < 16.71:
        rank_proj = "climbing Advanced ranks"
    elif avg_score < 19.13:
        rank_proj = "approaching Master"
    elif avg_score < 22.75:
        rank_proj = "knocking on Protocolmaxxer's door"
    else:
        rank_proj = "a confirmed Protocolmaxxer — the apex"

    return {
        'has_data':  True,
        'days_ahead': DAYS_AHEAD,
        'avg_score':  avg_score,
        'proj_it':    round(proj_it, 1),
        'proj_pages': int(proj_pages),
        'proj_kcal':  int(proj_kcal),
        'proj_km':    round(proj_km, 1),
        'rank_proj':  rank_proj,
        'message': (
            f"In {DAYS_AHEAD} days at this pace: "
            f"{round(proj_it):.0f}h of IT mastery, "
            f"{int(proj_pages):,} pages consumed, "
            f"{round(proj_km):.0f}km covered — "
            f"{rank_proj}."
        ),
    }


def _get_client_ip(request):
    """SECURITY: Real client IP, respects reverse proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def handler429(request, exception=None):
    """SECURITY: Graceful 429 — JSON for AJAX, HTML for browser."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(
            {'error': 'Too many requests. Please slow down.'},
            status=429
        )
    return render(request, 'protocol_app/429.html', status=429)