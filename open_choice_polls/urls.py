from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'open_choice_polls'
urlpatterns = [
    path('', views.QuestionListView.as_view(), name='question-list'),

    path('voter/password_change/', auth_views.PasswordChangeView.as_view(), name='password-change'),
    path('voter/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password-change-done'),
    path('voter/password_reset/', auth_views.PasswordResetView.as_view(), name='password-reset'),
    path('voter/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password-reset-done'),
    path('voter/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('voter/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password-reset-complete'),

    path('voter/enroll/', views.EnrollFormView.as_view(), name='voter-enroll'),
    path('voter/logout/', auth_views.LogoutView.as_view(), name='voter-logout'),
    path('voter/sign_in/', views.SignInFormView.as_view(), name='voter-sign-in'),

    # leave as last as it potentially shadows the other voter/ path
    path('voter/<username>/', views.VoterDetailView.as_view(), name='voter-detail'),

    path('<slug:slug>,<uuid:id>/', views.QuestionDetailView.as_view(), name='question-detail'),
    path('<slug:slug>,<uuid:id>/vote/', views.QuestionEnterVoteView.as_view(), name='vote'),
    path('<slug:slug>,<uuid:id>/choices/', views.QuestionAddChoiceView.as_view(), name='choices'),
    path('<slug:slug>,<uuid:id>/results/', views.QuestionResultsView.as_view(), name='results'),
]
