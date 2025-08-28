from django.urls import path, include
from .views import *
urlpatterns = [
    path('rooms/', GroupAdd.as_view(), name='add'),
    path('rooms/<str:group_id>/', GroupEditor.as_view(), name='edit group'),
    path('rooms/<str:group_id>/questions/', AddQuestion.as_view(), name='addtest'),
    path('rooms/<str:group_id>/questions/<int:question_id>/', EditQuestion.as_view(), name='edit test'),
    path('myresult/', Result.as_view()),
    path('delete/<str:group_id>', DeleteUserAnswer.as_view())
]