import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Choice


# class AuthenticationForm(forms.Form):
#     """
#     Base class for authenticating users. Extend this to get a form that accepts
#     username/password logins.
#     """
#     username = UsernameField(widget=forms.TextInput(attrs={'autofocus': True}))
#     password = forms.CharField(
#         label=_("Password"),
#         strip=False,
#         widget=forms.PasswordInput,
#     )
#
#     error_messages = {
#         'invalid_login': _(
#             "Please enter a correct %(username)s and password. Note that both "
#             "fields may be case-sensitive."
#         ),
#         'inactive': _("This account is inactive."),
#     }
#
#     def __init__(self, request=None, *args, **kwargs):
#         """
#         The 'request' parameter is set for custom auth use by subclasses.
#         The form data comes in via the standard 'data' kwarg.
#         """
#         self.request = request
#         self.user_cache = None
#         super().__init__(*args, **kwargs)
#
#         # Set the max length and label for the "username" field.
#         self.username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
#         self.fields['username'].max_length = self.username_field.max_length or 254
#         if self.fields['username'].label is None:
#             self.fields['username'].label = capfirst(self.username_field.verbose_name)
#
#     def clean(self):
#         username = self.cleaned_data.get('username')
#         password = self.cleaned_data.get('password')
#
#         if username is not None and password:
#             self.user_cache = authenticate(self.request, username=username, password=password)
#             if self.user_cache is None:
#                 raise self.get_invalid_login_error()
#             else:
#                 self.confirm_login_allowed(self.user_cache)
#
#         return self.cleaned_data
#
#     def confirm_login_allowed(self, user):
#         """
#         Controls whether the given User may log in. This is a policy setting,
#         independent of end-user authentication. This default behavior is to
#         allow login by active users, and reject login by inactive users.
#
#         If the given user cannot log in, this method should raise a
#         ``forms.ValidationError``.
#
#         If the given user may log in, this method should return None.
#         """
#         if not user.is_active:
#             raise forms.ValidationError(
#                 self.error_messages['inactive'],
#                 code='inactive',
#             )
#
#     def get_user(self):
#         return self.user_cache
#
#     def get_invalid_login_error(self):
#         return forms.ValidationError(
#             self.error_messages['invalid_login'],
#             code='invalid_login',
#             params={'username': self.username_field.verbose_name},
#         )


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

    username = forms.CharField(label=_("Username"), label_suffix="", required=True, max_length=100)
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

#     def __init__(self, request=None, *args, **kwargs):
#         self.request = request
#         self.user_cache = None
#
#         super().__init__(*args, **kwargs)
#
#         if request.method == 'GET':
#             username = request.GET.get('username')
#             self.fields['username'].widget.attrs['placeholder'] = "e.g. anon12345"
#             self.fields['username'].widget.attrs['value'] = username
#             self.fields['username'].widget.attrs['readonly'] = True
#         elif request.method == 'POST':
#             # username = kwargs['data'].get('username', None)
#             # if username:
#
#             raise Exception

#     def clean(self):
#         """
#         Override clean
#         """
#         pass

# def clean(self):
#     username = self.cleaned_data.get('username')
#     password = self.cleaned_data.get('password')
#
#     if username is not None and password:
#         self.user_cache = authenticate(self.request, username=username, password=password)
#         if self.user_cache is None:
#             raise self.get_invalid_login_error()
#         else:
#             self.confirm_login_allowed(self.user_cache)
#
#     return self.cleaned_data


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
