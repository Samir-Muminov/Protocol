# protocol_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# protocol_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


class MotivationQuote(models.Model):
    FONT_CHOICES = [
        ('serif',    'Serif / Calligraphy'),
        ('orbitron', 'Orbitron / Tech'),
        ('playfair', 'Playfair Display / Editorial'),
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
    it_math_hours = models.FloatField(default=0.0, help_text="Target: 1 hour")
    pages_read    = models.IntegerField(default=0,  help_text="Target: 50 pages")
    calories      = models.IntegerField(default=0,  help_text="Target: 500 kcal")
    distance_km   = models.FloatField(default=0.0,  help_text="Target: 5 km")
    ai_comment    = models.TextField(blank=True, default='')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} | {self.date} | Score: {self.discipline_score:.2f}"

    # ══════════════════════════════════════════════════════════════════
    # TARGETS & MAX POINTS PER CATEGORY
    # ══════════════════════════════════════════════════════════════════

    IT_TARGET       = 1.0     # hours
    PAGES_TARGET    = 50      # pages
    KCAL_TARGET     = 500     # calories
    KM_TARGET       = 5.0     # km

    # Maximum points each category can award
    IT_MAX_PTS      = 7.00
    BOOKS_MAX_PTS   = 5.25
    KCAL_MAX_PTS    = 5.25
    KM_MAX_PTS      = 5.25

    # Total maximum possible daily score
    MAX_DAILY_SCORE = 22.75   # 7 + 5.25 + 5.25 + 5.25

    # ══════════════════════════════════════════════════════════════════
    # 19-RANK SYSTEM
    # Ranks distributed evenly from 1.0 to MAX_DAILY_SCORE (22.75)
    # Each rank covers a band of (22.75 - 1.0) / 18 ≈ 1.208 points
    # Novice 1 starts at >= 1.0 pts
    # Protocolmaxxer requires >= 22.75 (perfect score)
    # ══════════════════════════════════════════════════════════════════

    RANK_THRESHOLDS = [
        # (min_score, rank_name, rank_slug)
        # slug is used as the static image filename: ranks/<slug>.png
        (0.00,  'Unranked',       'unranked'),
        (1.00,  'Novice I',       'novice_1'),
        (2.21,  'Novice II',      'novice_2'),
        (3.42,  'Novice III',     'novice_3'),
        (4.63,  'Novice IV',      'novice_4'),
        (5.84,  'Apprentice I',   'apprentice_1'),
        (7.04,  'Apprentice II',  'apprentice_2'),
        (8.25,  'Apprentice III', 'apprentice_3'),
        (9.46,  'Intermediate I', 'intermediate_1'),
        (10.67, 'Intermediate II','intermediate_2'),
        (11.88, 'Intermediate III','intermediate_3'),
        (13.08, 'Advanced I',     'advanced_1'),
        (14.29, 'Advanced II',    'advanced_2'),
        (15.50, 'Advanced III',   'advanced_3'),
        (16.71, 'Expert',         'expert'),
        (17.92, 'Expert Pro',     'expert_pro'),
        (19.13, 'Master',         'master'),
        (20.33, 'Grandmaster',    'grandmaster'),
        (21.54, 'Apex',           'apex'),
        (22.75, 'Protocolmaxxer', 'protocolmaxxer'),
    ]

    # ══════════════════════════════════════════════════════════════════
    # RAW CATEGORY SCORES (proportional, uncapped at target)
    # ══════════════════════════════════════════════════════════════════

    @property
    def it_points(self):
        """
        Proportional points for IT/Math.
        0.5h out of 1h target → 3.5 pts (50% of 7.0)
        Capped at IT_MAX_PTS — no bonus for going over target.
        """
        ratio = min(self.it_math_hours / self.IT_TARGET, 1.0)
        return round(ratio * self.IT_MAX_PTS, 4)

    @property
    def books_points(self):
        """Proportional points for pages read."""
        ratio = min(self.pages_read / self.PAGES_TARGET, 1.0)
        return round(ratio * self.BOOKS_MAX_PTS, 4)

    @property
    def kcal_points(self):
        """Proportional points for calories burned."""
        ratio = min(self.calories / self.KCAL_TARGET, 1.0)
        return round(ratio * self.KCAL_MAX_PTS, 4)

    @property
    def km_points(self):
        """Proportional points for distance covered."""
        ratio = min(self.distance_km / self.KM_TARGET, 1.0)
        return round(ratio * self.KM_MAX_PTS, 4)

    @property
    def discipline_score(self):
        """
        Total daily discipline score (0 – 22.75).

        RELENTLESS PENALTY: if ANY single metric is zero,
        the score is capped at the bottom of Novice II (2.20).
        This ensures a zero metric cannot push the user
        above the lowest real rank.
        """
        raw = (
            self.it_points    +
            self.books_points +
            self.kcal_points  +
            self.km_points
        )

        # Relentless Penalty
        any_zero = (
            self.it_math_hours == 0 or
            self.pages_read    == 0 or
            self.calories      == 0 or
            self.distance_km   == 0
        )
        if any_zero:
            raw = min(raw, 2.20)

        return round(min(raw, self.MAX_DAILY_SCORE), 4)

    # ══════════════════════════════════════════════════════════════════
    # RANK RESOLUTION
    # ══════════════════════════════════════════════════════════════════

    @property
    def rank_data(self):
        """
        Returns the full rank tuple for the current discipline_score.
        Iterates thresholds in reverse — highest match wins.
        """
        score = self.discipline_score
        result = self.RANK_THRESHOLDS[0]   # default: Unranked
        for threshold, name, slug in self.RANK_THRESHOLDS:
            if score >= threshold:
                result = (threshold, name, slug)
        return result

    @property
    def rank(self):
        return self.rank_data[1]

    @property
    def rank_slug(self):
        """
        Slug used to find the rank image.
        Image path: /static/protocol_app/ranks/<slug>.png
        Drop your PNG files into that folder with these exact names.
        """
        return self.rank_data[2]

    @property
    def rank_image_url(self):
        """
        Returns the static URL for the rank image.
        Falls back to a placeholder SVG path if image not found.
        Expected files: protocol_app/static/protocol_app/ranks/<slug>.png
        """
        return f'/static/protocol_app/ranks/{self.rank_slug}.png'

    @property
    def next_rank_data(self):
        """Returns the next rank above current, or None if at max."""
        score = self.discipline_score
        for threshold, name, slug in self.RANK_THRESHOLDS:
            if threshold > score:
                return (threshold, name, slug)
        return None

    @property
    def rank_progress_pct(self):
        """
        Percentage progress toward the NEXT rank (for the rank progress bar).
        Returns 100 if at max rank.
        """
        score    = self.discipline_score
        current  = self.rank_data
        next_r   = self.next_rank_data

        if next_r is None:
            return 100

        current_min  = current[0]
        next_min     = next_r[0]
        band         = next_min - current_min

        if band <= 0:
            return 100

        progress = (score - current_min) / band
        return round(min(progress * 100, 100), 1)

    # ══════════════════════════════════════════════════════════════════
    # SCORE COLOR CLASS (for CSS theming)
    # ══════════════════════════════════════════════════════════════════

    @property
    def score_color_class(self):
        s = self.discipline_score
        if s < 5.84:   return 'score-low'    # Unranked → Novice IV
        if s < 13.08:  return 'score-mid'    # Apprentice I → Intermediate III
        if s < 19.13:  return 'score-high'   # Advanced I → Master
        return 'score-elite'                  # Grandmaster → Protocolmaxxer

    # ══════════════════════════════════════════════════════════════════
    # PROGRESS PERCENTAGES (for mini bars, 0–100)
    # ══════════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════════
    # AI VERDICT
    # ══════════════════════════════════════════════════════════════════

    def generate_ai_comment(self):
        verdicts = []

        # IT
        if self.it_math_hours >= self.IT_TARGET:
            verdicts.append("Machine mastery achieved today.")
        elif self.it_math_hours == 0:
            verdicts.append("Zero hours logged — the machine ran without you.")
        else:
            pct = int((self.it_math_hours / self.IT_TARGET) * 100)
            verdicts.append(f"IT at {pct}% of target. Acceptable, not elite.")

        # Books
        if self.pages_read >= self.PAGES_TARGET:
            verdicts.append("The mind is fed and sharp.")
        elif self.pages_read == 0:
            verdicts.append("A ghost in the library today.")
        else:
            verdicts.append(f"{self.pages_read} pages — the Protocol demands 50.")

        # Physical
        if self.calories >= self.KCAL_TARGET and self.distance_km >= self.KM_TARGET:
            verdicts.append("The body answered every call.")
        elif self.calories == 0 and self.distance_km == 0:
            verdicts.append("The body was dormant. Unacceptable.")
        elif self.calories >= self.KCAL_TARGET:
            verdicts.append(f"Burn was solid. Distance was light at {self.distance_km}km.")
        elif self.distance_km >= self.KM_TARGET:
            verdicts.append(f"Distance locked in. Burn was low at {self.calories}kcal.")
        else:
            verdicts.append("Physical output was partial. Push harder tomorrow.")

        # Score verdict
        s = self.discipline_score
        if s >= 20:
            verdicts.append("PROTOCOLMAXXER territory. You are the standard.")
        elif s >= 16:
            verdicts.append("Elite execution. The Protocol is proud.")
        elif s >= 10:
            verdicts.append("Solid. Not your ceiling — keep climbing.")
        elif s >= 5:
            verdicts.append("Below mid. The Protocol has higher expectations.")
        else:
            verdicts.append("Restart. Tomorrow is a new execution window.")

        return " ".join(verdicts)

    def save(self, *args, **kwargs):
        # Regenerate AI comment on every save so it reflects latest data
        self.ai_comment = self.generate_ai_comment()
        super().save(*args, **kwargs)