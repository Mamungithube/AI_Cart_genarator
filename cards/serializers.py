from rest_framework import serializers
from .models import CardSession, CardMessage

class CardPromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True)

class CardChatSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)
    prompt = serializers.CharField(required=False, allow_blank=True)
    reference_image = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        # Allow either message or prompt
        if not attrs.get('message') and not attrs.get('prompt') and not attrs.get('reference_image'):
            raise serializers.ValidationError("Either 'message', 'prompt', or 'reference_image' must be provided.")
        if not attrs.get('message') and attrs.get('prompt'):
            attrs['message'] = attrs['prompt']
        return attrs


class CardMessageSerializer(serializers.ModelSerializer):
    reference_image_url = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)

    class Meta:
        model = CardMessage
        fields = [
            'id',
            'sender',
            'role',
            'message',
            'content',
            'version',
            'reference_image_url',
            'front_html',
            'back_html',
            'css',
            'card_data',
            'image_base64',
            'image_url',
            'created_at',
        ]

    def get_reference_image_url(self, obj):
        if obj.reference_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.reference_image.url)
            return obj.reference_image.url
        return None


class CardSessionSerializer(serializers.ModelSerializer):
    messages = CardMessageSerializer(many=True, read_only=True)
    current_version = serializers.IntegerField(source='version', read_only=True)
    current_state = serializers.JSONField(source='card_data', read_only=True)

    class Meta:
        model = CardSession
        fields = [
            'id',
            'title',
            'version',
            'current_version',
            'current_state',
            'front_html',
            'back_html',
            'css',
            'card_data',
            'image_base64',
            'image_url',
            'created_at',
            'updated_at',
            'messages',
        ]
