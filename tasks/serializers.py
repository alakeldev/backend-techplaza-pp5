from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the Task model.
    """

    class Meta:
        model = Task
        fields = ("id", "user", "task_title", "task_description", "is_done")
        read_only_fields = ("user",)
