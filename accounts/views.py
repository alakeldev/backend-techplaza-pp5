from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from datetime import timedelta
import random
import string
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    NewPasswordSerializer,
    LogoutSerializer,
    UpdateAccountInfoSerializer,
)
from .models import User


class RegisterView(GenericAPIView):
    """
    API view for user registration.
    Sends an OTP to the user's email for verification.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()

            otp = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            send_mail(
                "Techplaza OTP for Registration Verification",
                (
                    f"Your OTP for registration verification is {otp}.\n"
                    "Please use this link: "
                    "https://frontend-techplaza-d0af91d53972."
                    "herokuapp.com/otp/verify "
                    "if you close your browser window.\n"
                    "Note: Your email will be deleted "
                    "from our database after 14 days "
                    "if not verified."
                ),
                "techplazaplatform@gmail.com",
                [user.email],
                fail_silently=False,
            )

            response_data = RegisterSerializer(user).data

            return Response(
                {
                    "data": response_data,
                    "message": f"""Thanks for Registration {user.full_name},
                            a verified code has been sent to your Email.""",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmail(APIView):
    """
    API view for verifying user email with OTP.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        otp_to_verify = request.data.get("otp")
        email = request.data.get("email")
        if not otp_to_verify or not email:
            return Response(
                {"error": "OTP and email are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(email=email)
            otp_valid_duration = 15
            if (
                user.otp == otp_to_verify
                and timezone.now() - user.otp_created_at
                <= timedelta(minutes=otp_valid_duration)
            ):
                user.is_verified = True
                user.save()
                return Response(
                    {"message": "Email successfully verified"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Invalid or expired OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LoginView(GenericAPIView):
    """
    API view for user login.
    Authenticates the user and returns tokens.
    """

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordResetView(GenericAPIView):
    """
    API view for requesting a password reset.
    Sends an email with the reset link or registration invitation.
    """

    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "message": (
                            "A reset link or registration invitation "
                            "has been sent to your email."
                            "Check the spam folder if you do not see it."
                        )
            },
            status=status.HTTP_200_OK,
        )


class ConfirmPasswordResetView(GenericAPIView):
    """
    API view for confirming the password reset token.
    """

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            user_id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response(
                    {"message": "Token is expired"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            return Response(
                {
                    "success": True,
                    "message": "The credentials are valid",
                    "uidb64": uidb64,
                    "token": token,
                },
                status=status.HTTP_200_OK,
            )
        except (DjangoUnicodeDecodeError, ValueError, User.DoesNotExist):
            return Response(
                {"message": "Token has expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class NewPasswordView(GenericAPIView):
    """
    API view for setting a new password.
    """

    serializer_class = NewPasswordSerializer
    permission_classes = [AllowAny]

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"message": "Your Password Reset Successfully"},
            status=status.HTTP_200_OK,
        )


class LogoutView(GenericAPIView):
    """
    API view for logging out a user.
    Blacklists the refresh token.
    """

    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)


class UpdateInformationView(APIView):
    """
    API view for updating user account information.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UpdateAccountInfoSerializer(
            user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )


class DeleteAccountView(APIView):
    """
    API view for deleting a user account.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        user.delete()
        return Response(
            {"message": "Account deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )
