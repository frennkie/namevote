import re
from django import forms
from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import gettext_lazy as _

from .models import Choice, Question


class SignInForm(forms.Form):
    username = forms.CharField(label=_("Username"), label_suffix="", required=True, max_length=100)
    password = forms.CharField(label=_("Password"), label_suffix="", strip=False)
    next = forms.CharField(required=False, widget=forms.HiddenInput())


class EnrollForm(forms.Form):
    enrollment_code = forms.CharField(label=_("Code"), label_suffix="")
    next = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_enrollment_code(self):
        # the hyphens are optional - so both will work: PDPGN-8922-fnkcg and PDPGN8922fnkcg
        data = self.cleaned_data['enrollment_code']
        data_no_hyphen = data.replace('-', '')
        return "{}-{}-{}".format(data_no_hyphen[0:5],  # PDPGN
                                 data_no_hyphen[5:9],  # 8922
                                 data_no_hyphen[9:14])  # fnkcg


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

        return cleaned_data
