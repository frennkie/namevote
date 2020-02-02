from django.urls import path

from . import views

app_name = 'open_choice_polls'
urlpatterns = [
    path('', views.QuestionListView.as_view(), name='question-list'),
    path('<slug:slug>,<uuid:id>/', views.QuestionDetailView.as_view(), name='question-detail'),
    path('<slug:slug>,<uuid:id>/enter_vote/', views.EnterVoteView.as_view(), name='enter_vote'),
    path('<slug:slug>,<uuid:id>/choices/', views.AddChoiceView.as_view(), name='choices'),
    path('<slug:slug>,<uuid:id>/results/', views.ResultsView.as_view(), name='results'),
    path('<slug:slug>,<uuid:id>/add_choice/', views.add_choice, name='add_choice'),
    path('<slug:slug>,<uuid:id>/vote/', views.vote, name='vote'),
]
