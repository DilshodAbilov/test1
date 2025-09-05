from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
from firebase_admin import auth as firebase_auth

User = get_user_model()

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

class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

    def validate(self, data):
        token = data.get("id_token")

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request())

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            username = email.split("@")[0] if email else None

            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first_name, "last_name": last_name, "email": email},
            )

            user.is_admin = True
            user.is_user = False
            user.is_staff = False
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

class FirebaseAuthSerializer(serializers.Serializer):
    firebase_token = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

    def validate(self, data):
        token = data.get("firebase_token")

        try:
            decoded_token = firebase_auth.verify_id_token(token)
            email = decoded_token.get("email")
            uid = decoded_token.get("uid")
            name = decoded_token.get("name", "")
            first_name = name.split(" ")[0] if name else ""
            last_name = " ".join(name.split(" ")[1:]) if len(name.split(" ")) > 1 else ""

            username = email.split("@")[0] if email else uid

            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first_name, "last_name": last_name, "email": email},
            )

            user.is_user = True
            user.is_admin = False
            user.is_staff = False
            user.save()

            refresh = RefreshToken.for_user(user)
            return {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_user": user.is_user,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }

        except Exception as e:
            raise serializers.ValidationError(f"Firebase token noto‘g‘ri: {str(e)}")
