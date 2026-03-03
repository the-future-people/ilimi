from django import forms
from apps.teachers.models import StaffProfile
from apps.academics.models import Subject


class StaffPersonalForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Kwame'})
    )
    middle_name = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Asante (optional)'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Mensah'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(choices=[('', '— Select —')] + StaffProfile.GENDER_CHOICES)
    nationality = forms.CharField(
        max_length=100, initial='Ghanaian',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Ghanaian'})
    )
    marital_status = forms.ChoiceField(
        required=False,
        choices=[('', '— Select (optional) —')] + StaffProfile.MARITAL_STATUS_CHOICES
    )
    number_of_dependants = forms.IntegerField(
        min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'placeholder': '0'})
    )
    photo = forms.ImageField(required=False)


class StaffContactForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 0244123456'})
    )
    whatsapp_number = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'If different from phone'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'e.g. kwame@email.com'})
    )
    residential_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. House 12, Tema Community 5'})
    )
    city = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Accra'})
    )
    region = forms.ChoiceField(
        required=False,
        choices=[('', '— Select Region —')] + StaffProfile.GHANA_REGIONS
    )

    def validate_phone_unique(self, school, instance=None):
        phone = self.cleaned_data.get('phone')
        if not phone:
            return
        qs = StaffProfile.objects.filter(school=school, phone=phone)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            self.add_error('phone', 'A staff member with this phone number already exists.')


class StaffEmploymentForm(forms.Form):
    employment_type = forms.ChoiceField(
        choices=StaffProfile.EMPLOYMENT_TYPE_CHOICES
    )
    date_joined_school = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_of_first_appointment = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    salary_grade = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. SS4, P4'})
    )
    is_on_probation = forms.BooleanField(required=False)
    probation_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    is_head_of_department = forms.BooleanField(required=False)


class StaffQualificationForm(forms.Form):
    highest_qualification = forms.ChoiceField(
        required=False,
        choices=[('', '— Select —')] + StaffProfile.QUALIFICATION_CHOICES
    )
    institution_attended = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. University of Ghana'})
    )
    years_of_experience = forms.IntegerField(
        min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'placeholder': '0'})
    )
    ntc_license_number = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. NTC-2019-00123'})
    )
    subject_specializations = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['subject_specializations'].queryset = (
                Subject.objects.filter(school=school).order_by('name')
            )


class StaffDocumentsBankingForm(forms.Form):
    ghana_card_number = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. GHA-000123456-7'})
    )
    ssnit_number = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. C000123456789'})
    )
    bank_name = forms.ChoiceField(
        required=False,
        choices=[('', '— Select Bank —')] + StaffProfile.BANK_CHOICES
    )
    bank_branch = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Accra Main'})
    )
    bank_account_number = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 1234567890'})
    )
    momo_number = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 0244123456'})
    )

    def validate_unique_documents(self, school, instance=None):
        """Cross-field uniqueness checks against the school."""
        ghana_card = self.cleaned_data.get('ghana_card_number')
        ssnit = self.cleaned_data.get('ssnit_number')

        if ghana_card:
            qs = StaffProfile.objects.filter(school=school, ghana_card_number=ghana_card)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                self.add_error('ghana_card_number', 'This Ghana Card number is already registered.')

        if ssnit:
            qs = StaffProfile.objects.filter(school=school, ssnit_number=ssnit)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                self.add_error('ssnit_number', 'This SSNIT number is already registered.')


class StaffNextOfKinForm(forms.Form):
    next_of_kin_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Abena Mensah'})
    )
    next_of_kin_relationship = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Spouse, Father'})
    )
    next_of_kin_phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 0201234567'})
    )
    next_of_kin_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Residential address of next of kin'})
    )