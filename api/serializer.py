from rest_framework import serializers
from tests.models import *
from accounts.models import CustomUser
class AnswersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'answer', 'is_correct']
        read_only_fields = ['id']
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
class QuestionsSerializer(serializers.ModelSerializer):
    answers = AnswersSerializer(many=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True
    )
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Questions
        fields = '__all__'

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        category = validated_data.pop('category_id')  # write_only fielddan olamiz
        request = self.context.get('request')
        group = self.context.get('group')

        question = Questions.objects.create(
            created_by=request.user,
            category=category,
            **validated_data
        )

        for answer_data in answers_data:
            Answer.objects.create(question=question, **answer_data)

        if group:
            question.group.add(group)

        return question

    def validate(self, data):
        answers = data.get('answers', [])
        if len(answers) != 4:
            raise serializers.ValidationError({"answers": "Har bir savolda aniq 4ta javob bo‘lishi kerak."})
        true_count = sum(1 for ans in answers if ans.get('is_correct') == True)
        if true_count != 1:
            raise serializers.ValidationError({"answers": "Har bir savolda faqat bitta javob to'g'ri bo'lishi kerak."})
        return data
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.created_by != request.user:
            raise serializers.ValidationError("Faqat o‘zingiz yaratgan savolni tahrirlash mumkin.")
        answers_data = validated_data.pop('answers', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.answers.all().delete()
        for answer_data in answers_data:
            Answer.objects.create(question=instance, **answer_data)
        return instance
class GroupSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True, read_only=True)
    class Meta:
        model = Group
        fields = '__all__'
        read_only_fields = ('id', 'admin', 'start_time', "end_time", "is_used")
class ResultSerializer(serializers.Serializer):
    score = serializers.FloatField()
    rank = serializers.IntegerField()
    group_name = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), source='group.name')
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields  = '__all__'