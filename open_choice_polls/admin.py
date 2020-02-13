from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .forms import ChoiceReviewForm
from .models import Choice, Question, Voter, Participation


class VoterInline(admin.StackedInline):
    model = Voter
    can_delete = False
    verbose_name_plural = "voter"

    readonly_fields = ('is_voter', 'enrollment_code',)


class UserAdmin(BaseUserAdmin):
    inlines = (VoterInline, )


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 1

    # def get_queryset(self, request):
    #     qs = super(ParticipationInline, self).get_queryset(request)
    #     return qs.filter(voter.is_voter=True)


class VoterAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_voter', 'is_enrolled', 'enrollment_code')
    list_filter = ('is_voter', 'is_enrolled',)
    search_fields = ['user__username']

    # readonly_fields = ('user', 'is_voter', 'is_enrolled', 'enrollment_code',)
    readonly_fields = ('user', 'is_voter', 'enrollment_code',)

    fieldsets = [
        (None, {'fields': ['user',
                           'is_voter',
                           'is_enrolled',
                           'enrollment_code',
                           'enrollment_code_valid_until']}),
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    actions = ["export_codes_to_html", "generate_1_voter", 'generate_25_voter']

    def export_codes_to_html(self, request, queryset):
        # rows_updated = queryset.update(is_distributed=True)
        # _ = queryset.update(distribution_type=DownloadCode.PRINTED)
        response = TemplateResponse(request, 'open_choice_polls/admin_voter_export.html', {'entries': queryset})
        return response

    export_codes_to_html.short_description = _("Export selected Voters to HTML")

    # ToDo(frennkie) this requires admin to select (any) existing voter
    def generate_1_voter(self, request, queryset):
        res = Voter.create_voter(1, 30)
        if res:
            user_obj = res[0]
            self.message_user(request, "successfully generated 1 user: {}".format(user_obj))

    generate_1_voter.short_description = _("Create 1 Voter")

    # ToDo(frennkie) this requires admin to select (any) existing voter
    def generate_25_voter(self, request, queryset):
        res = Voter.create_voter(25, 30)
        if res:
            user_objs = [x.username for x in res]
            lst = ",".join(user_objs)
            self.message_user(request, "successfully generated 25 user: {}".format(lst))

    generate_25_voter.short_description = _("Create 25 Voters")

    inlines = (ParticipationInline, )


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'number', 'created', 'is_visible', 'collection_is_active', 'voting_is_active')
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
                               'total_approved_choices'],
                    'classes': ['collapse']}),
    ]
    readonly_fields = ('number', 'slug', 'created',
                       'collection_is_active', 'collection_is_in_past', 'collection_is_in_future',
                       'collection_duration',
                       'voting_is_active', 'voting_is_in_past', 'voting_is_in_future',
                       'voting_duration',
                       'total_choices', 'total_approved_choices')

    inlines = (ChoiceInline, ParticipationInline,)

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


class ChoiceAdmin(admin.ModelAdmin):
    form = ChoiceReviewForm

    list_display = ('choice_text', 'choice_slug', 'question_text', 'review_status', 'votes')
    list_filter = ('question__text', 'question__number', 'review_status',)

    def question_text(self, obj):
        redirect_url = reverse('admin:open_choice_polls_question_change', args=(obj.question.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.question.text))

    readonly_fields = ('choice_slug',)

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


# ToDo only needed in DEV
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()

    list_display = ('session_key', '_session_data', 'expire_date')


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register other models
admin.site.register(Voter, VoterAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
