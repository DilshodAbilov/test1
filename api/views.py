from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializer import *
from tests.models import *
from accounts.models import *
from .permission import *
from rest_framework.pagination import PageNumberPagination
class GroupAdd(APIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=GroupSerializer(many=True))
    def get(self, request):
        groups = Group.objects.filter(admin = request.user)
        page = PageNumberPagination()
        pagination = page.paginate_queryset(groups, request, view=self)
        serializer = GroupSerializer(pagination, many=True, context={'request': request})
        return page.get_paginated_response(serializer.data)

    @extend_schema(request=GroupSerializer, responses=GroupSerializer)
    def post(self, request):
        serializer = GroupSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(admin=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroupEditor(APIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsRoomOwner]

    @extend_schema(responses=GroupSerializer)
    def get(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        serializer = GroupSerializer(group)
        return Response(serializer.data)
    @extend_schema(request=GroupSerializer, responses=GroupSerializer)
    def patch(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        serializer = GroupSerializer(instance=group, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save(admin=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={204: None})
    def delete(self, request, group_code):
        group = get_object_or_404(Group, code=group_code)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AddQuestion(APIView):
    serializer_class = QuestionsSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=QuestionsSerializer(many=True))
    def get(self, request, group_code):
        questions = Questions.objects.filter(group__code=group_code, created_by = request.user)
        page = PageNumberPagination()
        pagination = page.paginate_queryset(questions, request, view=self)
        serializer = QuestionsSerializer(pagination, many=True, context={'request': request})
        return page.get_paginated_response(serializer.data)

    @extend_schema(request=QuestionsSerializer, responses=QuestionsSerializer)
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

    @extend_schema(request=QuestionsSerializer(many=True))
    def get(self, request, group_code):
        questions = Questions.objects.filter(created_by=request.user, group__code=group_code)
        if request.GET.get("category"):
            questions = questions.filter(category_id=request.GET.get("category"))
        if request.GET.get("level"):
            questions = questions.filter(level=request.GET.get("level"))
        if request.GET.get("question"):
            questions = questions.filter(questions__icontains=request.GET.get("question"))
        page = PageNumberPagination()
        pagination = page.paginate_queryset(questions, request, view=self)
        serializer = QuestionsSerializer(pagination, many=True, context={'request': request})
        return page.get_paginated_response(serializer.data)

    @extend_schema(request=QuestionsSerializer, responses=QuestionsSerializer)
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

    @extend_schema(responses={204: None})
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
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=QuestionsSerializer)
    def get(self, request, group_code, question_id):
        question = get_object_or_404(Questions, id=question_id, group__code=group_code)
        serializer = QuestionsSerializer(question)
        return Response(serializer.data)

    @extend_schema(request=QuestionsSerializer, responses=QuestionsSerializer)
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

    @extend_schema(responses={204: None})
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

class Question(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=QuestionsSerializer(many=True))
    def get(self, request):
        question = Questions.objects.filter(created_by=request.user)
        if request.GET.get("category"):
            question = question.filter(category_id=request.GET.get("category"))
        if request.GET.get("level"):
            question = question.filter(level=request.GET.get("level"))
        if request.GET.get("question"):
            question = question.filter(questions__icontains=request.GET.get("question"))
        page = PageNumberPagination()
        pagination = page.paginate_queryset(question, request, view=self)
        serializer = QuestionsSerializer(pagination, many=True, context={'request': request})
        return page.get_paginated_response(serializer.data)

    @extend_schema(request=QuestionsSerializer, responses=QuestionsSerializer)
    def post(self, request):
        if not request.user.is_admin:
            return Response({"detail": "Faqat admin savol qo‘shishi mumkin."}, status=status.HTTP_403_FORBIDDEN)
        serializer = QuestionsSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class QuestionsEditor(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=QuestionsSerializer)
    def get(self, request, question_id):
        question = Questions.objects.get(id=question_id, created_by=request.user)
        serializer = QuestionsSerializer(question)
        return Response(serializer.data)

    @extend_schema(request=QuestionsSerializer, responses=QuestionsSerializer)
    def put(self, request, question_id):
        question = Questions.objects.get(id=question_id, created_by=request.user)
        if not request.user == question.created_by:
            return Response({"detail":"Savol egasi emassiz!"})

        serializer = QuestionsSerializer(instance=question, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={204: None})
    def delete(self, request, question_id):
        question = Questions.objects.get(id=question_id, created_by=request.user)
        if not request.user == question.created_by:
            return Response({"detail":"Savol egasi emassiz!"})
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
class CategoryApi(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CategorySerializer(many=True))
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(request=CategorySerializer, responses=CategorySerializer)
    def post(self, request):
        if not request.user.is_admin:
            return Response({"detail":"Admin emassiz!"})
        serializer = CategorySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class CategoryList(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CategorySerializer)
    def get(self, request, category_id):
        category = Category.objects.get(id=category_id)
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=CategorySerializer, responses=CategorySerializer)
    def put(self, request, category_id):
        if not request.user.is_admin:
            return Response({"detail":"Admin emassiz!"})
        category = Category.objects.get(id=category_id)
        serializer = CategorySerializer(instance=category, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={204: None})
    def delete(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        if not request.user.is_admin:
            return Response({"detail":"Admin emassiz!"})
        category.delete()
        return Response({"detail":"O'chirildi!!!"},status=status.HTTP_204_NO_CONTENT)
class UserMe(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        serializer = CustomUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
