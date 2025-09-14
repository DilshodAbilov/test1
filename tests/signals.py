from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Group, Questions

@receiver([post_save, post_delete], sender=Questions)
def update_total_questions(sender, instance, **kwargs):
    group = instance.group
    total = Questions.objects.filter(group=group).count()
    group.total_questions = total
    group.save(update_fields=['total_questions'])
