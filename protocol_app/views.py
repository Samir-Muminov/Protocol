# protocol_app/views.py
import json
import calendar
import datetime
from collections import defaultdict

from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import (
    TemplateView, CreateView, View, FormView
)
from django.urls import reverse_lazy

from .models import DailyReport, MotivationQuote
from .forms import DailyReportForm, ProtocolRegistrationForm


# ══════════════════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class ProtocolLoginView(LoginView):
    """
    Custom login view using our Protocol-styled template.
    Redirects authenticated users straight to dashboard.
    """
    template_name = 'protocol_app/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


# /* PATH: Auth Views — Logout Fix */
class ProtocolLogoutView(View):
    """
    GET request shows a confirmation page.
    POST request performs the actual logout and redirects to login.
    This prevents accidental logouts and satisfies Django's CSRF
    protection on logout (required in Django 5+).
    """
    def get(self, request, *args, **kwargs):
        from django.shortcuts import render
        return render(request, 'protocol_app/logout_confirm.html')

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout as auth_logout
        auth_logout(request)
        return redirect('login')


class RegisterView(CreateView):
    """
    Registration with our custom form.
    Auto-logs in the new user and redirects to dashboard.
    """
    template_name   = 'protocol_app/register.html'
    form_class      = ProtocolRegistrationForm
    success_url     = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    The main Protocol OS dashboard.
    Builds the triple-bar data, today's report, the collapsed
    calendar heatmap for the current week, and the Protocol Shadow.
    """
    template_name = 'protocol_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user  = self.request.user
        today = timezone.localdate()

        # ── Today's Report ────────────────────────────────────────────────────
        try:
            today_report = DailyReport.objects.get(user=user, date=today)
        except DailyReport.DoesNotExist:
            today_report = None

        # ── Current Week Heatmap (collapsed calendar) ─────────────────────────
        # Monday of the current week
        week_start = today - datetime.timedelta(days=today.weekday())
        week_days  = [week_start + datetime.timedelta(days=i) for i in range(7)]

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
                'date':       day,
                'date_str':   day.strftime('%Y-%m-%d'),
                'day_name':   day.strftime('%a').upper(),
                'day_num':    day.day,
                'is_today':   day == today,
                'report':     report,
                'score':      report.discipline_score if report else None,
                'dot_class':  _score_to_dot_class(report.discipline_score if report else None),
            })

        # ── Protocol Shadow (Bar 3 projection) ────────────────────────────────
        shadow = _calculate_protocol_shadow(user, today)

        # ── Form for modal ────────────────────────────────────────────────────
        initial_date = {'date': today}
        form = DailyReportForm(initial=initial_date)
        # /* PATH: Streak Calculator */
        streak = 0
        check_date = today
        while True:
            if DailyReport.objects.filter(user=user, date=check_date).exists():
                streak += 1
                check_date -= datetime.timedelta(days=1)
            else:
                break
        ctx['streak'] = streak
        ctx.update({
            'today':        today,
            'streak':       streak,
            'today_report': today_report,
            'week_data':    week_data,
            'shadow':       shadow,
            'form':         form,
            'month_name':   today.strftime('%b').upper(),
            'day_num':      today.strftime('%d').lstrip('0') if hasattr(today, 'strftime') else today.day,
            'weekday':      today.strftime('%A').upper(),
        })
        return ctx


# ══════════════════════════════════════════════════════════════════════════════
# REPORT VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class AddReportView(LoginRequiredMixin, View):
    """
    Handles both GET (render full input page) and POST (save report).
    Supports an optional date URL parameter for back-filling past days.
    Redirects to dashboard after save.
    """
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
        from django.shortcuts import render
        target_date = self.get_initial_date()

        # Pre-fill if report already exists for this date
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
        from django.shortcuts import render

        # Check if updating an existing report
        date_str = request.POST.get('date')
        existing = None
        if date_str:
            try:
                d = datetime.date.fromisoformat(date_str)
                existing = DailyReport.objects.filter(user=request.user, date=d).first()
            except ValueError:
                pass

        form = DailyReportForm(request.POST, instance=existing)
        if form.is_valid():
            report = form.save(commit=False)
            report.user      = request.user
            report.ai_comment = ''  # Force regeneration
            report.save()
            return redirect('dashboard')

        return render(request, self.template_name, {
            'form':        form,
            'target_date': self.get_initial_date(),
        })
# /* PATH: Delete Report View */
class DeleteReportView(LoginRequiredMixin, View):
    """
    Deletes a DailyReport for the given date.
    GET  → shows confirmation page
    POST → performs delete, redirects to dashboard
    CSRF protected. Only deletes reports owned by the logged-in user.
    """
    def get(self, request, date, *args, **kwargs):
        from django.shortcuts import render
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

        # get_object_or_404 ensures user can only delete their own reports
        report = get_object_or_404(DailyReport, user=request.user, date=d)
        report.delete()
        return redirect('dashboard')

# ══════════════════════════════════════════════════════════════════════════════
# AJAX VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class DayCardAjaxView(LoginRequiredMixin, View):
    """
    AJAX endpoint: returns JSON for a specific day's card.
    Called when user clicks a day in the expanded calendar.
    URL: /ajax/day/YYYY-MM-DD/
    """
    def get(self, request, date, *args, **kwargs):
        try:
            d = datetime.date.fromisoformat(date)
        except ValueError:
            return JsonResponse({'error': 'Invalid date'}, status=400)

        try:
            report = DailyReport.objects.get(user=request.user, date=d)
            # /* PATH: AJAX — Day Card data dict (Phase 2 scoring) */
            data = {
                'exists':          True,
                'date':            date,
                'date_display':    d.strftime('%B %d, %Y').upper(),
                'it_hours':        report.it_math_hours,
                'pages':           report.pages_read,
                'calories':        report.calories,
                'distance_km':     report.distance_km,
                'score':           report.discipline_score,
                'rank':            report.rank,
                'rank_slug':       report.rank_slug,
                'rank_image_url':  report.rank_image_url,
                'rank_progress':   report.rank_progress_pct,
                'next_rank':       report.next_rank_data[1] if report.next_rank_data else 'MAX',
                'ai_comment':      report.ai_comment,
                'it_pct':          report.it_progress_pct,
                'books_pct':       report.books_progress_pct,
                'kcal_pct':        report.kcal_progress_pct,
                'km_pct':          report.km_progress_pct,
                'color_class':     report.score_color_class,
                'it_pts':          report.it_points,
                'books_pts':       report.books_points,
                'kcal_pts':        report.kcal_points,           
                }
        except DailyReport.DoesNotExist:
            data = {
                'exists':       False,
                'date':         date,
                'date_display': d.strftime('%B %d, %Y').upper(),
            }

        return JsonResponse(data)


class CalendarAjaxView(LoginRequiredMixin, View):
    """
    AJAX endpoint: returns the full month's heatmap data as JSON.
    Query params: ?year=YYYY&month=MM
    Called when user expands the calendar.
    """
    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        try:
            year  = int(request.GET.get('year',  today.year))
            month = int(request.GET.get('month', today.month))
        except (TypeError, ValueError):
            year, month = today.year, today.month

        # All days in the month
        _, days_in_month = calendar.monthrange(year, month)
        month_start = datetime.date(year, month, 1)
        month_end   = datetime.date(year, month, days_in_month)

        reports = DailyReport.objects.filter(
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
                'weekday':   d.weekday(),   # 0=Mon, 6=Sun
                'is_today':  d == today,
                'is_future': d > today,
                'score':     report.discipline_score if report else None,
                'dot_class': _score_to_dot_class(report.discipline_score if report else None),
            })

        # Padding for the first row (empty cells before month starts)
        first_weekday = month_start.weekday()  # 0=Mon

        return JsonResponse({
            'year':          year,
            'month':         month,
            'month_name':    month_start.strftime('%B').upper(),
            'days':          days,
            'first_weekday': first_weekday,
        })


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL REPORT VIEW
# ══════════════════════════════════════════════════════════════════════════════

class GlobalReportView(LoginRequiredMixin, TemplateView):
    """
    Macro view: shows aggregated stats for weekly / monthly /
    half-year / yearly periods, trend line data, and a
    period-over-period comparison verdict.
    """
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

        # Current period reports
        reports = list(DailyReport.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=today,
        ).order_by('date'))

        # Previous period reports
        prev_reports = list(DailyReport.objects.filter(
            user=user,
            date__gte=prev_start,
            date__lte=prev_end,
        ))

        # Aggregation
        avg_score  = _average_score(reports)
        prev_score = _average_score(prev_reports)

        if prev_score and prev_score > 0:
            delta_pct = ((avg_score - prev_score) / prev_score) * 100
            if delta_pct > 0:
                comparison = f"You are {abs(delta_pct):.0f}% more disciplined than last {period}."
            elif delta_pct < 0:
                comparison = f"You are {abs(delta_pct):.0f}% less disciplined than last {period}. The Protocol does not forgive regression."
            else:
                comparison = "Identical to last period. Stagnation is decline."
        elif reports:
            comparison = "No previous period data. The Protocol begins today."
        else:
            comparison = "No data for this period. Log your first report."

        # Trend line data for SVG chart (date → score pairs)
        trend_data = [
            {
                'date': r.date.strftime('%b %#d'),
                'score': r.discipline_score,
            }
            for r in reports
        ]

        # Summary totals
        total_it    = sum(r.it_math_hours for r in reports)
        total_pages = sum(r.pages_read    for r in reports)
        total_kcal  = sum(r.calories      for r in reports)
        total_km    = sum(r.distance_km   for r in reports)

        ctx.update({
            'period':        period,
            'period_label':  self.PERIOD_LABELS[period],
            'periods':       self.PERIOD_LABELS,
            'reports':       reports,
            'avg_score':     avg_score,
            'prev_score':    prev_score,
            'comparison':    comparison,
            'trend_data':    json.dumps(trend_data),
            'total_it':      total_it,
            'total_pages':   total_pages,
            'total_kcal':    total_kcal,
            'total_km':      round(total_km, 1),
            'report_count':  len(reports),
        })
        return ctx


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

# /* PATH: Helper — Score to dot class (updated for 22.75 scale) */
def _score_to_dot_class(score):
    """Maps discipline_score (0–22.75) to a CSS heatmap dot class."""
    if score is None:
        return 'dot-empty'
    if score < 5.84:
        return 'dot-low'
    if score < 13.08:
        return 'dot-mid'
    return 'dot-high'


def _average_score(reports):
    """Returns the average discipline_score for a list of reports."""
    if not reports:
        return 0.0
    return round(sum(r.discipline_score for r in reports) / len(reports), 2)


def _calculate_protocol_shadow(user, today):
    """
    Protocol Shadow: projects where the user will be in 180 days
    if they maintain today's pace.

    Uses the last 7 days of data as the 'current pace' baseline.
    Returns a dict with projection strings for the UI.
    """
    DAYS_AHEAD   = 180
    LOOKBACK     = 7

    start = today - datetime.timedelta(days=LOOKBACK - 1)
    recent = list(DailyReport.objects.filter(
        user=user,
        date__gte=start,
        date__lte=today,
    ))

    if not recent:
        return {
            'has_data':       False,
            'message':        'Log at least one day to unlock the Protocol Shadow.',
            'days_ahead':     DAYS_AHEAD,
        }

    # Daily averages from recent pace
    avg_it    = sum(r.it_math_hours for r in recent) / LOOKBACK
    avg_pages = sum(r.pages_read    for r in recent) / LOOKBACK
    avg_kcal  = sum(r.calories      for r in recent) / LOOKBACK
    avg_km    = sum(r.distance_km   for r in recent) / LOOKBACK
    avg_score = _average_score(recent)

        # /* PATH: Protocol Shadow — updated for 22.75 scale */
    proj_it    = avg_it    * DAYS_AHEAD
    proj_pages = avg_pages * DAYS_AHEAD
    proj_kcal  = avg_kcal  * DAYS_AHEAD
    proj_km    = avg_km    * DAYS_AHEAD

    # Rank projection based on avg score on new 22.75 scale
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
        'has_data':    True,
        'days_ahead':  DAYS_AHEAD,
        'avg_score':   avg_score,
        'proj_it':     round(proj_it, 1),
        'proj_pages':  int(proj_pages),
        'proj_kcal':   int(proj_kcal),
        'proj_km':     round(proj_km, 1),
        'rank_proj':   rank_proj,
        'message': (
            f"In {DAYS_AHEAD} days at this pace: "
            f"{round(proj_it, 0):.0f}h of IT mastery, "
            f"{int(proj_pages):,} pages consumed, "
            f"{round(proj_km, 0):.0f}km covered — "
            f"{rank_proj}."
        ),
    }