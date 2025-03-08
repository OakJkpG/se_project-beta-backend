# users/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Profile
from django.contrib.auth import authenticate

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")
        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User account not activated")
        data["user"] = user
        return data

class SignupReaderSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def create(self, validated_data):
        username = validated_data["email"]  # ใช้ email เป็น username
        user = User.objects.create_user(
            username=username,
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["name"]
        )
        user.is_active = False  # รอการยืนยันอีเมล
        user.save()
        # สร้าง Profile สำหรับ reader พร้อมรหัสยืนยัน (6 หลัก)
        import random
        verification_code = str(random.randint(100000, 999999))
        Profile.objects.create(user=user, user_type='reader', verification_code=verification_code)
        # ส่งอีเมลยืนยัน (สำหรับ demo ส่งไปที่ console)
        from django.core.mail import send_mail
        send_mail(
            'Your Verification Code',
            f'Your verification code is: {verification_code}',
            'noreply@bookhub.com',
            [validated_data["email"]],
            fail_silently=True,
        )
        return user

class ReaderVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data.get("email")
        code = data.get("verification_code")
        try:
            user = User.objects.get(email=email)
            profile = user.profile
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        if profile.verification_code != code:
            raise serializers.ValidationError("Invalid verification code")
        return data

    def save(self, **kwargs):
        email = self.validated_data["email"]
        user = User.objects.get(email=email)
        user.is_active = True
        user.save()
        profile = user.profile
        profile.verification_code = ""
        profile.save()
        return user

class SignupPublisherSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    id_card = serializers.CharField(max_length=50)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def create(self, validated_data):
        username = validated_data["email"]
        user = User.objects.create_user(
            username=username,
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["name"]
        )
        user.is_active = False  # รอการตรวจสอบจาก admin
        user.save()
        Profile.objects.create(user=user, user_type='publisher', id_card=validated_data["id_card"])
        # ส่งอีเมลแจ้ง admin ให้ตรวจสอบ (ในที่นี้ส่งไปที่ admin@bookhub.com)
        from django.core.mail import send_mail
        send_mail(
            'New Publisher Signup',
            f'A new publisher has registered with email: {validated_data["email"]}. Please review and activate the account.',
            'noreply@bookhub.com',
            ['admin@bookhub.com'],
            fail_silently=True,
        )
        return user
