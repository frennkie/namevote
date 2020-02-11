import re

from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views import generic

from .forms import ChoiceForm, SeLoginUserForm, SeLoginSignInForm, SeLoginEnrollForm
from .models import Choice, Participation, Question, Voter


def selogin_user(request, *args, **kwargs):
    error_message = None

    if request.method == 'POST':
        next_ = request.POST.get('next')
        username = request.POST.get('username', None)
        if username:
            return redirect('open_choice_polls:se-login-username', username=username)
    else:
        next_ = request.GET.get('next')

    form = SeLoginUserForm(initial={'next': next_})
    form.is_valid()

    return render(request, 'open_choice_polls/voter_login_user.html', {
        'form': form,
        'error_message': error_message,
    })


def selogin(request, username=None, *args, **kwargs):
    error_message = None
    form_sign_in = None
    form_enroll = None

    if request.method == 'POST':
        next_ = request.POST.get('next')

        if request.POST.get('form') == SeLoginSignInForm.FORM_NAME:
            form_sign_in = SeLoginSignInForm(request.POST)
            form_sign_in.is_valid()

            if not username:
                username = form_sign_in.cleaned_data.get('username')
            password = form_sign_in.cleaned_data.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:

                if user.is_superuser:
                    login(request, user)
                    if next_:
                        return redirect(next_)
                    else:
                        return redirect('open_choice_polls:question-list')

                if user.voter.is_enrolled:
                    login(request, user)

                    if next_:
                        return redirect(next_)
                    else:
                        return redirect('open_choice_polls:question-list')
                else:
                    error_message = "Account is not yet enrolled. Please enroll first!"
                    form_enroll = SeLoginEnrollForm(initial={'username': username,
                                                             'next': next_})
                    form_sign_in = None

            else:
                error_message = "Sign in failed. Invalid username or password! Try another password again."

        elif request.POST.get('form') == SeLoginEnrollForm.FORM_NAME:
            print("enrollment...")

            form_enroll = SeLoginEnrollForm(request.POST)
            form_enroll.is_valid()

            enrollment_code = form_enroll.cleaned_data.get('enrollment_code')

            if not username:
                username = form_enroll.cleaned_data.get('username')

            if not username:
                print("looking up username from enrollment_code")

                voter_obj = Voter.objects.filter(is_voter=True). \
                    filter(enrollment_code=enrollment_code). \
                    first()

                if not voter_obj:
                    error_message = "not found"

                    return render(request, 'open_choice_polls/voter_login.html', {
                        'username': None,
                        'form_sign_in': SeLoginSignInForm(initial={'next': next_}),
                        'form_enroll': SeLoginEnrollForm(initial={'next': next_}),
                        'error_message': error_message,
                    })

                if voter_obj.is_enrolled:
                    error_message = "already enrolled"

                    return render(request, 'open_choice_polls/voter_login.html', {
                        'username': None,
                        'form_sign_in': SeLoginSignInForm(initial={'next': next_}),
                        'form_enroll': SeLoginEnrollForm(initial={'next': next_}),
                        'error_message': error_message,
                    })

                username = voter_obj.user.username

                # try to authenticate
                user = authenticate(username=username, password=enrollment_code)
                if user is not None:
                    new_pw = Voter.create_new_password()
                    user.voter.is_enrolled = True
                    user.set_password(new_pw)
                    user.save()
                    message = 'Enrollment successful of user: {}\n' \
                              'Password has been changed. If you close your browser or delete your ' \
                              'cookies then you will need the new password to re-enable your voting ' \
                              'privileges. The new password is: {}'.format(username, new_pw)

                    login(request, user)

                    return render(request, 'open_choice_polls/voter_detail.html', {
                        'message': message,
                        'successful_enrollment': True,
                    })
                else:
                    raise Exception("hm.. couldn't authenticate you.. this should have worked! :-/")

        else:
            raise Exception("form fu")

    else:
        next_ = request.GET.get('next')
        form_sign_in = SeLoginSignInForm(initial={'username': username, 'next': next_})
        form_enroll = SeLoginEnrollForm(initial={'username': username, 'next': next_})

    return render(request, 'open_choice_polls/voter_login.html', {
        'username': username,
        'form_sign_in': form_sign_in,
        'form_enroll': form_enroll,
        'error_message': error_message,

    })


class QuestionListView(generic.ListView):
    # template_name = 'open_choice_polls/question_list.html'
    model = Question
    context_object_name = 'questions'
    query_pk_and_slug = True

    def get_queryset(self):
        """Return the last 25 visible questions starting with oldest"""
        return Question.objects.filter(is_visible=True).order_by('created')[:25]

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class QuestionDetailView(generic.DetailView):
    # template_name = 'open_choice_polls/question_detail.html'
    model = Question
    query_pk_and_slug = True
    context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class VoterDetailView(generic.DetailView):
    template_name = 'open_choice_polls/voter_detail.html'
    model = Voter

    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        obj = get_object_or_404(User, username=self.kwargs.get('username'))

        # only owner can view his page
        if self.request.user.username == obj.username:
            return obj
        else:
            # redirect to 404 page
            raise Http404("Poll does not exist")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        qs = Participation.objects.filter(Q(voter__user__id=self.request.user.id) & Q(is_allowed=True)) \
            .order_by('question__number')
        context['participation_list'] = qs
        return context


class EnterVoteView(LoginRequiredMixin, generic.DetailView):
    model = Question
    template_name = 'open_choice_polls/question_enter_vote.html'
    query_pk_and_slug = True
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        qs = Participation.objects.filter(Q(voter__user__id=self.request.user.id) &
                                          Q(question__id=self.object.id) &
                                          Q(is_allowed=True))
        participation = qs.get()
        context['participation'] = participation

        if participation.votes_cast >= self.object.votes_per_session:
            return redirect(reverse('open_choice_polls:results',
                                    kwargs={'slug': self.object.slug, 'id': self.object.id}))

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        qs = Participation.objects.filter(Q(voter__user__id=self.request.user.id) &
                                          Q(question__id=self.object.id) &
                                          Q(is_allowed=True))
        participation = qs.get()
        context['participation'] = participation

        choices_approved = self.object.choice_set.filter(review_status=Choice.APPROVED).order_by(Lower('choice_text'))
        context['choices_approved'] = choices_approved
        return context


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'open_choice_polls/question_results.html'
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        qs = Participation.objects.filter(Q(voter__user__id=self.request.user.id) &
                                          Q(question__id=self.object.id))
        participation = qs.get()
        context['participation'] = participation

        choices_approved = self.object.choice_set.filter(review_status=Choice.APPROVED).order_by('-votes')
        context['choices_approved'] = choices_approved
        return context


class AddChoiceView(generic.DetailView):
    model = Question
    template_name = 'open_choice_polls/question_add_choice.html'
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        context['choices_approved'] = Choice.approved.filter(question=self.object.id).order_by(Lower('choice_text'))
        context['choices_open'] = Choice.open.filter(question=self.object.id).order_by(Lower('choice_text'))
        context['choices_rejected'] = Choice.rejected.filter(question=self.object.id).order_by(Lower('choice_text'))

        context['form'] = ChoiceForm

        return context


def add_choice(request, id, slug=None, *args, **kwargs):
    question = get_object_or_404(Question, id=id)

    form = ChoiceForm(request.POST)

    if not request.POST.get('choice_text', None):
        error_message = _("Choice is empty")
    else:
        form.is_valid()
        choice_text = form.cleaned_data.get('choice_text', None)

        if question.choice_validation_regex and not re.compile(question.choice_validation_regex).search(choice_text):
            error_message = _("Failed Regex. Hint: {}".format(question.choice_validation_hint))
        else:
            try:
                question.choice_set.get(choice_slug=slugify(choice_text))
            except (KeyError, Choice.DoesNotExist):
                question.choice_set.create(choice_text=choice_text, votes=0)
                # Always return an HttpResponseRedirect after successfully dealing
                # with POST data. This prevents data from being posted twice if a
                # user hits the Back button.
                return HttpResponseRedirect(reverse('open_choice_polls:choices',
                                                    kwargs={'slug': question.slug, 'id': question.id}))
            except MultipleObjectsReturned:
                error_message = " {} - this exists already (multiple times) - try something else".format(
                    choice_text)
            else:
                error_message = " {} - this exists already - try something else".format(choice_text)

    # Redisplay the question voting form.
    return render(request, 'open_choice_polls/question_add_choice.html', {
        'choices_approved': Choice.approved.filter(question=question.id).order_by(Lower('choice_text')),
        'choices_open': Choice.open.filter(question=question.id).order_by(Lower('choice_text')),
        'choices_rejected': Choice.rejected.filter(question=question.id).order_by(Lower('choice_text')),
        'question': question,
        'form': ChoiceForm,
        'error_message': error_message,
    })


def vote(request, id, slug=None, *args, **kwargs):
    question = get_object_or_404(Question, id=id)

    # try:

    qs = Participation.objects.filter(Q(voter__user__id=request.user.id) &
                                      Q(question__id=question.id))
    participation = qs.select_for_update().get()

    # except ObjectDoesNotExist:
    #     # ToDo(frennkie) what to do here?
    #     pass

    try:
        selected_choice = question.choice_set.get(id=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(request, 'open_choice_polls/question_enter_vote.html', {
            'choices_approved': Choice.approved.filter(question=question.id).order_by(Lower('choice_text')),
            'choices_open': Choice.open.filter(question=question.id).order_by(Lower('choice_text')),
            'choices_rejected': Choice.rejected.filter(question=question.id).order_by(Lower('choice_text')),
            'participation': participation,
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        # check whether allowed votes is exceeded
        if participation.votes_cast >= question.votes_per_session:
            return render(request, 'open_choice_polls/question_results.html', {
                'choices_approved': Choice.approved.filter(question=question.id).order_by(Lower('choice_text')),
                'participation': participation,
                'question': question,
                'error_message': "Sorry - you have already used up all votes",
            })

        # only allow votes for approved choices
        if selected_choice.review_status == Choice.APPROVED:
            with transaction.atomic():
                selected_choice.votes += 1
                selected_choice.save()
                selected_choice.refresh_from_db()

            with transaction.atomic():
                participation.votes_cast += 1
                participation.save()
                participation.refresh_from_db()

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('open_choice_polls:results',
                                            kwargs={'slug': question.slug, 'id': question.id}))
