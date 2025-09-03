from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests

User = get_user_model()


# -------------------
# Admin Register
# -------------------
class AdminRegisterSerializer(serializers.ModelSerializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "password", "access", "refresh")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.is_admin = True
        user.is_staff = False   # API orqali hech qachon staff bo‘lmaydi
        user.save()

        refresh = RefreshToken.for_user(user)
        return {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_user": user.is_user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


# -------------------
# Admin Login
# -------------------
class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, data):
        user = authenticate(username=data.get("username"), password=data.get("password"))
        if not user or not user.is_admin:
            raise serializers.ValidationError("Admin topilmadi yoki parol noto‘g‘ri")

        refresh = RefreshToken.for_user(user)
        return {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_user": user.is_user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


# -------------------
# Google Auth (User & Admin)
# -------------------
class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)
    is_admin = serializers.BooleanField(default=False, write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

    def validate(self, data):
        token = data.get("id_token")
        is_admin = data.get("is_admin", False)

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request())

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            username = email.split("@")[0]

            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first_name, "last_name": last_name, "email": email},
            )

            if is_admin:
                user.is_admin = True
            else:
                user.is_user = True

            user.is_staff = False   # API orqali staff qo‘yilmaydi
            user.save()

            refresh = RefreshToken.for_user(user)
            return {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_user": user.is_user,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }

        except ValueError:
            raise serializers.ValidationError("Google token noto‘g‘ri yoki eskirgan")
