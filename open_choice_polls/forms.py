import re
from django import forms

from .models import Choice


class ChoiceForm(forms.ModelForm):
    choice_text = forms.CharField(required=True, max_length=100, label=False,
                                  widget=forms.TextInput(
                                      attrs={'placeholder': 'Enter Suggestion',
                                             'class': 'mr-2',
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
