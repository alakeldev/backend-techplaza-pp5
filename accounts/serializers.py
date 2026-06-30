from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, force_str
from django.core.mail import EmailMessage
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Validates that the two password fields match.
    Create a new user with the provided data.
    """

    password1 = serializers.CharField(
        max_length=40, min_length=4, write_only=True
    )
    password2 = serializers.CharField(
        max_length=40, min_length=4, write_only=True
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "password1", "password2"]

    def validate(self, attrs):
        password1 = attrs.get("password1", "")
        password2 = attrs.get("password2", "")
        if password1 != password2:
            raise serializers.ValidationError(
                "The password fields didn't match"
            )
        else:
            return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            full_name=validated_data.get("full_name"),
            email=validated_data.get("email"),
            password=validated_data.get("password1"),
        )
        return user


class LoginSerializer(serializers.ModelSerializer):
    """
    Serializer for user login.
    Authenticates the user
    ensure the email is verified
    returns tokens.
    """

    email = serializers.EmailField(max_length=255, min_length=10)
    password = serializers.CharField(
        max_length=40, min_length=4, write_only=True
    )
    full_name = serializers.CharField(max_length=100, read_only=True)
    token = serializers.CharField(max_length=255, read_only=True)
    refresh_token = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "full_name", "token", "refresh_token"]

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        request = self.context.get("request")
        user = authenticate(request, email=email, password=password)
        if not user:
            raise AuthenticationFailed("Sorry the cerdentials are invalid")
        if not user.is_verified:
            raise AuthenticationFailed("User's Email isn't verified")
        user_token = user.user_tokens()
        return {
            "full_name": user.user_full_name(),
            "email": user.email,
            "token": str(user_token.get("token")),
            "refresh_token": str(user_token.get("refresh")),
        }


class PasswordResetSerializer(serializers.Serializer):
    """
    - Serializer for requesting a password reset.
    - Sends an email with the reset link.
    """

    email = serializers.EmailField(max_length=255)

    class Meta:
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email")

        try:
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            absolute_link = (
                    "https://frontend-techplaza-d0af91d53972."
                    f"herokuapp.com/password_reset_confirm/{uidb64}/{token}"
            )
            data = {
                "email_subject": "Link to reset your password",
                "email_text": (
                    "Hello, please use the link below to reset the password"
                    f"\n{absolute_link}"
                ),
                "to": user.email,
            }
        except User.DoesNotExist:
            data = {
                "email_subject": "Registration Invitation",
                "email_text": (
                    "Hello, it seems you are not registered user."
                    "Please register using the link below:\n"
                    "https://frontend-techplaza-d0af91d53972."
                    "herokuapp.com/register"
                ),
                "to": email,
            }
        self.send_email(data)
        return super().validate(attrs)

    def send_email(self, data):
        email = EmailMessage(
            subject=data["email_subject"],
            body=data["email_text"],
            from_email=settings.EMAIL_HOST_USER,
            to=[data["to"]],
        )
        email.send()


class NewPasswordSerializer(serializers.Serializer):
    """
    Serializer for setting a new password.
    Validates the token and ensures the passwords match.
    """

    password = serializers.CharField(
        max_length=40, min_length=4, write_only=True
    )
    password_confirm = serializers.CharField(
        max_length=40, min_length=4, write_only=True
    )
    uidb64 = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    class Meta:
        fields = ["password", "password_confirm", "uidb64", "token"]

    def validate(self, attrs):
        try:
            uidb64 = attrs.get("uidb64")
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)
        except (ValueError, User.DoesNotExist):
            raise AuthenticationFailed("The reset link is invalid or has expired.", 401)

        token = attrs.get("token")
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise AuthenticationFailed("The reset link is invalid or has expired.", 401)

        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")
        if password != password_confirm:
            raise serializers.ValidationError("Password fields didn't match.")

        user.set_password(password)
        user.save()
        return attrs


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logging out a user.
    Validate the refresh token.
    Blacklists the refresh token.
    """

    refresh_token = serializers.CharField()
    default_error_messages = {"bad_token": ("Token expired")}

    def validate(self, attrs):
        self.token = attrs.get("refresh_token")
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            return self.fail("bad_token")


class UpdateAccountInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for updating account information.
    Validates that the email is unique.
    """

    class Meta:
        model = User
        fields = ["full_name", "email"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
