from rest_framework import viewsets
from .models import Card
from .serializers import CardSerializer
from rest_framework.permissions import IsAuthenticated


class CardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Card objects.
    Requires authentication for all actions.
    Listing and retrieving cards is open to all authenticated users (community feature).
    Creating, updating, and deleting a card is restricted to the card's owner.
    """

    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action in ("update", "partial_update", "destroy"):
            return Card.objects.filter(user=self.request.user)
        return Card.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
