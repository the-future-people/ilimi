from rest_framework import serializers

from apps.documents.models import DocumentTemplate, GeneratedDocument


class DocumentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'name', 'document_type', 'body_html', 'extra_fields',
            'requires_signature', 'is_computed', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    document_type = serializers.CharField(source='template.document_type', read_only=True)
    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'student', 'template', 'template_name', 'document_type',
            'generated_by', 'generated_by_name', 'generated_at',
            'pdf_file', 'context_snapshot',
        ]
        read_only_fields = fields

    def get_generated_by_name(self, obj):
        if obj.generated_by:
            return obj.generated_by.full_name or obj.generated_by.email
        return None


class DocumentGenerationRequestSerializer(serializers.Serializer):
    """
    Shared input shape for both preview/ and generate/ endpoints.
    Not tied to a model — this validates the request payload only;
    extra_fields validation against the specific template happens in
    the service layer (validate_extra_values), since that depends on
    which template was chosen.
    """
    template_id = serializers.IntegerField()
    extra_values = serializers.DictField(required=False, default=dict)