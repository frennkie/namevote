import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import gettext_lazy as _

from .models import Choice, Question


class SeLoginUserForm(forms.ModelForm):
    """
    Sign In / Enroll Login - User Form
    """

    username = forms.CharField(required=True, max_length=100, label=False,
                               widget=forms.TextInput(
                                   attrs={'placeholder': 'Username: e.g. anon12345',
                                          'class': 'form-control',
                                          'autofocus': 'autofocus'}))

    class Meta:
        model = User
        fields = ['username']


class SeLoginSignInForm(forms.Form):
    """
    Sign In / Enroll Login - Sign In Form
    """
    FORM_NAME = 'sign-in-form'

    username = forms.CharField(label=_("Username"), label_suffix="", required=True, max_length=100,
                               widget=forms.TextInput(attrs={'placeholder': 'e.g. anon12345'}))

    password = forms.CharField(label=_("Password"), label_suffix="", strip=False)

    next = forms.CharField(required=False, widget=forms.HiddenInput())
    form = forms.CharField(required=True, widget=forms.HiddenInput(), initial=FORM_NAME)


class SeLoginEnrollForm(forms.Form):
    """
    Sign In / Enroll Login - Enroll Form
    """
    FORM_NAME = 'enroll-form'

    username = forms.CharField(label=_("Username"), label_suffix="", required=False, widget=forms.HiddenInput())
    enrollment_code = forms.CharField(label=_("Code"), label_suffix="")

    next = forms.CharField(required=False, widget=forms.HiddenInput())
    form = forms.CharField(required=True, widget=forms.HiddenInput(), initial=FORM_NAME)

    def clean_enrollment_code(self):
        # remove duplicate spaces and strip space from start and end
        data = self.cleaned_data['enrollment_code']
        # PDPGN-8922-fnkcg
        no_hypen = data.replace('-', '')
        return "{}-{}-{}".format(no_hypen.replace('-', '')[0:5],  # PDPGN
                                 no_hypen.replace('-', '')[5:9],  # 8922
                                 no_hypen.replace('-', '')[9:14])  # fnkcg


class SeLoginSignInAuthenticationForm(AuthenticationForm):
    """
    Inherited
    """

    username = forms.HiddenInput()
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ['password']


class ChoiceForm(forms.ModelForm):
    choice_text = forms.CharField(required=True, max_length=100, label=False,
                                  widget=forms.TextInput(
                                      attrs={'placeholder': 'Enter Suggestion',
                                             'class': 'form-control',
                                             'autofocus': 'autofocus'}))

    class Meta:
        model = Choice
        fields = ['choice_text']

    def clean_choice_text(self):
        # remove duplicate spaces and strip space from start and end
        data = self.cleaned_data['choice_text']
        return re.sub(' +', ' ', data.strip())

    def clean(self):
        cleaned_data = super().clean()
        clean_choice_text = cleaned_data['choice_text']

        # check regex
        if self.instance.choice_validation_regex and \
                not re.compile(self.instance.choice_validation_regex).search(clean_choice_text):
            raise forms.ValidationError("Failed Regex. Hint: {}".format(self.instance.choice_validation_hint))

        # check duplicates
        try:
            self.instance.choice_set.get(choice_text=clean_choice_text)
            raise forms.ValidationError("Suggestion exists already - "
                                        "try something else: {}".format(clean_choice_text))
        except MultipleObjectsReturned:
            raise forms.ValidationError("Suggestion exists already (multiple times) - "
                                        "try something else: {}".format(clean_choice_text))
        except Choice.DoesNotExist:
            pass  # all good

        return cleaned_data


class ChoiceReviewForm(forms.ModelForm):
    class Meta:
        model = Choice

        fields = ['question', 'choice_text', 'review_status', 'review_remark']

    review_status = forms.ChoiceField(
        label='Review',
        choices=Choice.REVIEW_STATUS_CHOICES,
        initial=Choice.OPEN,
        widget=forms.RadioSelect,
    )


class VoteForm(forms.ModelForm):
    choice = forms.UUIDField(label=_("Choice"), label_suffix="", required=True)

    class Meta:
        model = Question
        fields = ['choice']

    def clean(self):
        cleaned_data = super().clean()
        clean_choice = cleaned_data['choice']

        # make sure this Choice exists for this Question
        try:
            self.instance.choice_set.get(pk=clean_choice)
        except Choice.DoesNotExist as err:
            raise forms.ValidationError("Not found: {} - {}".format(clean_choice, err))

        # check that user is has not yet used up all votes
        # if participation.votes_cast >= self.object.votes_per_session:

        return cleaned_data
