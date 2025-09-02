from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializer import *
from tests.models import *
from .permission import *

class GroupAdd(APIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = Group.objects.all()
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = GroupSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(admin=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroupEditor(APIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsRoomOwner]

    def get(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        serializer = GroupSerializer(group)
        return Response(serializer.data)

    def put(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        serializer = GroupSerializer(instance=group, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(admin=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AddQuestion(APIView):
    serializer_class = QuestionsSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, group_code):
        questions = Questions.objects.filter(group__code=group_code)
        serializer = QuestionsSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Faqat xona egasi savol qo‘shishi mumkin."}, status=status.HTTP_403_FORBIDDEN)
        serializer = QuestionsSerializer(data=request.data, context={'request': request, 'group': group})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AddExistingQuestions(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_code):
        questions = Questions.objects.filter(created_by=request.user, group__code=group_code)
        serializer = QuestionsSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Faqat xona egasi test qo‘shishi mumkin."}, status=status.HTTP_403_FORBIDDEN)
        question_ids = request.data.get('question_ids', [])
        if not question_ids:
            return Response({"detail": "Hech qanday test tanlanmagan"}, status=status.HTTP_400_BAD_REQUEST)
        questions = Questions.objects.filter(id__in=question_ids, created_by=request.user)
        for q in questions:
            q.group.add(group)
        return Response({"detail": f"{questions.count()} test qo‘shildi"}, status=status.HTTP_200_OK)

    def delete(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Faqat xona egasi testlarni o‘chirishi mumkin."}, status=status.HTTP_403_FORBIDDEN)
        question_ids = request.data.get('question_ids', [])
        if not question_ids:
            return Response({"detail": "Hech qanday test tanlanmagan"}, status=status.HTTP_400_BAD_REQUEST)
        questions = Questions.objects.filter(id__in=question_ids, group=group)
        if not questions.exists():
            return Response({"detail": "Tanlangan testlar groupda topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        for q in questions:
            q.group.remove(group)
        return Response({"detail": f"{questions.count()} test groupdan o‘chirildi"}, status=status.HTTP_200_OK)

class EditQuestion(APIView):
    serializer_class = QuestionsSerializer

    def get(self, request, group_code, question_id):
        question = get_object_or_404(Questions, id=question_id, group__code=group_code)
        serializer = QuestionsSerializer(question)
        return Response(serializer.data)

    def put(self, request, group_code, question_id):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Faqat xona egasi savol qo‘shishi mumkin."}, status=status.HTTP_403_FORBIDDEN)
        question = get_object_or_404(Questions, id=question_id, group__code=group_code)
        serializer = QuestionsSerializer(instance=question, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, group_code, question_id):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Faqat xona egasi bu huquqqa ega"}, status=status.HTTP_403_FORBIDDEN)
        question = get_object_or_404(Questions, id=question_id, group__code=group_code)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class Result(APIView):
    serializer_class = ResultSerializer

    @extend_schema(responses=ResultSerializer(many=True))
    def get(self, request):
        results = Result.objects.filter(user=request.user)
        serializer = ResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DeleteUserAnswer(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        if group.admin != request.user:
            return Response({"detail": "Siz xona egasi emassiz"}, status=status.HTTP_403_FORBIDDEN)
        answers = UserAnswers.objects.filter(question__group__code=group_code)
        deleted_count = answers.count()
        answers.delete()
        return Response({"detail": f"{deleted_count} javob o‘chirildi"}, status=status.HTTP_200_OK)
