import random
from datetime import date, timedelta

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassRoom, AcademicYear
from apps.core.models import Occupation
from apps.students.models import Student, Guardian, StudentGuardian, StudentClassHistory
from apps.tenants.models import School, Branch


MALE_DAY_NAMES = {
    0: 'Kwadwo', 1: 'Kwabena', 2: 'Kwaku', 3: 'Yaw',
    4: 'Kofi', 5: 'Kwame', 6: 'Kwasi',
}
FEMALE_DAY_NAMES = {
    0: 'Adwoa', 1: 'Abena', 2: 'Akua', 3: 'Yaa',
    4: 'Afua', 5: 'Ama', 6: 'Akosua',
}

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
    'Addo', 'Kotey', 'Agbeko', 'Kudjoe', 'Dogbe', 'Amenyo', 'Fiawoo',
    'Mahama', 'Alhassan', 'Iddrisu', 'Seidu', 'Abdulai', 'Fuseini', 'Yakubu',
]

HOME_TOWNS = [
    'Kumasi', 'Accra', 'Tamale', 'Cape Coast', 'Sunyani', 'Koforidua',
    'Ho', 'Sekondi', 'Takoradi', 'Techiman', 'Obuasi', 'Tema', 'Winneba',
    'Bolgatanga', 'Wa', 'Nkawkaw', 'Dunkwa', 'Berekum', 'Elmina', 'Axim',
]

MOTHER_TONGUES = ['Twi', 'Fante', 'Ga', 'Ewe', 'Dagbani', 'Dagaare', 'Hausa', 'Nzema', 'Gonja']

RELIGIONS = ['christian'] * 7 + ['muslim'] * 2 + ['traditionalist'] + ['none']

REGIONS = [
    'greater_accra', 'ashanti', 'central', 'eastern', 'western',
    'volta', 'northern', 'bono',
]

OCCUPATIONS = [
    'Teacher', 'Trader', 'Farmer', 'Nurse', 'Driver', 'Seamstress',
    'Carpenter', 'Electrician', 'Civil Servant', 'Businessman',
    'Businesswoman', 'Mechanic', 'Accountant', 'Police Officer',
    'Banker', 'Hairdresser', 'Fisherman', 'Mason', 'Tailor', 'Caterer',
]

PHONE_PREFIXES = ['024', '054', '055', '020', '059', '026', '027', '050', '057']

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown']

GUARDIAN_RELATIONSHIPS_MINIMAL = ['father', 'mother', 'guardian', 'aunt', 'uncle', 'grandmother', 'grandfather']

TALENTS = ['Football', 'Singing', 'Drawing', 'Storytelling', 'Athletics', 'Drumming', 'Dancing', 'Debate', '']


def random_phone():
    prefix = random.choice(PHONE_PREFIXES)
    suffix = ''.join(random.choices('0123456789', k=7))
    return f"{prefix}{suffix}"


class Command(BaseCommand):
    help = "Generate test student data across Primary 1 - JHS 3 with Ghanaian names and real placeholder photos."

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, default=4)
        parser.add_argument('--count', type=int, default=250)
        parser.add_argument('--full-count', type=int, default=150)
        parser.add_argument('--no-photos', action='store_true')

    def handle(self, *args, **options):
        school = School.objects.get(id=options['school_id'])
        branch = Branch.objects.filter(school=school).first()
        academic_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        total = options['count']
        full_count = options['full_count']

        classrooms = list(
            ClassRoom.objects.filter(school=school, is_active=True)
            .select_related('class_level')
            .order_by('class_level__order')
        )
        if not classrooms:
            self.stderr.write("No classrooms found for this school.")
            return

        male_photos, female_photos = [], []
        if not options['no_photos']:
            self.stdout.write("Fetching placeholder photos (this can take a few minutes)...")
            male_photos = self._fetch_photos('male', total // 2 + 20)
            female_photos = self._fetch_photos('female', total // 2 + 20)
            self.stdout.write(f"  Got {len(male_photos)} male, {len(female_photos)} female photos.")

        created = 0
        for i in range(total):
            classroom = classrooms[i % len(classrooms)]
            is_full = i < full_count
            gender = random.choice(['male', 'female'])

            with transaction.atomic():
                student = self._create_student(school, branch, classroom, gender, is_full)

                photo_list = male_photos if gender == 'male' else female_photos
                if photo_list:
                    photo_bytes = photo_list.pop()
                    safe_id = student.student_id.replace('/', '-')
                    student.photo.save(f"{safe_id}.jpg", ContentFile(photo_bytes), save=True)

                if academic_year:
                    StudentClassHistory.objects.create(
                        student=student, classroom=classroom,
                        academic_year=academic_year, is_current=True,
                    )

                self._create_guardians(student, is_full)

            created += 1
            if created % 25 == 0:
                self.stdout.write(f"  ...{created}/{total} created")

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} students across {len(classrooms)} classrooms."))

    def _fetch_photos(self, gender, count):
        photos = []
        try:
            resp = requests.get(
                f"https://randomuser.me/api/?results={count}&gender={gender}&inc=picture&noinfo",
                timeout=20,
            )
            resp.raise_for_status()
            for r in resp.json().get('results', []):
                url = r['picture']['large']
                img_resp = requests.get(url, timeout=10)
                if img_resp.status_code == 200:
                    photos.append(img_resp.content)
        except Exception as e:
            self.stderr.write(f"Photo fetch failed for {gender}: {e}")
        return photos

    def _create_student(self, school, branch, classroom, gender, is_full):
        order = classroom.class_level.order  # 0..8
        age = 6 + order
        today = timezone.localdate()
        birth_year = today.year - age
        dob = date(birth_year, random.randint(1, 12), random.randint(1, 28))

        day_name = (MALE_DAY_NAMES if gender == 'male' else FEMALE_DAY_NAMES)[dob.weekday()]
        given_pool = MALE_GIVEN_NAMES if gender == 'male' else FEMALE_GIVEN_NAMES

        if random.random() < 0.6:
            first_name = day_name
            middle_name = random.choice(given_pool) if random.random() < 0.5 else ''
        else:
            first_name = random.choice(given_pool)
            middle_name = day_name if random.random() < 0.7 else ''

        last_name = random.choice(SURNAMES)

        student = Student(
            school=school,
            branch=branch,
            current_class=classroom,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            date_of_birth=dob,
            gender=gender,
            nationality='Ghanaian',
            status='active',
            enrollment_date=today - timedelta(days=random.randint(0, 400)),
        )

        if is_full:
            student.place_of_birth = random.choice(HOME_TOWNS)
            student.home_town = random.choice(HOME_TOWNS)
            student.mother_tongue = random.choice(MOTHER_TONGUES)
            student.religion = random.choice(RELIGIONS)
            student.blood_group = random.choice(BLOOD_GROUPS)
            student.boarding_status = 'day' if random.random() < 0.9 else random.choice(['boarder', 'weekly'])
            student.residential_address = f"House No. {random.randint(1, 200)}, {random.choice(HOME_TOWNS)}"
            student.city = random.choice(HOME_TOWNS)
            student.region = random.choice(REGIONS)
            student.talents_skills = random.choice(TALENTS)
        else:
            if random.random() < 0.4:
                student.city = random.choice(HOME_TOWNS)
            if random.random() < 0.3:
                student.mother_tongue = random.choice(MOTHER_TONGUES)

        student.save()
        return student

    def _create_guardians(self, student, is_full):
        if is_full:
            for relationship, g_gender in [('father', 'male'), ('mother', 'female')]:
                first = random.choice(MALE_GIVEN_NAMES if g_gender == 'male' else FEMALE_GIVEN_NAMES)
                last = student.last_name if random.random() < 0.7 else random.choice(SURNAMES)
                occupation, _ = Occupation.objects.get_or_create(name=random.choice(OCCUPATIONS))
                guardian = Guardian.objects.create(
                    first_name=first,
                    last_name=last,
                    relationship=relationship,
                    occupation=occupation,
                    employer=random.choice(['', 'Self-employed', 'Ghana Education Service', 'Local Business', 'Ministry of Health']),
                    nationality='Ghanaian',
                    phone=random_phone(),
                    whatsapp_number=random_phone() if random.random() < 0.8 else '',
                    residential_address=student.residential_address or f"House No. {random.randint(1, 200)}, {random.choice(HOME_TOWNS)}",
                    is_fee_payer=(relationship == 'father'),
                )
                StudentGuardian.objects.create(
                    student=student, guardian=guardian, is_primary=(relationship == 'mother'),
                )
        else:
            relationship = random.choice(GUARDIAN_RELATIONSHIPS_MINIMAL)
            g_gender = 'male' if relationship in ('father', 'uncle', 'grandfather') else 'female'
            guardian = Guardian.objects.create(
                first_name=random.choice(MALE_GIVEN_NAMES if g_gender == 'male' else FEMALE_GIVEN_NAMES),
                last_name=random.choice(SURNAMES),
                relationship=relationship,
                phone=random_phone(),
            )
            StudentGuardian.objects.create(student=student, guardian=guardian, is_primary=True)