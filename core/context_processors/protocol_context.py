# core/context_processors/protocol_context.py
import random

def protocol_quote(request):
    """
    Injects a random active MotivationQuote into every template context.
    Safely handles the case where no quotes exist yet.
    """
    try:
        from protocol_app.models import MotivationQuote
        quotes = list(MotivationQuote.objects.filter(is_active=True))
        quote = random.choice(quotes) if quotes else None
    except Exception:
        quote = None
    return {'global_quote': quote}