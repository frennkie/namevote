import re

from django.core.exceptions import MultipleObjectsReturned#
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic

from .models import Choice, Question
from .forms import ChoiceForm


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
        context = super(QuestionDetailView, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class EnterVoteView(generic.DetailView):
    model = Question
    template_name = 'open_choice_polls/question_enter_vote.html'
    query_pk_and_slug = True
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # check whether allowed votes (of cookie-based session) is exceeded
        num_votes_cast = get_session_num_votes_cast(self.request.session, self.object.id)
        if num_votes_cast >= self.object.votes_per_session:
            return redirect(reverse('open_choice_polls:results',
                                    kwargs={'slug': self.object.slug, 'id': self.object.id}))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Number of votes, as counted in the session variable.
        context['num_votes_cast'] = get_session_num_votes_cast(self.request.session, self.object.id)

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

        # Number of votes, as counted in the session variable.
        num_votes_cast = get_session_num_votes_cast(self.request.session, self.object.id)
        context['num_votes_cast'] = num_votes_cast

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


# ToDo where does this belong?
def get_session_num_votes_cast(session, obj_id):
    return session.get('question_{}_num_votes_cast'.format(obj_id), 0)


def set_session_num_votes_cast(session, obj_id, value):
    session['question_{}_num_votes_cast'.format(obj_id)] = value


def inc_session_num_votes_cast(session, obj_id):
    old_value = get_session_num_votes_cast(session, obj_id)
    session['question_{}_num_votes_cast'.format(obj_id)] = old_value + 1


def vote(request, id, slug=None, *args, **kwargs):
    question = get_object_or_404(Question, id=id)
    try:
        selected_choice = question.choice_set.get(id=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(request, 'open_choice_polls/question_enter_vote.html', {
            'choices_approved': Choice.approved.filter(question=question.id).order_by(Lower('choice_text')),
            'choices_open': Choice.open.filter(question=question.id).order_by(Lower('choice_text')),
            'choices_rejected': Choice.rejected.filter(question=question.id).order_by(Lower('choice_text')),
            'num_votes_cast': get_session_num_votes_cast(request.session, question.id),
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        # check whether allowed votes (of cookie-based session) is exceeded
        if get_session_num_votes_cast(request.session, question.id) >= question.votes_per_session:
            return render(request, 'open_choice_polls/question_results.html', {
                'choices_approved': Choice.approved.filter(question=question.id).order_by(Lower('choice_text')),
                'num_votes_cast': get_session_num_votes_cast(request.session, question.id),
                'question': question,
                'error_message': "Sorry - you have already used up all votes",
            })

        # only allow votes for approved choices
        if selected_choice.review_status == Choice.APPROVED:
            selected_choice.votes += 1
            selected_choice.save()

            # Increment number of votes, as counted in the session variable.
            inc_session_num_votes_cast(request.session, question.id)

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('open_choice_polls:results',
                                            kwargs={'slug': question.slug, 'id': question.id}))
