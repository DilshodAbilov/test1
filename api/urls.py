from django.urls import path, include
from .views import *
urlpatterns = [
    path('rooms/', GroupAdd.as_view(), name='add'),
    path('rooms/<str:group_code>/', GroupEditor.as_view(), name='edit group'),
    path('rooms/<str:group_code>/questions/', AddQuestion.as_view(), name='addtest'),
    path('rooms/<str:group_code>/questions/<int:question_id>/', EditQuestion.as_view(), name='edit test'),
    path('myresult/', Result.as_view()),
    path('delete/<str:group_code>/', DeleteUserAnswer.as_view()),
    path('rooms/<str:group_code>/addexist/', AddExistingQuestions.as_view()),
]