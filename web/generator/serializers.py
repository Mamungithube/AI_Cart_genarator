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
