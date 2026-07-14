from rest_framework import serializers
from apps.tenants.models import School, Branch, SchoolMember


# ── Branch ────────────────────────────────────────────────────────────────

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "branch_code",
            "address",
            "city",
            "phone",
            "email",
            "is_main_branch",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BranchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "name",
            "branch_code",
            "address",
            "city",
            "phone",
            "email",
            "is_main_branch",
        ]

    def validate_branch_code(self, value):
        school = self.context.get("school")
        qs = Branch.objects.filter(school=school, branch_code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A branch with this code already exists for your school."
            )
        return value.upper()


# ── School ────────────────────────────────────────────────────────────────

class SchoolSerializer(serializers.ModelSerializer):
    branches = BranchSerializer(many=True, read_only=True)

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "slug",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "logo",
            "website",
            "subscription_status",
            "is_active",
            "onboarding_complete",
            "onboarding_step",
            "branches",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "subscription_status",
            "is_active",
            "onboarding_complete",
            "onboarding_step",
            "created_at",
        ]


class SchoolUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "logo",
            "website",
        ]


# ── School Member ─────────────────────────────────────────────────────────

class SchoolMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()

    class Meta:
        model = SchoolMember
        fields = [
            "id",
            "user_email",
            "full_name",
            "role",
            "branch_name",
            "is_active",
            "joined_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.user.full_name

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None


class SchoolMemberInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            ("school_admin", "School Administrator"),
            ("branch_manager", "Branch Manager"),
            ("teacher", "Teacher"),
            ("accountant", "Accountant"),
            ("receptionist", "Receptionist"),
        ]
    )
    branch_id = serializers.IntegerField(required=False, allow_null=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone_number(self, value):
        if not value:
            return value
        value = value.strip().replace(" ", "")
        if not value.startswith("+"):
            raise serializers.ValidationError(
                "Phone number must include country code, e.g. +233XXXXXXXXX"
            )
        return value


# ── My Memberships ────────────────────────────────────────────────────────

class MyMembershipSerializer(serializers.ModelSerializer):
    school_id      = serializers.IntegerField(source="school.id", read_only=True)
    school_name    = serializers.CharField(source="school.name", read_only=True)
    school_logo    = serializers.ImageField(source="school.logo", read_only=True)
    branch_id      = serializers.IntegerField(source="branch.id", read_only=True, allow_null=True)
    branch_name    = serializers.SerializerMethodField()
    role_display   = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = SchoolMember
        fields = [
            "id",
            "school_id",
            "school_name",
            "school_logo",
            "branch_id",
            "branch_name",
            "role",
            "role_display",
            "is_active",
            "has_seen_tour",
            "joined_at",
        ]
        read_only_fields = fields

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None