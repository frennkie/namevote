import random
import re
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from open_choice_polls import settings

SELECTED_LETTERS = 'ABCDEFGHKMNPQRSTUVWX'
SELECTED_NUMBERS = '23456789'


class ActiveVoterManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(Q(is_voter=True) & Q(is_enrolled=True))


class Voter(models.Model):
    # DATABASE FIELDS
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    is_voter = models.BooleanField(default=False, editable=False,
                                   verbose_name=_('Is Voter?'))
    is_enrolled = models.BooleanField(default=False, editable=True,
                                      verbose_name=_('Is Enrolled?'))

    enrollment_code = models.CharField(max_length=80, blank=True, editable=False,
                                       verbose_name=_('Enrollment Code'))

    enrollment_code_is_distributed = models.BooleanField(default=False, editable=True,
                                                         verbose_name=_('Is Distributed?'))

    enrollment_code_valid_until = models.DateTimeField(verbose_name=_('Enrollment Code valid until'),
                                                       blank=True, null=True,
                                                       help_text=_("Leave empty for codes that never expire"))

    # MANAGERS
    objects = models.Manager()  # default
    active = ActiveVoterManager()

    # META CLASS
    class Meta:
        ordering = ('user',)

    # REPR and TO STRING METHOD
    def __repr__(self):
        return "<{0}: {1}>".format(
            self.__class__.__name__,
            self.user.username)

    def __str__(self):
        return self.user.username

    # ABSOLUTE URL METHOD
    def get_absolute_url(self):
        return reverse('open_choice_polls:voter-detail', kwargs={'username': self.user})

    @staticmethod
    def create_enrollment_code():
        first = get_random_string(5, SELECTED_LETTERS)
        second = get_random_string(4, SELECTED_NUMBERS)
        third = get_random_string(5, SELECTED_LETTERS.lower())
        return "{}-{}-{}".format(first, second, third)

    @staticmethod
    def create_new_password():
        first = get_random_string(4, SELECTED_LETTERS)
        second = get_random_string(3, SELECTED_NUMBERS)
        third = get_random_string(4, SELECTED_LETTERS.lower())
        return "{}-{}-{}".format(first, second, third)

    @classmethod
    def create_voter(cls, amount=1, code_valid_timedelta_days=None, question_id=None):
        if amount < 1:
            raise NotImplementedError("create at least 1 Voter!")

        prefix = settings.OPEN_CHOICE_POLLS_VOTER_PREFIX

        ids_rand = random.sample(range(settings.OPEN_CHOICE_POLLS_VOTER_RANGE_START,
                                       settings.OPEN_CHOICE_POLLS_VOTER_RANGE_END), amount)

        res = []
        for i in ids_rand:
            # Create user and save to the database
            voter_username = '{}{}'.format(prefix, str(i).zfill(3))
            try:
                enrollment_code = Voter.create_enrollment_code()
                user = User.objects.create_user(voter_username, password=enrollment_code)

                user.voter.is_voter = True
                user.voter.enrollment_code = enrollment_code
                if code_valid_timedelta_days:
                    user.voter.enrollment_code_valid_until = timezone.now() + timedelta(days=code_valid_timedelta_days)

                if question_id:
                    try:
                        question = Question.objects.get(pk=question_id)
                        user.voter.participation_set.create(voter=user.voter, question=question, is_allowed=True)
                    except Question.DoesNotExist:
                        pass
                user.save()

                res.append(user)
            except IntegrityError:
                break
        return res


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Voter.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.voter.save()
    except Voter.DoesNotExist:
        pass


@receiver(post_delete, sender=Voter)
def post_delete_user(sender, instance, *args, **kwargs):
    if instance.user:  # just in case user is not specified
        instance.user.delete()


class Question(models.Model):
    # DATABASE FIELDS
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

    # MANAGERS
    objects = models.Manager()  # default

    # META CLASS
    class Meta:
        ordering = ('-created',)
        get_latest_by = 'created'

    # REPR and TO STRING METHOD
    def __repr__(self):
        return "<{0}: {1}>".format(
            self.__class__.__name__,
            self.number_text)

    def __str__(self):
        return self.number_text

    # SAVE METHOD
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

        super().save(*args, **kwargs)

    # ABSOLUTE URL METHOD
    def get_absolute_url(self):
        return reverse('open_choice_polls:question-detail', kwargs={'slug': self.slug, 'id': self.id})

    def clean(self):
        if self.choice_validation_regex:
            try:
                re.compile(self.choice_validation_regex)
            except re.error:
                raise ValidationError("invalid regex for choice validation")

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


class Participation(models.Model):
    # DATABASE FIELDS
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_allowed = models.BooleanField(default=False, help_text=_('Is participation (vote) allowed?'))
    votes_cast = models.PositiveIntegerField(default=0, help_text=_('Number of votes cast no Question'))

    # REPR and TO STRING METHOD
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
    # CHOICES
    APPROVED = 'APPROVED'
    OPEN = 'OPEN'
    REJECTED = 'REJECTED'
    REVIEW_STATUS_CHOICES = (
        (APPROVED, mark_safe('&#10004; ({})'.format(_('approved')))),
        (OPEN, mark_safe('&#63; ({})'.format(_('not yet reviewed')))),
        (REJECTED, mark_safe('&#10005; ({})'.format(_('rejected')))),
    )

    # DATABASE FIELDS
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    choice_text = models.CharField(max_length=200)
    choice_slug = models.SlugField(blank=True, editable=False)

    votes = models.IntegerField(default=0)

    review_status = models.CharField(verbose_name=_("review status"), max_length=8,
                                     choices=REVIEW_STATUS_CHOICES, default=OPEN)

    review_remark = models.CharField(max_length=200, blank=True)

    # MANAGERS
    objects = models.Manager()  # default
    approved = ApprovedChoiceManager()
    open = OpenChoiceManager()
    rejected = RejectedChoiceManager()

    # META CLASS
    class Meta:
        verbose_name = 'choice'
        verbose_name_plural = 'choices'
        ordering = [Lower('choice_text')]

    # REPR and TO STRING METHOD
    def __repr__(self):
        return "<{0}: {1}>".format(
            self.__class__.__name__,
            self.choice_text)

    def __str__(self):
        return self.choice_text
