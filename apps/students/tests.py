from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.tenants.models import School, Branch, SchoolMember
from apps.academics.models import AcademicYear, Term, ClassLevel, ClassRoom
from apps.students.models import (
    Student,
    Guardian,
    StudentGuardian,
    EmergencyContact,
    StudentClassHistory,
)


# ── Base Setup ────────────────────────────────────────────────────────────

class StudentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create school
        self.school = School.objects.create(
            name='Test Academy',
            email='school@test.com',
        )
        self.branch = Branch.objects.create(
            school=self.school,
            name='Main Branch',
        )

        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='Testpass123!',
            first_name='Admin',
            last_name='User',
        )
        self.member = SchoolMember.objects.create(
            user=self.admin,
            school=self.school,
            branch=self.branch,
            role='school_admin',
            is_active=True,
        )

        # Create another school + user (for tenant isolation tests)
        self.other_school = School.objects.create(
            name='Other Academy',
            email='other@test.com',
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='Testpass123!',
            first_name='Other',
            last_name='User',
        )
        SchoolMember.objects.create(
            user=self.other_user,
            school=self.other_school,
            role='school_admin',
            is_active=True,
        )

        # Create academics
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_current=True,
        )
        self.term = Term.objects.create(
            academic_year=self.academic_year,
            name='term1',
            start_date='2025-09-01',
            end_date='2025-12-31',
            is_current=True,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            name='Primary 1',
            order=1,
        )
        self.classroom = ClassRoom.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            class_level=self.class_level,
            section_name='Nkrumah',
            capacity=35,
        )

        # Authenticate
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Base enrol payload
        self.enrol_payload = {
            'first_name': 'Kofi',
            'last_name': 'Asante',
            'date_of_birth': '2012-03-10',
            'gender': 'male',
            'current_class': self.classroom.id,
            'guardians': [
                {
                    'first_name': 'Yaw',
                    'last_name': 'Asante',
                    'relationship': 'father',
                    'phone': '0244000001',
                    'is_primary': True,
                    'is_fee_payer': True,
                }
            ],
        }


# ── Enrol Tests ───────────────────────────────────────────────────────────

class StudentEnrolTests(StudentAPITestCase):

    def test_enrol_student_success(self):
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['first_name'], 'Kofi')
        self.assertEqual(data['data']['last_name'], 'Asante')
        self.assertTrue(data['data']['student_id'].startswith('TA/'))

    def test_enrol_generates_student_id(self):
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()['data']['student_id'])

    def test_enrol_creates_guardian(self):
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.assertEqual(response.status_code, 201)
        student_id = response.json()['data']['id']
        self.assertEqual(StudentGuardian.objects.filter(student_id=student_id).count(), 1)

    def test_enrol_creates_class_history(self):
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.assertEqual(response.status_code, 201)
        student_id = response.json()['data']['id']
        self.assertEqual(
            StudentClassHistory.objects.filter(student_id=student_id, is_current=True).count(), 1
        )

    def test_enrol_with_emergency_contact(self):
        payload = {**self.enrol_payload, 'emergency_contacts': [
            {
                'full_name': 'Akua Asante',
                'relationship': 'aunt',
                'phone': '0244000099',
                'is_primary': True,
            }
        ]}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        student_id = response.json()['data']['id']
        self.assertEqual(EmergencyContact.objects.filter(student_id=student_id).count(), 1)

    def test_enrol_with_multiple_guardians(self):
        payload = {**self.enrol_payload, 'guardians': [
            {
                'first_name': 'Yaw',
                'last_name': 'Asante',
                'relationship': 'father',
                'phone': '0244000001',
                'is_primary': True,
                'is_fee_payer': True,
            },
            {
                'first_name': 'Akosua',
                'last_name': 'Asante',
                'relationship': 'mother',
                'phone': '0244000002',
                'is_primary': False,
                'is_fee_payer': False,
            },
        ]}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        student_id = response.json()['data']['id']
        self.assertEqual(StudentGuardian.objects.filter(student_id=student_id).count(), 2)

    def test_enrol_auto_assigns_primary_guardian(self):
        """If no guardian marked as primary, first one should be auto-assigned."""
        payload = {**self.enrol_payload, 'guardians': [
            {
                'first_name': 'Yaw',
                'last_name': 'Asante',
                'relationship': 'father',
                'phone': '0244000001',
                'is_primary': False,
                'is_fee_payer': False,
            }
        ]}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        student_id = response.json()['data']['id']
        self.assertTrue(
            StudentGuardian.objects.get(student_id=student_id).is_primary
        )

    def test_enrol_fails_without_guardian(self):
        payload = {**self.enrol_payload, 'guardians': []}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_enrol_fails_with_multiple_primary_guardians(self):
        payload = {**self.enrol_payload, 'guardians': [
            {
                'first_name': 'Yaw',
                'last_name': 'Asante',
                'relationship': 'father',
                'phone': '0244000001',
                'is_primary': True,
                'is_fee_payer': True,
            },
            {
                'first_name': 'Akosua',
                'last_name': 'Asante',
                'relationship': 'mother',
                'phone': '0244000002',
                'is_primary': True,
                'is_fee_payer': False,
            },
        ]}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_enrol_fails_without_required_fields(self):
        payload = {'first_name': 'Kofi'}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_enrol_fails_unauthenticated(self):
        self.client.credentials()
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.assertEqual(response.status_code, 401)

    def test_enrol_fails_with_classroom_from_other_school(self):
        other_year = AcademicYear.objects.create(
            school=self.other_school,
            name='2025/2026',
            start_date='2025-09-01',
            end_date='2026-07-31',
            is_current=True,
        )
        other_level = ClassLevel.objects.create(
            school=self.other_school,
            name='Primary 1',
            order=1,
        )
        other_classroom = ClassRoom.objects.create(
            school=self.other_school,
            academic_year=other_year,
            class_level=other_level,
            section_name='A',
            capacity=30,
        )
        payload = {**self.enrol_payload, 'current_class': other_classroom.id}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_enrol_fails_with_invalid_gender(self):
        payload = {**self.enrol_payload, 'gender': 'invalid'}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_enrol_fails_with_invalid_date_format(self):
        payload = {**self.enrol_payload, 'date_of_birth': '10-03-2012'}
        response = self.client.post('/api/v1/students/', payload, format='json')
        self.assertEqual(response.status_code, 400)


# ── List Tests ────────────────────────────────────────────────────────────

class StudentListTests(StudentAPITestCase):

    def setUp(self):
        super().setUp()
        # Enrol two students
        self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        payload2 = {**self.enrol_payload, 'first_name': 'Abena', 'last_name': 'Boateng'}
        self.client.post('/api/v1/students/', payload2, format='json')

    def test_list_students_success(self):
        response = self.client.get('/api/v1/students/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 2)

    def test_list_students_unauthenticated(self):
        self.client.credentials()
        response = self.client.get('/api/v1/students/')
        self.assertEqual(response.status_code, 401)

    def test_list_filters_by_classroom(self):
        response = self.client.get(f'/api/v1/students/?classroom={self.classroom.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 2)

    def test_list_filters_by_status(self):
        response = self.client.get('/api/v1/students/?status=active')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 2)

    def test_list_filters_by_search(self):
        response = self.client.get('/api/v1/students/?search=Abena')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_list_tenant_isolation(self):
        """Other school admin should see zero students."""
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/students/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Detail Tests ──────────────────────────────────────────────────────────

class StudentDetailTests(StudentAPITestCase):

    def setUp(self):
        super().setUp()
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.student_id = response.json()['data']['id']

    def test_get_student_detail(self):
        response = self.client.get(f'/api/v1/students/{self.student_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['id'], self.student_id)

    def test_get_student_detail_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(f'/api/v1/students/{self.student_id}/')
        self.assertEqual(response.status_code, 401)

    def test_get_student_not_found(self):
        response = self.client.get('/api/v1/students/99999/')
        self.assertEqual(response.status_code, 404)

    def test_get_student_from_other_school_returns_404(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(f'/api/v1/students/{self.student_id}/')
        self.assertEqual(response.status_code, 404)

    def test_patch_student_success(self):
        response = self.client.patch(
            f'/api/v1/students/{self.student_id}/',
            {'first_name': 'Kwame'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['first_name'], 'Kwame')

    def test_patch_student_cannot_change_student_id(self):
        response = self.client.patch(
            f'/api/v1/students/{self.student_id}/',
            {'student_id': 'FAKE/0000'},
            format='json'
        )
        # student_id is excluded from update serializer — should be ignored or rejected
        student = Student.objects.get(pk=self.student_id)
        self.assertNotEqual(student.student_id, 'FAKE/0000')

    def test_patch_student_unauthenticated(self):
        self.client.credentials()
        response = self.client.patch(
            f'/api/v1/students/{self.student_id}/',
            {'first_name': 'Kwame'},
            format='json'
        )
        self.assertEqual(response.status_code, 401)


# ── Guardian Tests ────────────────────────────────────────────────────────

class StudentGuardianTests(StudentAPITestCase):

    def setUp(self):
        super().setUp()
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.student_id = response.json()['data']['id']

    def test_list_guardians(self):
        response = self.client.get(f'/api/v1/students/{self.student_id}/guardians/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_add_guardian(self):
        response = self.client.post(
            f'/api/v1/students/{self.student_id}/guardians/',
            {
                'first_name': 'Akosua',
                'last_name': 'Asante',
                'relationship': 'mother',
                'phone': '0244000002',
                'is_primary': False,
                'is_fee_payer': False,
            },
            format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(StudentGuardian.objects.filter(student_id=self.student_id).count(), 2)

    def test_add_primary_guardian_demotes_existing(self):
        """Adding a new primary guardian should demote the existing one."""
        self.client.post(
            f'/api/v1/students/{self.student_id}/guardians/',
            {
                'first_name': 'Akosua',
                'last_name': 'Asante',
                'relationship': 'mother',
                'phone': '0244000002',
                'is_primary': True,
                'is_fee_payer': False,
            },
            format='json'
        )
        self.assertEqual(
            StudentGuardian.objects.filter(student_id=self.student_id, is_primary=True).count(), 1
        )

    def test_list_guardians_for_nonexistent_student(self):
        response = self.client.get('/api/v1/students/99999/guardians/')
        self.assertEqual(response.status_code, 404)

    def test_guardian_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(f'/api/v1/students/{self.student_id}/guardians/')
        self.assertEqual(response.status_code, 404)


# ── Emergency Contact Tests ───────────────────────────────────────────────

class StudentEmergencyContactTests(StudentAPITestCase):

    def setUp(self):
        super().setUp()
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.student_id = response.json()['data']['id']

    def test_add_emergency_contact(self):
        response = self.client.post(
            f'/api/v1/students/{self.student_id}/emergency-contacts/',
            {
                'full_name': 'Akua Mensah',
                'relationship': 'aunt',
                'phone': '0244000099',
                'is_primary': True,
            },
            format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EmergencyContact.objects.filter(student_id=self.student_id).count(), 1)

    def test_add_emergency_contact_missing_required_fields(self):
        response = self.client.post(
            f'/api/v1/students/{self.student_id}/emergency-contacts/',
            {'full_name': 'Akua Mensah'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_add_emergency_contact_nonexistent_student(self):
        response = self.client.post(
            '/api/v1/students/99999/emergency-contacts/',
            {
                'full_name': 'Akua Mensah',
                'relationship': 'aunt',
                'phone': '0244000099',
                'is_primary': True,
            },
            format='json'
        )
        self.assertEqual(response.status_code, 404)

    def test_emergency_contact_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(
            f'/api/v1/students/{self.student_id}/emergency-contacts/',
            {
                'full_name': 'Akua Mensah',
                'relationship': 'aunt',
                'phone': '0244000099',
                'is_primary': True,
            },
            format='json'
        )
        self.assertEqual(response.status_code, 404)


# ── Class History Tests ───────────────────────────────────────────────────

class StudentClassHistoryTests(StudentAPITestCase):

    def setUp(self):
        super().setUp()
        response = self.client.post('/api/v1/students/', self.enrol_payload, format='json')
        self.student_id = response.json()['data']['id']

    def test_get_class_history(self):
        response = self.client.get(f'/api/v1/students/{self.student_id}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_class_history_nonexistent_student(self):
        response = self.client.get('/api/v1/students/99999/history/')
        self.assertEqual(response.status_code, 404)

    def test_class_history_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(f'/api/v1/students/{self.student_id}/history/')
        self.assertEqual(response.status_code, 404)