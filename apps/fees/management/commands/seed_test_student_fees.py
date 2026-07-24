import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.tenants.models import School
from apps.academics.models import AcademicYear
from apps.students.models import Student
from apps.fees.models import FeeStructure, StudentFee


class Command(BaseCommand):
    help = "Assign real StudentFee records to active students, matching existing FeeStructures for their class level."

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, default=4)

    def handle(self, *args, **options):
        school = School.objects.get(id=options['school_id'])
        year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not year:
            self.stderr.write("No current academic year for this school.")
            return
        term = year.terms.filter(is_current=True).first()
        if not term:
            self.stderr.write("No current term for this school.")
            return

        students = Student.objects.filter(
            school=school, status='active'
        ).select_related('current_class__class_level')
        structures = FeeStructure.objects.filter(
            school=school, term=term, is_active=True
        ).select_related('class_level')

        created_fees = 0
        for student in students:
            if not student.current_class:
                continue
            matching = structures.filter(class_level=student.current_class.class_level)
            for structure in matching:
                paid_state = random.choice(['none', 'partial', 'full'])
                amount_paid = Decimal('0')
                if paid_state == 'partial':
                    amount_paid = structure.amount * Decimal('0.5')
                elif paid_state == 'full':
                    amount_paid = structure.amount

                fee, created = StudentFee.objects.get_or_create(
                    school=school, student=student,
                    fee_structure=structure, term=term,
                    defaults={
                        'amount_charged': structure.amount,
                        'amount_paid': amount_paid,
                    },
                )
                if created:
                    fee.update_status()
                    created_fees += 1

        self.stdout.write(self.style.SUCCESS(f"{created_fees} student fees created."))