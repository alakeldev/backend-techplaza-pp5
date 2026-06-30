from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import HighScore
from .serializers import HighScoreSerializer


class HighScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing HighScore objects.
    Requires authentication for all actions.
    Associates the high score with the currently authenticated user.
    """

    serializer_class = HighScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HighScore.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
