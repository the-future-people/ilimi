from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.tenants.models import School, Branch, SchoolMember
from apps.academics.models import AcademicYear, ClassLevel, Subject
from apps.teachers.models import StaffProfile


# ── Base Setup ────────────────────────────────────────────────────────────

class StaffAPITestCase(TestCase):
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

        # Create a subject for specialization tests
        self.subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            code='MATH',
            subject_type='core',
        )

        # Authenticate
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Base create payload
        self.create_payload = {
            'first_name': 'Ama',
            'last_name': 'Owusu',
            'gender': 'female',
            'phone': '0244000001',
            'employment_type': 'permanent',
            'date_joined_school': '2024-09-01',
            'highest_qualification': 'bachelors',
            'years_of_experience': 3,
        }


# ── Create Tests ──────────────────────────────────────────────────────────

class StaffCreateTests(StaffAPITestCase):

    def test_create_staff_success(self):
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['first_name'], 'Ama')
        self.assertEqual(data['data']['last_name'], 'Owusu')
        self.assertTrue(data['data']['staff_id'].startswith('TA/STF/'))

    def test_create_staff_generates_staff_id(self):
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()['data']['staff_id'])

    def test_create_staff_sequential_ids(self):
        self.client.post('/api/v1/staff/', self.create_payload, format='json')
        payload2 = {**self.create_payload, 'phone': '0244000002'}
        response = self.client.post('/api/v1/staff/', payload2, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('0002', response.json()['data']['staff_id'])

    def test_create_staff_with_subject_specializations(self):
        payload = {**self.create_payload, 'subject_specializations': [self.subject.id]}
        response = self.client.post('/api/v1/staff/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()['data']['subject_specializations']), 1)

    def test_create_staff_default_leave_entitlement(self):
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['leave_entitlement_days'], 21)
        self.assertEqual(response.json()['data']['leave_days_remaining'], 21)

    def test_create_staff_with_banking_details(self):
        payload = {
            **self.create_payload,
            'bank_name': 'gcb',
            'bank_branch': 'Accra Central',
            'bank_account_number': '1234567890',
            'momo_number': '0244000001',
        }
        response = self.client.post('/api/v1/staff/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['bank_name'], 'gcb')

    def test_create_staff_with_next_of_kin(self):
        payload = {
            **self.create_payload,
            'next_of_kin_name': 'Kofi Owusu',
            'next_of_kin_relationship': 'Husband',
            'next_of_kin_phone': '0244999888',
        }
        response = self.client.post('/api/v1/staff/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['next_of_kin_name'], 'Kofi Owusu')

    def test_create_staff_fails_duplicate_phone(self):
        self.client.post('/api/v1/staff/', self.create_payload, format='json')
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_staff_fails_duplicate_ghana_card(self):
        payload = {**self.create_payload, 'ghana_card_number': 'GHA-123456789-0'}
        self.client.post('/api/v1/staff/', payload, format='json')
        payload2 = {**self.create_payload, 'phone': '0244000002', 'ghana_card_number': 'GHA-123456789-0'}
        response = self.client.post('/api/v1/staff/', payload2, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_staff_fails_duplicate_ssnit(self):
        payload = {**self.create_payload, 'ssnit_number': 'SSNIT-001'}
        self.client.post('/api/v1/staff/', payload, format='json')
        payload2 = {**self.create_payload, 'phone': '0244000002', 'ssnit_number': 'SSNIT-001'}
        response = self.client.post('/api/v1/staff/', payload2, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_staff_fails_without_required_fields(self):
        response = self.client.post('/api/v1/staff/', {'first_name': 'Ama'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_staff_fails_unauthenticated(self):
        self.client.credentials()
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.assertEqual(response.status_code, 401)

    def test_create_staff_fails_invalid_gender(self):
        payload = {**self.create_payload, 'gender': 'invalid'}
        response = self.client.post('/api/v1/staff/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_staff_fails_invalid_employment_type(self):
        payload = {**self.create_payload, 'employment_type': 'invalid'}
        response = self.client.post('/api/v1/staff/', payload, format='json')
        self.assertEqual(response.status_code, 400)


# ── List Tests ────────────────────────────────────────────────────────────

class StaffListTests(StaffAPITestCase):

    def setUp(self):
        super().setUp()
        self.client.post('/api/v1/staff/', self.create_payload, format='json')
        payload2 = {
            **self.create_payload,
            'first_name': 'Kofi',
            'last_name': 'Mensah',
            'phone': '0244000002',
            'employment_type': 'contract',
        }
        self.client.post('/api/v1/staff/', payload2, format='json')

    def test_list_staff_success(self):
        response = self.client.get('/api/v1/staff/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 2)

    def test_list_staff_unauthenticated(self):
        self.client.credentials()
        response = self.client.get('/api/v1/staff/')
        self.assertEqual(response.status_code, 401)

    def test_list_filters_by_status(self):
        response = self.client.get('/api/v1/staff/?status=active')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 2)

    def test_list_filters_by_employment_type(self):
        response = self.client.get('/api/v1/staff/?employment_type=contract')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_list_filters_by_search(self):
        response = self.client.get('/api/v1/staff/?search=Kofi')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_list_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/staff/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Detail Tests ──────────────────────────────────────────────────────────

class StaffDetailTests(StaffAPITestCase):

    def setUp(self):
        super().setUp()
        response = self.client.post('/api/v1/staff/', self.create_payload, format='json')
        self.staff_id = response.json()['data']['id']

    def test_get_staff_detail(self):
        response = self.client.get(f'/api/v1/staff/{self.staff_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['id'], self.staff_id)

    def test_get_staff_detail_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(f'/api/v1/staff/{self.staff_id}/')
        self.assertEqual(response.status_code, 401)

    def test_get_staff_not_found(self):
        response = self.client.get('/api/v1/staff/99999/')
        self.assertEqual(response.status_code, 404)

    def test_get_staff_from_other_school_returns_404(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(f'/api/v1/staff/{self.staff_id}/')
        self.assertEqual(response.status_code, 404)

    def test_patch_staff_success(self):
        response = self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'first_name': 'Akosua'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['first_name'], 'Akosua')

    def test_patch_staff_cannot_change_staff_id(self):
        self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'staff_id': 'FAKE/STF/0000'},
            format='json'
        )
        staff = StaffProfile.objects.get(pk=self.staff_id)
        self.assertNotEqual(staff.staff_id, 'FAKE/STF/0000')

    def test_patch_staff_update_leave_days(self):
        response = self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'leave_days_taken': 5},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['leave_days_remaining'], 16)

    def test_patch_staff_update_status(self):
        response = self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'status': 'on_leave'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'on_leave')

    def test_patch_staff_unauthenticated(self):
        self.client.credentials()
        response = self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'first_name': 'Akosua'},
            format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_patch_staff_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.patch(
            f'/api/v1/staff/{self.staff_id}/',
            {'first_name': 'Hacker'},
            format='json'
        )
        self.assertEqual(response.status_code, 404)