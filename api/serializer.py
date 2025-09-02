# serializers.py
from rest_framework import serializers
from tests.models import *
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
class AnswersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'answer', 'is_correct']
        read_only_fields = ['id']

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = '__all__'

class QuestionsSerializer(serializers.ModelSerializer):
    answers = AnswersSerializer(many=True)
    level = LevelSerializer()
    category = CategorySerializer()
    created_by = serializers.ReadOnlyField(source='created_by.username')  # faqat o‘qish uchun

    class Meta:
        model = Questions
        fields = '__all__'
        read_only_fields = ('id', 'group', 'created_by')  # group va created_by view orqali belgilanadi

    def validate(self, data):
        answers = self.initial_data.get('answers', [])
        if len(answers) != 4:
            raise serializers.ValidationError("Har bir savolda aniq 4ta javob bo‘lishi kerak.")
        true_count = sum(1 for ans in answers if ans.get('is_correct') == True)
        if true_count != 1:
            raise serializers.ValidationError("Har bir savolda faqat bitta javob True bo‘lishi kerak.")
        return data

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        request = self.context.get('request')
        group = self.context.get('group')

        level_data = self.initial_data.get('level', {})
        level, _ = Level.objects.get_or_create(name=level_data.get('name', 'Default Level'), defaults={'ball': 0})
        validated_data['level'] = level

        category_data = self.initial_data.get('category', {})
        category, _ = Category.objects.get_or_create(name=category_data.get('name', 'Default Category'))
        validated_data['category'] = category

        question = Questions.objects.create(created_by=request.user, **validated_data)

        for answer in answers_data:
            Answer.objects.create(question=question, **answer)

        if group:
            question.group.add(group)

        return question

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.created_by != request.user:
            raise serializers.ValidationError("Faqat o‘zing yaratgan savolni tahrirlash mumkin.")

        answers_data = validated_data.pop('answers', [])

        level_data = self.initial_data.get('level', None)
        if level_data:
            level, _ = Level.objects.get_or_create(name=level_data.get('name', 'Default Level'), defaults={'ball': 0})
            instance.level = level

        category_data = self.initial_data.get('category', None)
        if category_data:
            category, _ = Category.objects.get_or_create(name=category_data.get('name', 'Default Category'))
            instance.category = category

        instance.text = validated_data.get('text', instance.text)
        instance.save()

        instance.answers.all().delete()
        for answer in answers_data:
            Answer.objects.create(question=instance, **answer)

        return instance

class GroupSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = '__all__'
        read_only_fields = ('id', 'admin', 'start_time', "end_time")


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = '__all__'

