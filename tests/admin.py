from django.contrib import admin

# Register your models here.
from .models import *
admin.site.register(Questions)
admin.site.register(Answer)
admin.site.register(Group)
admin.site.register(Result)
admin.site.register(UserAnswers)
admin.site.register(Category)
admin.site.register(GroupUsers)
