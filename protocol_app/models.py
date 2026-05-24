# protocol_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class MotivationQuote(models.Model):
    FONT_CHOICES = [
        ('serif',      'Serif / Calligraphy'),
        ('orbitron',   'Orbitron / Tech'),
        ('playfair',   'Playfair Display / Editorial'),
    ]
    text       = models.TextField()
    font_style = models.CharField(max_length=20, choices=FONT_CHOICES, default='playfair')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]

    class Meta:
        ordering = ['-created_at']


class DailyReport(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    date          = models.DateField(default=timezone.localdate)
    it_math_hours = models.FloatField(default=0.0, help_text="Target: 5 hours")
    pages_read    = models.IntegerField(default=0,  help_text="Target: 50 pages")
    calories      = models.IntegerField(default=0,  help_text="Calories burned")
    distance_km   = models.FloatField(default=0.0,  help_text="Distance in km")
    ai_comment    = models.TextField(blank=True, default='')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} | {self.date} | Score: {self.discipline_score:.1f}"

    # ── SCORING CONSTANTS ──────────────────────────────────────────────────────
    IT_TARGET       = 1.0    # hours
    PAGES_TARGET    = 50     # pages
    KCAL_TARGET     = 500    # calories
    KM_TARGET       = 5.0    # km

    IT_WEIGHT       = 0.40
    BOOKS_WEIGHT    = 0.20
    PHYSICAL_WEIGHT = 0.40

    @property
    def it_score_raw(self):
        """Score 0–10 for IT/Math hours."""
        raw = min(self.it_math_hours / self.IT_TARGET, 1.0) * 10
        # Penalty: if < 2h, score is halved
        if self.it_math_hours < 2.0 and self.it_math_hours > 0:
            raw *= 0.5
        return raw

    @property
    def books_score_raw(self):
        """Score 0–10 for pages read."""
        return min(self.pages_read / self.PAGES_TARGET, 1.0) * 10

    @property
    def physical_score_raw(self):
        """Combined score 0–10 for calories + distance."""
        kcal_score = min(self.calories / self.KCAL_TARGET, 1.0) * 10
        km_score   = min(self.distance_km / self.KM_TARGET, 1.0) * 10
        return (kcal_score + km_score) / 2

    @property
    def discipline_score(self):
        """
        Weighted score 0–10.
        RELENTLESS PENALTY: any metric at 0 → cap at 4.0.
        IT PENALTY: if IT < 2h → overall score penalized by -2 (floored at 0).
        """
        weighted = (
            self.it_score_raw    * self.IT_WEIGHT +
            self.books_score_raw * self.BOOKS_WEIGHT +
            self.physical_score_raw * self.PHYSICAL_WEIGHT
        )

        # Relentless Penalty
        any_zero = (
            self.it_math_hours == 0 or
            self.pages_read    == 0 or
            (self.calories == 0 and self.distance_km == 0)
        )
        if any_zero:
            weighted = min(weighted, 4.0)

        # IT under-2h macro penalty
        if self.it_math_hours < 2.0 and self.it_math_hours > 0:
            weighted = max(weighted - 2.0, 0.0)

        return round(min(weighted, 10.0), 2)

    @property
    def rank(self):
        """Returns rank label based on discipline_score."""
        s = self.discipline_score
        if s < 4.0:  return 'Beginner'
        if s < 6.0:  return 'Intermediate I'
        if s < 7.5:  return 'Intermediate II'
        if s < 9.0:  return 'Elite'
        return 'Master'
    
    # /* PATH: Models — Rank Icon SVG Property */
    @property
    def rank_icon_svg(self):
        """Returns a monochrome SVG string for the rank — no emojis."""
        base = 'stroke="#A0A0A0" stroke-width="1" fill="none"'
        icons = {
            'Beginner': f'''
                <svg width="48" height="48" viewBox="0 0 24 24" {base}
                     stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                  <line x1="9" y1="9" x2="9.01" y2="9"/>
                  <line x1="15" y1="9" x2="15.01" y2="9"/>
                </svg>''',
            'Intermediate I': f'''
                <svg width="48" height="48" viewBox="0 0 24 24" {base}
                     stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>''',
            'Intermediate II': f'''
                <svg width="48" height="48" viewBox="0 0 24 24" {base}
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>''',
            'Elite': f'''
                <svg width="48" height="48" viewBox="0 0 24 24" {base}
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>''',
            'Master': f'''
                <svg width="48" height="48" viewBox="0 0 24 24" {base}
                     stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="8" r="6"/>
                  <path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/>
                </svg>''',
        }
        return icons.get(self.rank, icons['Beginner'])

      

    @property
    def score_color_class(self):
        """CSS class for score color band."""
        s = self.discipline_score
        if s < 4.0:  return 'score-low'
        if s < 7.5:  return 'score-mid'
        return 'score-high'

    @property
    def it_progress_pct(self):
        return min(int((self.it_math_hours / self.IT_TARGET) * 100), 100)

    @property
    def books_progress_pct(self):
        return min(int((self.pages_read / self.PAGES_TARGET) * 100), 100)

    @property
    def kcal_progress_pct(self):
        return min(int((self.calories / self.KCAL_TARGET) * 100), 100)

    @property
    def km_progress_pct(self):
        return min(int((self.distance_km / self.KM_TARGET) * 100), 100)

    def generate_ai_comment(self):
        """
        Generates a sharp AI verdict sentence based on the day's stats.
        Called after save.
        """
        verdicts = []
        if self.it_math_hours >= self.IT_TARGET:
            verdicts.append("You dominated the machine today.")
        elif self.it_math_hours == 0:
            verdicts.append("The machine ran without you today.")
        else:
            verdicts.append(f"IT was weak at {self.it_math_hours}h — the Protocol demands {self.IT_TARGET}h.")

        if self.pages_read >= self.PAGES_TARGET:
            verdicts.append("Your mind is fed.")
        elif self.pages_read == 0:
            verdicts.append("A ghost in the library.")
        else:
            verdicts.append(f"Only {self.pages_read} pages — the Protocol demands more.")

        if self.calories >= self.KCAL_TARGET or self.distance_km >= self.KM_TARGET:
            verdicts.append("The body answered the call.")
        elif self.calories == 0 and self.distance_km == 0:
            verdicts.append("The body was a ghost today.")
        else:
            verdicts.append("The body showed up, but barely.")

        return " ".join(verdicts)

    def save(self, *args, **kwargs):
        if not self.ai_comment:
            self.ai_comment = self.generate_ai_comment()
        super().save(*args, **kwargs)