import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Choice


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
                               widget=forms.TextInput(
                                   attrs={'placeholder': 'e.g. anon12345'}))

    password = forms.CharField(label=_("Password"), label_suffix="", strip=False, widget=forms.PasswordInput)
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


class ChoiceReviewForm(forms.ModelForm):
    class Meta:
        model = Choice

        fields = ['question', 'choice_text', 'review_status', 'votes']

    review_status = forms.ChoiceField(
        label='Review',
        choices=Choice.REVIEW_STATUS_CHOICES,
        initial=Choice.OPEN,
        widget=forms.RadioSelect,
    )
