from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'open_choice_polls'
urlpatterns = [
    path('', views.QuestionListView.as_view(), name='question-list'),

    path('voter/selogin/', views.selogin, name='se-login'),
    path('voter/selogin/<username>/', views.selogin, name='se-login-username'),
    path('voter/selogin-user/', views.selogin_user, name='se-login-user'),

    path('voter/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('voter/password_change/', auth_views.PasswordChangeView.as_view(), name='password-change'),
    path('voter/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password-change-done'),

    path('voter/password_reset/', auth_views.PasswordResetView.as_view(), name='password-reset'),
    path('voter/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password-reset-done'),
    path('voter/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('voter/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password-reset-complete'),

    path('voter/<username>/', views.VoterDetailView.as_view(), name='user-detail'),

    path('<slug:slug>,<uuid:id>/', views.QuestionDetailView.as_view(), name='question-detail'),
    path('<slug:slug>,<uuid:id>/enter_vote/', views.EnterVoteView.as_view(), name='enter_vote'),
    path('<slug:slug>,<uuid:id>/choices/', views.AddChoiceView.as_view(), name='choices'),
    path('<slug:slug>,<uuid:id>/results/', views.ResultsView.as_view(), name='results'),
    path('<slug:slug>,<uuid:id>/add_choice/', views.add_choice, name='add_choice'),
    path('<slug:slug>,<uuid:id>/vote/', views.vote, name='vote'),
]
