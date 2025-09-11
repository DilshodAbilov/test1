from django.db import models
from accounts.models import CustomUser as User
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    def __str__(self):
        return self.name
class Group(models.Model):
    name = models.CharField(max_length=20)
    description = models.TextField(null=True, blank=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField()
    time = models.IntegerField()
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    def __str__(self):
        return self.name
level = {
    'HIGH': 'HIGH',
    'MEDIUM': 'MEDIUM',
    'LOW': 'LOW'
}
class Questions(models.Model):
    question = models.CharField(max_length=100)
    file = models.FileField(upload_to='questions', blank=True, null=True)
    group = models.ManyToManyField('Group',  related_name="questions", blank=True)
    level = models.CharField(choices=level, max_length=20)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    def __str__(self):
        return self.question

class Answer(models.Model):
    question = models.ForeignKey('Questions', on_delete=models.CASCADE, related_name='answers')
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Answer(models.Model):
        question = models.ForeignKey('Questions', on_delete=models.CASCADE, related_name='answers')
        answer = models.TextField()
        is_correct = models.BooleanField(default=False)

        def __str__(self):
            return self.answer


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    score = models.IntegerField()
    rank = models.IntegerField(default = 0)
    def __str__(self):
        return self.user.username
class GroupUsers(models.Model):
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.group.name
class UserAnswers(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.ForeignKey('Answer', on_delete=models.CASCADE)
    question = models.ForeignKey('Questions', on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()
    def __str__(self):
        return self.user.username
