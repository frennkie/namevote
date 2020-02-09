import re
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

SELECTED_LETTERS = 'ABCDEFGHKMNPQRSTUVWX'
SELECTED_NUMBERS = '23456789'


class Voter(models.Model):
    class Meta:
        ordering = ('user',)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    is_voter = models.BooleanField(default=False, editable=False,
                                   verbose_name=_('Is Voter?'))
    is_enrolled = models.BooleanField(default=False, editable=True,
                                      verbose_name=_('Is Enrolled?'))

    enrollment_code = models.CharField(max_length=80, blank=True, editable=False,
                                       verbose_name=_('Enrollment Code'))

    @staticmethod
    def create_enrollment_code():
        first = get_random_string(2, SELECTED_LETTERS)
        second = get_random_string(3, SELECTED_NUMBERS)
        third = get_random_string(2, SELECTED_LETTERS.lower())
        return "{}{}{}".format(first, second, third)

    @staticmethod
    def create_new_password():
        first = get_random_string(4, SELECTED_LETTERS)
        second = get_random_string(5, SELECTED_NUMBERS)
        third = get_random_string(4, SELECTED_LETTERS.lower())
        return "{}-{}-{}".format(first, second, third)

    def __repr__(self):
        return "<{0}: {1}>".format(
            self.__class__.__name__,
            self.user.username)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Voter.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not instance.id == 1:
        instance.voter.save()


class Question(models.Model):
    class Meta:
        ordering = ('-created',)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # incrementing unique numeric identifier (e.g. used for "Q034...")
    number = models.IntegerField(default=0, editable=False)

    text = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, editable=False)

    choice_validation_regex = models.CharField(max_length=200, blank=True)
    choice_validation_hint = models.CharField(max_length=200, blank=True)

    description = models.TextField(verbose_name=_('Description (with basic markdown support)'), blank=True)

    created = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)

    collection_start_date = models.DateTimeField(verbose_name=_('Start Collection Phase'),
                                                 blank=True, default=timezone.now)
    collection_end_date = models.DateTimeField(verbose_name=_('End Collection Phase'),
                                               blank=True, default=timezone.now)

    voting_start_date = models.DateTimeField(verbose_name=_('Start Voting Phase'),
                                             blank=True, default=timezone.now)
    voting_end_date = models.DateTimeField(verbose_name=_('End Voting Phase'),
                                           blank=True, default=timezone.now)

    is_visible = models.BooleanField(verbose_name=_('is visible'), default=True)

    show_choices_approved = models.BooleanField(verbose_name=_('show approved choices'), default=True)
    show_choices_open = models.BooleanField(verbose_name=_('show unchecked choices'), default=True)
    show_choices_rejected = models.BooleanField(verbose_name=_('show rejected choices'), default=True)

    show_voting_results = models.BooleanField(verbose_name=_('show voting results before vote ends'), default=True)

    votes_per_session = models.PositiveSmallIntegerField(verbose_name=_('number of votes allowed '
                                                                        'per (cookie-based session)'), default=5)

    voter_participation = models.ManyToManyField(Voter, through='Participation')

    def get_absolute_url(self):
        return reverse('open_choice_polls:question-detail', kwargs={'slug': self.slug, 'id': self.id})

    def collection_is_active(self):
        now = timezone.now()
        try:
            return self.collection_start_date <= now <= self.collection_end_date
        except TypeError:
            return False

    collection_is_active.boolean = True
    collection_is_active.short_description = _('Collection is active?')

    def collection_is_in_past(self):
        now = timezone.now()
        return self.collection_start_date < now and self.collection_end_date < now

    collection_is_in_past.boolean = True
    collection_is_in_past.short_description = _('Collection is in past?')

    def collection_is_in_future(self):
        now = timezone.now()
        return now < self.collection_start_date and now < self.collection_end_date

    collection_is_in_future.boolean = True
    collection_is_in_future.short_description = _('Collection is in future?')

    def collection_duration(self):
        return self.collection_end_date - self.collection_start_date

    collection_duration.short_description = _('Collection duration')

    def voting_is_active(self):
        now = timezone.now()
        try:
            return self.voting_start_date <= now <= self.voting_end_date
        except TypeError:
            return False

    voting_is_active.boolean = True
    voting_is_active.short_description = _('Voting is active?')

    def voting_is_in_past(self):
        now = timezone.now()
        return self.voting_start_date < now and self.voting_end_date < now

    voting_is_in_past.boolean = True
    voting_is_in_past.short_description = _('Voting is in past?')

    def voting_is_in_future(self):
        now = timezone.now()
        return now < self.voting_start_date and now < self.voting_end_date

    voting_is_in_future.boolean = True
    voting_is_in_future.short_description = _('Voting is in future?')

    def voting_duration(self):
        return self.voting_end_date - self.voting_start_date

    voting_duration.short_description = _('Voting duration')

    @property
    def number_zfill(self):
        return "Q{}".format(str(self.number).zfill(3))

    @property
    def number_text(self):
        return "{0} {1}".format(self.number_zfill, self.text)

    @property
    def total_choices(self):
        return self.choice_set.count()

    @property
    def total_approved_choices(self):
        return self.choice_set.filter(review_status=Choice.APPROVED).count()

    @property
    def total_votes(self):
        total = 0
        for choice in Choice.approved.filter(question=self.id):
            total += choice.votes
        return total

    def __repr__(self):
        return "<{0}: {1}".format(
            self.__class__.__name__,
            self.number_text)

    def __str__(self):
        return self.number_text

    def clean(self):
        if self.choice_validation_regex:
            try:
                re.compile(self.choice_validation_regex)
            except re.error:
                raise ValidationError("invalid regex for choice validation")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.text)

        # This means that the model isn't saved to the database yet
        if self._state.adding:
            # Get the maximum display_id value from the database
            last_number = Question.objects.all().aggregate(largest=models.Max('number'))['largest']
            if last_number is None:
                last_number = 0

            # aggregate can return None! Check it first.
            # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
            if last_number is not None:
                self.number = last_number + 1

        super(Question, self).save(*args, **kwargs)


class Participation(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_allowed = models.BooleanField(default=False, help_text=_('Is participation (vote) allowed?'))
    votes_cast = models.PositiveIntegerField(default=0, help_text=_('Number of votes cast no Question'))

    def __repr__(self):
        return "<{}: {} {} {} ({})>".format(
            self.__class__.__name__,
            self.question.number_zfill,
            self.voter.user.username,
            self.is_allowed,
            self.votes_cast)

    def __str__(self):
        return "{}_<{}>".format(self.voter.user.username, self.question.number_text)


class ApprovedChoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=Choice.APPROVED)


class OpenChoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=Choice.OPEN)


class RejectedChoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=Choice.REJECTED)


class Choice(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    choice_text = models.CharField(max_length=200)
    choice_slug = models.SlugField(blank=True, editable=False)

    votes = models.IntegerField(default=0)

    APPROVED = 'APPROVED'
    OPEN = 'OPEN'
    REJECTED = 'REJECTED'
    REVIEW_STATUS_CHOICES = (
        (APPROVED, mark_safe('&#10004; ({})'.format(_('approved')))),
        (OPEN, mark_safe('&#63; ({})'.format(_('not yet reviewed')))),
        (REJECTED, mark_safe('&#10005; ({})'.format(_('rejected')))),
    )
    review_status = models.CharField(verbose_name=_("review status"), max_length=8,
                                     choices=REVIEW_STATUS_CHOICES, default=OPEN)

    review_remark = models.CharField(max_length=200, blank=True)

    # Managers
    objects = models.Manager()  # default
    approved = ApprovedChoiceManager()
    open = OpenChoiceManager()
    rejected = RejectedChoiceManager()

    def __str__(self):
        return self.choice_text

    def __repr__(self):
        return "<{0}: {1}>".format(
            self.__class__.__name__,
            self.choice_text)

    def save(self, *args, **kwargs):
        if not self.choice_slug:
            self.choice_slug = slugify(self.choice_text)

        super(Choice, self).save(*args, **kwargs)
