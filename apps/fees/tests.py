from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.accounts.models import User
from apps.tenants.models import School, Branch, SchoolMember
from apps.academics.models import AcademicYear, Term, ClassLevel, ClassRoom
from apps.students.models import Student, Guardian, StudentGuardian
from apps.fees.models import (
    FeeType,
    FeeStructure,
    StudentFee,
    Payment,
    InstallmentPlan,
    Installment,
)


# ── Base Setup ────────────────────────────────────────────────────────────

class FeeAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # School
        self.school = School.objects.create(
            name='Test Academy',
            email='school@test.com',
        )
        self.branch = Branch.objects.create(
            school=self.school,
            name='Main Branch',
        )

        # Admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='Testpass123!',
            first_name='Admin',
            last_name='User',
        )
        SchoolMember.objects.create(
            user=self.admin,
            school=self.school,
            branch=self.branch,
            role='school_admin',
            is_active=True,
        )

        # Other school for tenant isolation
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

        # Academics
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

        # Student
        self.student = Student.objects.create(
            school=self.school,
            branch=self.branch,
            first_name='Kofi',
            last_name='Asante',
            date_of_birth='2012-03-10',
            gender='male',
            current_class=self.classroom,
        )

        # Fee type and structure
        self.fee_type = FeeType.objects.create(
            school=self.school,
            name='Tuition',
            description='Termly tuition fee',
        )
        self.fee_structure = FeeStructure.objects.create(
            school=self.school,
            fee_type=self.fee_type,
            class_level=self.class_level,
            term=self.term,
            amount=500.00,
            is_mandatory=True,
        )

        # Authenticate
        token = RefreshToken.for_user(self.admin).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


# ── Fee Type Tests ────────────────────────────────────────────────────────

class FeeTypeTests(FeeAPITestCase):

    def test_list_fee_types(self):
        response = self.client.get('/api/v1/fees/types/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_create_fee_type(self):
        response = self.client.post('/api/v1/fees/types/', {
            'name': 'PTA',
            'description': 'PTA levy',
            'is_active': True,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['name'], 'PTA')

    def test_create_fee_type_duplicate_name(self):
        response = self.client.post('/api/v1/fees/types/', {
            'name': 'Tuition',
            'is_active': True,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_fee_type_unauthenticated(self):
        self.client.credentials()
        response = self.client.post('/api/v1/fees/types/', {
            'name': 'Sports',
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_get_fee_type_detail(self):
        response = self.client.get(f'/api/v1/fees/types/{self.fee_type.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['name'], 'Tuition')

    def test_get_fee_type_not_found(self):
        response = self.client.get('/api/v1/fees/types/99999/')
        self.assertEqual(response.status_code, 404)

    def test_patch_fee_type(self):
        response = self.client.patch(
            f'/api/v1/fees/types/{self.fee_type.id}/',
            {'description': 'Updated description'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['description'], 'Updated description')

    def test_fee_type_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/fees/types/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Fee Structure Tests ───────────────────────────────────────────────────

class FeeStructureTests(FeeAPITestCase):

    def test_list_fee_structures(self):
        response = self.client.get('/api/v1/fees/structures/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_create_fee_structure(self):
        fee_type2 = FeeType.objects.create(
            school=self.school, name='PTA'
        )
        response = self.client.post('/api/v1/fees/structures/', {
            'fee_type': fee_type2.id,
            'class_level': self.class_level.id,
            'term': self.term.id,
            'amount': '150.00',
            'is_mandatory': True,
            'is_active': True,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['amount'], '150.00')

    def test_create_fee_structure_duplicate(self):
        response = self.client.post('/api/v1/fees/structures/', {
            'fee_type': self.fee_type.id,
            'class_level': self.class_level.id,
            'term': self.term.id,
            'amount': '500.00',
            'is_mandatory': True,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_filter_fee_structures_by_term(self):
        response = self.client.get(f'/api/v1/fees/structures/?term={self.term.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_filter_fee_structures_by_class_level(self):
        response = self.client.get(f'/api/v1/fees/structures/?class_level={self.class_level.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_patch_fee_structure(self):
        response = self.client.patch(
            f'/api/v1/fees/structures/{self.fee_structure.id}/',
            {'amount': '600.00'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['amount'], '600.00')

    def test_fee_structure_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/fees/structures/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Student Fee Tests ─────────────────────────────────────────────────────

class StudentFeeTests(FeeAPITestCase):

    def setUp(self):
        super().setUp()
        self.student_fee = StudentFee.objects.create(
            school=self.school,
            student=self.student,
            fee_structure=self.fee_structure,
            term=self.term,
            amount_charged=500.00,
            due_date='2025-10-01',
        )

    def test_list_student_fees(self):
        response = self.client.get('/api/v1/fees/student-fees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_create_student_fee(self):
        fee_type2 = FeeType.objects.create(school=self.school, name='PTA')
        structure2 = FeeStructure.objects.create(
            school=self.school,
            fee_type=fee_type2,
            class_level=self.class_level,
            term=self.term,
            amount=100.00,
        )
        response = self.client.post('/api/v1/fees/student-fees/', {
            'student': self.student.id,
            'fee_structure': structure2.id,
            'term': self.term.id,
            'amount_charged': '100.00',
            'due_date': '2025-10-01',
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_create_student_fee_duplicate(self):
        response = self.client.post('/api/v1/fees/student-fees/', {
            'student': self.student.id,
            'fee_structure': self.fee_structure.id,
            'term': self.term.id,
            'amount_charged': '500.00',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_filter_student_fees_by_student(self):
        response = self.client.get(f'/api/v1/fees/student-fees/?student={self.student.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_filter_student_fees_by_status(self):
        response = self.client.get('/api/v1/fees/student-fees/?status=unpaid')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_get_student_fee_detail(self):
        response = self.client.get(f'/api/v1/fees/student-fees/{self.student_fee.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['id'], self.student_fee.id)

    def test_patch_student_fee_waiver(self):
        response = self.client.patch(
            f'/api/v1/fees/student-fees/{self.student_fee.id}/',
            {'status': 'waived', 'waiver_reason': 'Scholarship'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'waived')

    def test_student_fee_balance(self):
        response = self.client.get(f'/api/v1/fees/student-fees/{self.student_fee.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['balance'], '500.00')

    def test_student_fee_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/fees/student-fees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Payment Tests ─────────────────────────────────────────────────────────

class PaymentTests(FeeAPITestCase):

    def setUp(self):
        super().setUp()
        self.student_fee = StudentFee.objects.create(
            school=self.school,
            student=self.student,
            fee_structure=self.fee_structure,
            term=self.term,
            amount_charged=500.00,
            due_date='2025-10-01',
        )

    def test_record_cash_payment(self):
        response = self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '200.00',
            'payment_method': 'cash',
            'payment_date': '2025-09-15',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()['data']
        self.assertIn('RCP', data['receipt_number'])
        self.assertEqual(data['amount'], '200.00')

    def test_record_momo_payment(self):
        response = self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '300.00',
            'payment_method': 'momo',
            'momo_provider': 'mtn',
            'momo_number': '0244000001',
            'momo_transaction_id': 'MTN123456',
            'payment_date': '2025-09-15',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['momo_provider'], 'mtn')

    def test_payment_updates_student_fee_status(self):
        self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '500.00',
            'payment_method': 'cash',
            'payment_date': '2025-09-15',
        }, format='json')
        self.student_fee.refresh_from_db()
        self.assertEqual(self.student_fee.status, 'paid')

    def test_partial_payment_sets_partial_status(self):
        self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '200.00',
            'payment_method': 'cash',
            'payment_date': '2025-09-15',
        }, format='json')
        self.student_fee.refresh_from_db()
        self.assertEqual(self.student_fee.status, 'partial')

    def test_payment_fails_exceeds_balance(self):
        response = self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '600.00',
            'payment_method': 'cash',
            'payment_date': '2025-09-15',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_payment_fails_zero_amount(self):
        response = self.client.post('/api/v1/fees/payments/', {
            'student_fee': self.student_fee.id,
            'amount': '0.00',
            'payment_method': 'cash',
            'payment_date': '2025-09-15',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_list_payments(self):
        Payment.objects.create(
            school=self.school,
            student_fee=self.student_fee,
            amount=200.00,
            payment_method='cash',
            payment_date='2025-09-15',
            status='successful',
        )
        response = self.client.get('/api/v1/fees/payments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_filter_payments_by_student(self):
        Payment.objects.create(
            school=self.school,
            student_fee=self.student_fee,
            amount=200.00,
            payment_method='cash',
            payment_date='2025-09-15',
            status='successful',
        )
        response = self.client.get(f'/api/v1/fees/payments/?student={self.student.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_get_payment_detail(self):
        payment = Payment.objects.create(
            school=self.school,
            student_fee=self.student_fee,
            amount=200.00,
            payment_method='cash',
            payment_date='2025-09-15',
            status='successful',
        )
        response = self.client.get(f'/api/v1/fees/payments/{payment.id}/')
        self.assertEqual(response.status_code, 200)

    def test_payment_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/fees/payments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)


# ── Installment Plan Tests ────────────────────────────────────────────────

class InstallmentPlanTests(FeeAPITestCase):

    def setUp(self):
        super().setUp()
        self.student_fee = StudentFee.objects.create(
            school=self.school,
            student=self.student,
            fee_structure=self.fee_structure,
            term=self.term,
            amount_charged=500.00,
            due_date='2025-10-01',
        )

    def test_create_installment_plan(self):
        response = self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 3,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        data = response.json()['data']
        self.assertEqual(data['number_of_installments'], 3)
        self.assertEqual(len(data['installments']), 3)

    def test_installment_plan_auto_generates_schedule(self):
        response = self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 2,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        installments = response.json()['data']['installments']
        self.assertEqual(len(installments), 2)
        self.assertEqual(installments[0]['installment_number'], 1)
        self.assertEqual(installments[1]['installment_number'], 2)

    def test_create_installment_plan_fails_minimum_installments(self):
        response = self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_installment_plan_fails_duplicate(self):
        self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 3,
        }, format='json')
        response = self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 2,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_installment_plan_fails_for_paid_fee(self):
        self.student_fee.status = 'paid'
        self.student_fee.save()
        response = self.client.post('/api/v1/fees/installments/', {
            'student_fee': self.student_fee.id,
            'number_of_installments': 3,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_list_installment_plans(self):
        InstallmentPlan.objects.create(
            student_fee=self.student_fee,
            number_of_installments=3,
        )
        response = self.client.get('/api/v1/fees/installments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 1)

    def test_get_installment_plan_detail(self):
        plan = InstallmentPlan.objects.create(
            student_fee=self.student_fee,
            number_of_installments=3,
        )
        response = self.client.get(f'/api/v1/fees/installments/{plan.id}/')
        self.assertEqual(response.status_code, 200)

    def test_installment_plan_tenant_isolation(self):
        token = RefreshToken.for_user(self.other_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/fees/installments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['count'], 0)