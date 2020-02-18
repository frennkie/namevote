from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .forms import ChoiceReviewForm
from .models import Choice, Question, Voter, Participation


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3

    readonly_fields = ('votes',)


class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 1

    readonly_fields = ('votes_cast',)


class VoterInline(admin.StackedInline):
    model = Voter
    can_delete = False
    verbose_name_plural = "voter"

    readonly_fields = ('is_voter', 'enrollment_code',)


class ChoiceAdmin(admin.ModelAdmin):
    form = ChoiceReviewForm

    list_display = ('choice_text', 'choice_slug', 'question_text', 'review_status', 'votes')
    list_filter = ('question__text', 'question__number', 'review_status',)

    def question_text(self, obj):
        redirect_url = reverse('admin:open_choice_polls_question_change', args=(obj.question.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.question.text))

    readonly_fields = ('choice_slug', 'votes',)

    actions = ["approve", "reject", "reset_review_status", "reset_votes"]

    def approve(self, request, queryset):
        rows_updated = queryset.update(review_status=Choice.APPROVED)
        if rows_updated == 1:
            message_bit = "1 choice was"
        else:
            message_bit = "%s choices were" % rows_updated
        self.message_user(request, "%s successfully approved." % message_bit)

    approve.short_description = _("Review Status: Approve")

    def reject(self, request, queryset):
        rows_updated = queryset.update(review_status=Choice.REJECTED)
        if rows_updated == 1:
            message_bit = "1 choice was"
        else:
            message_bit = "%s choices were" % rows_updated
        self.message_user(request, "%s successfully rejected." % message_bit)

    reject.short_description = _("Review Status: Reject")

    def reset_review_status(self, request, queryset):
        rows_updated = queryset.update(review_status=Choice.OPEN)
        if rows_updated == 1:
            message_bit = "Review status of 1 choice was"
        else:
            message_bit = "Review status of %s choices were" % rows_updated
        self.message_user(request, "%s successfully reset." % message_bit)

    reset_review_status.short_description = _("Review Status: Reset")

    def reset_votes(self, request, queryset):
        rows_updated = queryset.update(votes=0)
        if rows_updated == 1:
            message_bit = "Votes of 1 choice was"
        else:
            message_bit = "Votes of %s choices were" % rows_updated
        self.message_user(request, "%s successfully reset." % message_bit)

    reset_votes.short_description = _("Votes: Reset to 0")


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'number', 'created', 'is_visible',
                    'collection_is_active', 'voting_is_active', 'total_votes', 'allowed_voters')
    list_filter = ['created', 'is_visible']
    search_fields = ['text']

    fieldsets = [
        (None, {'fields': ['number',
                           'slug',
                           'text']}),
        ('Main Settings', {'fields': ['is_visible',
                                      'description',
                                      'votes_per_session',
                                      'show_choices_approved',
                                      'show_choices_open',
                                      'show_choices_rejected',
                                      'show_voting_results']}),
        ('Choice Validation', {'fields': ['choice_validation_regex',
                                          'choice_validation_hint'],
                               'classes': ['collapse']}),
        ('Dates', {'fields': ['created',
                              'collection_start_date',
                              'collection_end_date',
                              'voting_start_date',
                              'voting_end_date'],
                   'classes': ['collapse']}),
        ('Status', {'fields': ['collection_is_active',
                               'collection_is_in_past',
                               'collection_is_in_future',
                               'collection_duration',
                               'voting_is_active',
                               'voting_is_in_past',
                               'voting_is_in_future',
                               'voting_duration',
                               'total_choices',
                               'total_approved_choices',
                               'total_votes'
                               'allowed_voters',],
                    'classes': ['collapse']}),
    ]
    readonly_fields = ('number', 'slug', 'created',
                       'collection_is_active', 'collection_is_in_past', 'collection_is_in_future',
                       'collection_duration',
                       'voting_is_active', 'voting_is_in_past', 'voting_is_in_future',
                       'voting_duration',
                       'total_choices', 'total_approved_choices',
                       'total_votes',
                       'allowed_voters')

    actions = ['generate_1_voter', 'generate_3_voter', 'generate_25_voter']

    # inlines = (ChoiceInline, ParticipationInline,)
    inlines = (ChoiceInline,)

    def save_model(self, request, obj, form, change):
        if obj.collection_end_date <= obj.collection_start_date:
            messages.add_message(request, messages.WARNING,
                                 'Collection Start date must be before End date! Question: “{}“'.format(obj.text))
        if obj.voting_end_date <= obj.voting_start_date:
            messages.add_message(request, messages.WARNING,
                                 'Voting Start date must be before End date! Question: “{}“'.format(obj.text))
        if obj.voting_start_date <= obj.collection_end_date:
            messages.add_message(request, messages.WARNING,
                                 'Collection End date should be before Voting Start date! Question: “{}“'.format(
                                     obj.text))
        super(QuestionAdmin, self).save_model(request, obj, form, change)

    def generate_n_voter(self, request, queryset, n=1, days=30):
        user_objs = Voter.create_voter(n, 30)
        if user_objs:
            usernames = [x.username for x in user_objs]
            if n == 1:
                self.message_user(request, "successfully generated 1 user: {}".format(n))
            elif n <= 3:
                self.message_user(request, "successfully generated {} users: {}".format(len(usernames),
                                                                                        ",".join(usernames)))
            else:
                self.message_user(request, "successfully generated {} user(s)".format(n))
            for idx, user_obj in enumerate(user_objs):
                for q in queryset.all():
                    Participation.objects.create(voter=user_obj.voter, question=q, is_allowed=True)
                    if idx == len(user_objs) - 1:
                        self.message_user(request, "added new user(s) to: {}".format(q))

    def generate_1_voter(self, request, queryset):
        self.generate_n_voter(request, queryset)

    generate_1_voter.short_description = _("Create 1 Voter and assign to selected Questions")

    def generate_3_voter(self, request, queryset):
        self.generate_n_voter(request, queryset, 3)

    generate_3_voter.short_description = _("Create 3 Voters and assign to selected Questions")

    def generate_25_voter(self, request, queryset):
        self.generate_n_voter(request, queryset, 25)

    generate_25_voter.short_description = _("Create 25 Voters and assign to selected Questions")


class UserAdmin(BaseUserAdmin):
    inlines = (VoterInline,)


class VoterAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enrolled', 'enrollment_code_is_distributed', 'enrollment_code',)
    list_filter = ('is_enrolled', 'enrollment_code_is_distributed')
    search_fields = ['user__username', 'enrollment_code']

    readonly_fields = ('user', 'is_voter', 'enrollment_code',)

    fieldsets = [
        (None, {'fields': ['user',
                           'is_voter',
                           'is_enrolled',
                           'enrollment_code',
                           'enrollment_code_is_distributed',
                           'enrollment_code_valid_until']}),
    ]

    actions = ["export_codes_for_print", "export_codes_for_email"]

    # def get_actions(self, request):
    #     actions = super().get_actions(request)
    #     # if 'delete_selected' in actions:
    #         # del actions['delete_selected']
    #     return actions

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_voter=True)

    def export_codes_for_print(self, request, queryset):
        _ = queryset.update(enrollment_code_is_distributed=True)
        response = TemplateResponse(request, 'open_choice_polls/admin_voter_export_print.html', {'entries': queryset})
        return response

    export_codes_for_print.short_description = _("Export selected Voters for printing and set distributed")

    def export_codes_for_email(self, request, queryset):
        _ = queryset.update(enrollment_code_is_distributed=True)
        response = TemplateResponse(request, 'open_choice_polls/admin_voter_export_email.html', {'entries': queryset})
        return response

    export_codes_for_email.short_description = _("Export selected Voters for emailing and set distributed")

    inlines = (ParticipationInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register other models
admin.site.register(Voter, VoterAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
