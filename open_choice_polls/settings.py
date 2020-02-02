from django.conf import settings

OPEN_CHOICE_POLLS_QUESTION_ZFILL = getattr(settings, 'OPEN_CHOICE_POLLS_QUESTION_ZFILL', 3)
