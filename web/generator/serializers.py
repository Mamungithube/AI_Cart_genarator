from rest_framework import serializers


class CardPromptSerializer(serializers.Serializer):
    """
    Single-field serializer.
    User sends only a 'prompt' containing all card information in natural language.
    AI extracts structured data and generates the visiting card.
    """
    prompt = serializers.CharField(
        min_length=10,
        max_length=2000,
        required=True,
        error_messages={
            'required': 'prompt field is required.',
            'blank': 'prompt cannot be blank.',
            'min_length': 'prompt is too short. Please provide enough information.',
        }
    )

    def validate_prompt(self, value):
        return value.strip()


class CardChatSerializer(serializers.Serializer):
    """
    Serializer for multi-turn conversational visiting card generation.
    - session_id: Optional UUID string. If omitted/null, a new card session begins.
    - message: The natural language instruction from the user.
    """
    session_id = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None
    )
    message = serializers.CharField(
        min_length=2,
        max_length=2000,
        required=True,
        error_messages={
            'required': 'message field is required.',
            'blank': 'message cannot be blank.',
            'min_length': 'message is too short.',
        }
    )

    def validate_message(self, value):
        return value.strip()

