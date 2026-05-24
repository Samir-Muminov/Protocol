# protocol_app/admin.py
from django.contrib import admin
from .models import MotivationQuote, DailyReport


@admin.register(MotivationQuote)
class MotivationQuoteAdmin(admin.ModelAdmin):
    list_display  = ('text', 'font_style', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter   = ('is_active', 'font_style')


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display  = ('user', 'date', 'it_math_hours', 'pages_read',
                     'calories', 'distance_km', 'discipline_score_display', 'rank')
    list_filter   = ('user', 'date')
    readonly_fields = ('ai_comment',)

    def discipline_score_display(self, obj):
        return f"{obj.discipline_score:.2f}"
    discipline_score_display.short_description = 'Score'

    def rank(self, obj):
        return obj.rank