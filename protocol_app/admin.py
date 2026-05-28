# protocol_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count
from .models import MotivationQuote, DailyReport


@admin.register(MotivationQuote)
class MotivationQuoteAdmin(admin.ModelAdmin):
    list_display  = ('short_text', 'font_style', 'is_active', 'created_at')
    list_editable = ('is_active', 'font_style')
    list_filter   = ('is_active', 'font_style')
    search_fields = ('text',)
    actions       = ['activate_quotes', 'deactivate_quotes']

    def short_text(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    short_text.short_description = 'Quote'

    def activate_quotes(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} quotes activated.')
    activate_quotes.short_description = 'Activate selected quotes'

    def deactivate_quotes(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} quotes deactivated.')
    deactivate_quotes.short_description = 'Deactivate selected quotes'


class ScoreRangeFilter(admin.SimpleListFilter):
    title        = 'Score Range'
    parameter_name = 'score_range'

    def lookups(self, request, model_admin):
        return [
            ('novice',       'Novice (0–5.83)'),
            ('apprentice',   'Apprentice (5.84–9.45)'),
            ('intermediate', 'Intermediate (9.46–13.07)'),
            ('advanced',     'Advanced (13.08–16.70)'),
            ('expert',       'Expert+ (16.71+)'),
        ]

    def queryset(self, request, queryset):
        # Note: score is a property so we can't filter in DB directly.
        # We pull IDs and filter in Python — acceptable for admin use.
        if not self.value():
            return queryset
        ranges = {
            'novice':       (0,     5.83),
            'apprentice':   (5.84,  9.45),
            'intermediate': (9.46,  13.07),
            'advanced':     (13.08, 16.70),
            'expert':       (16.71, 22.75),
        }
        low, high = ranges[self.value()]
        ids = [
            r.pk for r in queryset.select_related('user')
            if low <= r.discipline_score <= high
        ]
        return queryset.filter(pk__in=ids)


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display   = (
        'user', 'date', 'it_math_hours', 'pages_read',
        'calories', 'distance_km',
        'score_badge', 'rank_display', 'updated_at'
    )
    list_filter    = ('date', ScoreRangeFilter)
    search_fields  = ('user__username',)
    readonly_fields = (
        'score_badge', 'rank_display', 'ai_comment',
        'created_at', 'updated_at',
        'it_points_display', 'books_points_display',
        'kcal_points_display', 'km_points_display',
    )
    ordering       = ('-date',)
    date_hierarchy = 'date'
    actions        = ['regenerate_ai_comments']

    fieldsets = (
        ('Identity', {
            'fields': ('user', 'date')
        }),
        ('Raw Metrics', {
            'fields': (
                'it_math_hours', 'pages_read',
                'calories', 'distance_km'
            )
        }),
        ('Calculated (read-only)', {
            'fields': (
                'it_points_display', 'books_points_display',
                'kcal_points_display', 'km_points_display',
                'score_badge', 'rank_display',
            )
        }),
        ('AI Verdict', {
            'fields': ('ai_comment',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def score_badge(self, obj):
        s = obj.discipline_score
        if s >= 16.71:
            color = '#B8972A'
        elif s >= 9.46:
            color = '#1B4FD8'
        elif s >= 5.84:
            color = '#0A7C4E'
        else:
            color = '#C0392B'
        return format_html(
            '<span style="'
            'background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-weight:700;font-size:12px;">'
            '{}</span>',
            color, f'{s:.2f}'
        )
    score_badge.short_description = 'Score'

    def rank_display(self, obj):
        return obj.rank
    rank_display.short_description = 'Rank'

    def it_points_display(self, obj):
        return f'{obj.it_points:.4f} / {obj.IT_MAX_PTS} pts'
    it_points_display.short_description = 'IT Points'

    def books_points_display(self, obj):
        return f'{obj.books_points:.4f} / {obj.BOOKS_MAX_PTS} pts'
    books_points_display.short_description = 'Books Points'

    def kcal_points_display(self, obj):
        return f'{obj.kcal_points:.4f} / {obj.KCAL_MAX_PTS} pts'
    kcal_points_display.short_description = 'Kcal Points'

    def km_points_display(self, obj):
        return f'{obj.km_points:.4f} / {obj.KM_MAX_PTS} pts'
    km_points_display.short_description = 'KM Points'

    def regenerate_ai_comments(self, request, queryset):
        count = 0
        for report in queryset:
            report.ai_comment = report.generate_ai_comment()
            report.save(update_fields=['ai_comment', 'updated_at'])
            count += 1
        self.message_user(request, f'Regenerated AI comments for {count} reports.')
    regenerate_ai_comments.short_description = 'Regenerate AI comments'