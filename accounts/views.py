from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
import firebase_admin
from firebase_admin import auth as firebase_auth
from .serializers import (
    AdminRegisterSerializer,
    AdminLoginSerializer,
    GoogleAuthSerializer,
    FirebaseAuthSerializer  ,
)

User = get_user_model()

class AdminRegisterView(generics.GenericAPIView):
    serializer_class = AdminRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_201_CREATED)

class AdminLoginView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class GoogleAuthView(generics.GenericAPIView):
    serializer_class = GoogleAuthSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class FirebaseAuthView(APIView):
    def post(self, request):
        id_token = request.data.get("id_token")

        if not id_token:
            return Response({"error": "id_token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
            email = decoded_token.get("email")
            name = decoded_token.get("name")

            if not email:
                return Response({"error": "Email not found in Firebase token"}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": name.split(" ")[0] if name else "",
                    "last_name": name.split(" ")[-1] if name and len(name.split(" ")) > 1 else "",
                }
            )

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            if created:
                message = "User created and logged in"
            else:
                message = "User logged in"

            return Response({
                "message": message,
                "refresh": str(refresh),
                "access": access_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
