import random
from datetime import date, timedelta

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Subject, ClassRoom, SubjectAssignment, Term
from apps.accounts.models import User
from apps.core.models import Position
from apps.teachers.models import StaffProfile
from apps.tenants.models import School, Branch, SchoolMember


MALE_GIVEN_NAMES = [
    'Nana', 'Kojo', 'Emmanuel', 'Michael', 'Samuel', 'Daniel', 'Joseph',
    'Isaac', 'Prince', 'Justice', 'Nicholas', 'Bright', 'Solomon',
    'Frank', 'Eric', 'Richard', 'Godfred', 'Ebenezer', 'Kelvin', 'Enoch',
]
FEMALE_GIVEN_NAMES = [
    'Comfort', 'Gifty', 'Grace', 'Vida', 'Abigail', 'Sarah', 'Mary',
    'Priscilla', 'Patience', 'Rebecca', 'Joyce', 'Linda', 'Diana',
    'Belinda', 'Serwaa', 'Adoma', 'Boatemaa', 'Charity', 'Faustina', 'Naomi',
]
SURNAMES = [
    'Mensah', 'Owusu', 'Asante', 'Boateng', 'Osei', 'Agyeman', 'Amoako',
    'Appiah', 'Darko', 'Frimpong', 'Adjei', 'Ofori', 'Gyasi', 'Sarpong',
    'Yeboah', 'Acheampong', 'Wiredu', 'Antwi', 'Kusi', 'Baah',
    'Tetteh', 'Aryee', 'Ashong', 'Lartey', 'Odoi', 'Nortey', 'Quaye',
]
HOME_TOWNS = [
    'Kumasi', 'Accra', 'Tamale', 'Cape Coast', 'Sunyani', 'Koforidua',
    'Ho', 'Sekondi', 'Takoradi', 'Techiman', 'Obuasi', 'Tema', 'Winneba',
]
MOTHER_TONGUES_UNUSED = []  # not used for staff
REGIONS = ['greater_accra', 'ashanti', 'central', 'eastern', 'western', 'volta', 'northern', 'bono']
PHONE_PREFIXES = ['024', '054', '055', '020', '059', '026', '027', '050', '057']
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown']
BANK_CHOICES = ['gcb', 'ecobank', 'absa', 'stanbic', 'zenith', 'uba', 'fidelity', 'calbank']
TITLE_CHOICES_MALE = ['mr', 'dr', 'prof', 'rev', 'pastor', 'alhaji', 'hon']
TITLE_CHOICES_FEMALE = ['mrs', 'miss', 'madam', 'dr', 'prof', 'hajia', 'hon']

TEACHING_SUBJECTS = [
    'Mathematics', 'English Language', 'Social Studies',
    'Religious and Moral Studies', 'Integrated Science', 'ICT',
    'Ghanaian Language', 'Creative Arts', 'Career Technology',
]

NON_TEACHING_POSITIONS = [
    'Bursar', 'Librarian', 'School Nurse', 'Administrative Assistant',
    'Security Officer', 'Groundskeeper', 'IT Support Officer',
    'Front Desk Officer', 'Cook', 'Cleaner', 'Driver', 'Store Keeper',
]


def random_phone():
    prefix = random.choice(PHONE_PREFIXES)
    suffix = ''.join(random.choices('0123456789', k=7))
    return f"{prefix}{suffix}"


class Command(BaseCommand):
    help = "Generate detailed test staff (teaching + non-teaching) with subject assignments across all classes."

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, default=4)
        parser.add_argument('--count', type=int, default=35)
        parser.add_argument('--teaching-count', type=int, default=22)
        parser.add_argument('--no-photos', action='store_true')

    def handle(self, *args, **options):
        school = School.objects.get(id=options['school_id'])
        branch = Branch.objects.filter(school=school).first()
        total = options['count']
        teaching_count = options['teaching_count']
        non_teaching_count = total - teaching_count

        self._ensure_subjects(school)
        subjects = list(Subject.objects.filter(school=school))
        classrooms = list(ClassRoom.objects.filter(school=school, is_active=True))
        current_term = Term.objects.filter(academic_year__school=school, is_current=True).first()

        if not classrooms:
            self.stderr.write("No classrooms found — run generate_test_students first.")
            return

        male_photos, female_photos = [], []
        if not options['no_photos']:
            self.stdout.write("Fetching placeholder photos...")
            male_photos = self._fetch_photos('male', total // 2 + 10)
            female_photos = self._fetch_photos('female', total // 2 + 10)
            self.stdout.write(f"  Got {len(male_photos)} male, {len(female_photos)} female photos.")

        created = 0

       # ── Teaching staff ──────────────────────────────────────────
        # Build the full grid of (classroom, subject) slots that need a
        # teacher, shuffle it, then hand slots out round-robin so no two
        # teachers can ever collide on the same classroom+subject.
        all_slots = [(c, s) for c in classrooms for s in subjects]
        random.shuffle(all_slots)
        slots_per_teacher = max(1, len(all_slots) // teaching_count)

        slot_index = 0
        for i in range(teaching_count):
            gender = random.choice(['male', 'female'])
            with transaction.atomic():
                staff, member = self._create_staff(
                    school, branch, gender, category='teaching',
                    position_name=random.choice(TEACHING_SUBJECTS) + ' Teacher',
                )
                self._attach_photo(staff, gender, male_photos, female_photos)

                # Last teacher absorbs any remainder slots
                is_last = (i == teaching_count - 1)
                end_index = len(all_slots) if is_last else slot_index + slots_per_teacher
                my_slots = all_slots[slot_index:end_index]
                slot_index = end_index

                assigned_subjects = set()
                for classroom, subject in my_slots:
                    SubjectAssignment.objects.get_or_create(
                        classroom=classroom, subject=subject, term=current_term,
                        defaults={'teacher': member, 'periods_per_week': random.randint(3, 6)},
                    )
                    assigned_subjects.add(subject)

                if assigned_subjects:
                    staff.subject_specializations.set(assigned_subjects)
            created += 1

        # ── Non-teaching staff ──────────────────────────────────────
        for i in range(non_teaching_count):
            gender = random.choice(['male', 'female'])
            with transaction.atomic():
                staff, member = self._create_staff(
                    school, branch, gender, category='non_teaching',
                    position_name=random.choice(NON_TEACHING_POSITIONS),
                )
                self._attach_photo(staff, gender, male_photos, female_photos)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created} staff ({teaching_count} teaching, {non_teaching_count} non-teaching)."
        ))

    def _ensure_subjects(self, school):
        for name in TEACHING_SUBJECTS:
            Subject.objects.get_or_create(school=school, name=name)

    def _fetch_photos(self, gender, count):
        photos = []
        try:
            resp = requests.get(
                f"https://randomuser.me/api/?results={count}&gender={gender}&inc=picture&noinfo",
                timeout=20,
            )
            resp.raise_for_status()
            for r in resp.json().get('results', []):
                img_resp = requests.get(r['picture']['large'], timeout=10)
                if img_resp.status_code == 200:
                    photos.append(img_resp.content)
        except Exception as e:
            self.stderr.write(f"Photo fetch failed for {gender}: {e}")
        return photos

    def _attach_photo(self, staff, gender, male_photos, female_photos):
        photo_list = male_photos if gender == 'male' else female_photos
        if photo_list:
            photo_bytes = photo_list.pop()
            safe_id = staff.staff_id.replace('/', '-')
            staff.photo.save(f"{safe_id}.jpg", ContentFile(photo_bytes), save=True)

    def _create_staff(self, school, branch, gender, category, position_name):
        given_pool = MALE_GIVEN_NAMES if gender == 'male' else FEMALE_GIVEN_NAMES
        title_pool = TITLE_CHOICES_MALE if gender == 'male' else TITLE_CHOICES_FEMALE

        first_name = random.choice(given_pool)
        last_name = random.choice(SURNAMES)
        today = timezone.localdate()
        age = random.randint(24, 58)
        dob = date(today.year - age, random.randint(1, 12), random.randint(1, 28))

        position, _ = Position.objects.get_or_create(name=position_name)

        # Placeholder-only User + SchoolMember — never intended to log in
        unique_suffix = ''.join(random.choices('0123456789', k=6))
        placeholder_email = f"staff.{unique_suffix}@placeholder.ilimi.local"
        user = User.objects.create_user(
            email=placeholder_email,
            password=User.objects.make_random_password() if hasattr(User.objects, 'make_random_password') else 'PlaceholderNotForLogin!123',
            first_name=first_name,
            last_name=last_name,
        )

        staff = StaffProfile.objects.create(
            school=school,
            branch=branch,
            user=user,
            title=random.choice(title_pool),
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            gender=gender,
            nationality='Ghanaian',
            marital_status=random.choice(['single', 'married', 'married', 'divorced']),
            number_of_dependants=random.randint(0, 4),
            blood_group=random.choice(BLOOD_GROUPS),
            phone=random_phone(),
            whatsapp_number=random_phone(),
            secondary_phone=random_phone() if random.random() < 0.4 else '',
            email=f"{first_name.lower()}.{last_name.lower()}{unique_suffix[:3]}@gmail.com",
            residential_address=f"House No. {random.randint(1, 300)}, {random.choice(HOME_TOWNS)}",
            digital_address=f"GA-{random.randint(100,999)}-{random.randint(1000,9999)}",
            city=random.choice(HOME_TOWNS),
            region=random.choice(REGIONS),
            ghana_card_number='',
            ssnit_number=f"C{random.randint(100000000000, 999999999999)}",
            ntc_license_number=f"NTC-{random.randint(2005,2023)}-{random.randint(1000,9999)}" if category == 'teaching' else '',
            highest_qualification=random.choice(['bachelors', 'diploma', 'hnd', 'masters', 'wassce']),
            institution_attended=random.choice(['University of Ghana', 'KNUST', 'University of Cape Coast', 'Accra College of Education', 'Wesley College of Education']),
            years_of_experience=random.randint(1, 25),
            employment_type=random.choice(['permanent', 'permanent', 'contract', 'national_service']),
            time_commitment='full_time' if random.random() < 0.85 else 'part_time',
            staff_category=category,
            position=position,
            salary_grade=f"GES-{random.randint(10,20)}",
            date_of_first_appointment=today - timedelta(days=random.randint(365, 365*15)),
            date_joined_school=today - timedelta(days=random.randint(30, 365*6)),
            is_on_probation=random.random() < 0.1,
            is_head_of_department=random.random() < 0.08,
            leave_entitlement_days=21,
            leave_days_taken=random.randint(0, 18),
            bank_name=random.choice(BANK_CHOICES),
            bank_branch=f"{random.choice(HOME_TOWNS)} Branch",
            bank_account_number=''.join(random.choices('0123456789', k=13)),
            momo_number=random_phone(),
            next_of_kin_name=f"{random.choice(MALE_GIVEN_NAMES + FEMALE_GIVEN_NAMES)} {last_name}",
            next_of_kin_relationship=random.choice(['Spouse', 'Sibling', 'Parent']),
            next_of_kin_phone=random_phone(),
            next_of_kin_address=f"House No. {random.randint(1, 300)}, {random.choice(HOME_TOWNS)}",
        )

        member = SchoolMember.objects.create(
            user=user, school=school, branch=branch,
            role='teacher' if category == 'teaching' else 'accountant',
            position_title=position_name,
            is_active=True, has_seen_tour=True,
        )

        return staff, member