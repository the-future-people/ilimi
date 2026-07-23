from rest_framework import serializers

from apps.agamotto.models import DemoRequest


class DemoRequestSerializer(serializers.ModelSerializer):
    """
    Public intake for the marketing site's demo form.

    `website` is a honeypot — a hidden field real users never fill. Bots that
    fill every field trip it and are silently rejected. Server-managed fields
    (status, source, ip, user_agent) are never accepted from the client.
    """

    hp_ilimi_x92 = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = DemoRequest
        fields = ['name', 'email', 'phone', 'school_name', 'message', 'hp_ilimi_x92']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please tell us your name.")
        return value.strip()

    def validate_phone(self, value):
        digits = ''.join(c for c in value if c.isdigit())
        if len(digits) < 9:
            raise serializers.ValidationError("Please enter a valid phone number.")
        return value.strip()

    def validate(self, attrs):
        # Honeypot: content here means a bot. Generic error so it can't tell
        # it was detected.
        if attrs.get('hp_ilimi_x92'):
            raise serializers.ValidationError("Submission could not be processed.")
        attrs.pop('hp_ilimi_x92', None)
        return attrs