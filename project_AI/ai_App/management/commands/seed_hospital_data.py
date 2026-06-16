import random
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from faker import Faker

from ai_App.models import Department, Doctor, Patient, Appointment, Queue, Bed

# Realistic Indian-themed / general hospital departments
DEPARTMENTS_DATA = [
    {"name": "Cardiology", "description": "Specialized cardiovascular and coronary care, including heart telemetry and angiography diagnostics."},
    {"name": "Neurology", "description": "Neurological care for nerve, spinal cord, and complex brain injuries/stroke diagnostics."},
    {"name": "Orthopedics", "description": "Surgical and therapeutic clinical treatment for bone fractures, joint replacements, and structural support."},
    {"name": "Emergency Medicine", "description": "Priority emergency triage featuring 24/7 overrides, immediate trauma care, and accident resuscitation."},
    {"name": "ENT Care", "description": "Comprehensive treatment for ear, nose, throat, head, and neck pathologies."},
    {"name": "Pediatrics", "description": "Customized and gentle pediatric outpatient, neonatal, and developmental growth analysis."},
    {"name": "Oncology", "description": "Inpatient and outpatient cancer treatment, diagnostic screenings, and therapeutic chemotherapy care."},
    {"name": "Dermatology", "description": "Clinical care for skin pathology, allergy testing, chronic rashes, and topical therapies."},
    {"name": "ICU Wards", "description": "Intensive Care Unit equipped with life-support devices, advanced ventilators, and high-frequency critical monitoring."},
    {"name": "General Medicine", "description": "General Outpatient Department (OPD) treating daily fever, mild symptoms, chronic hypertension, and triage referrals."}
]

# Clinician specialties mapped by department
SPECIALIZATIONS = {
    "Cardiology": ["Cardiologist", "Interventional Cardiologist", "Cardiac Electrophysiologist"],
    "Neurology": ["Neurologist", "Neurosurgeon", "Neuro-oncologist"],
    "Orthopedics": ["Orthopedic Surgeon", "Joint Replacement Specialist", "Sports Medicine Doctor"],
    "Emergency Medicine": ["Emergency Physician", "Trauma Specialist", "Critical Care Specialist"],
    "ENT Care": ["Otolaryngologist", "Ear & Throat Specialist"],
    "Pediatrics": ["Pediatrician", "Neonatologist", "Pediatric Cardiologist"],
    "Oncology": ["Oncologist", "Surgical Oncologist"],
    "Dermatology": ["Dermatologist", "Pediatric Dermatologist"],
    "ICU Wards": ["Critical Care Intensivist", "ICU Specialist"],
    "General Medicine": ["General Physician", "Family Medicine Practitioner"]
}

class Command(BaseCommand):
    help = "Seeds the government hospital database with realistic multi-role historical and live analytics data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting SmartCare AI Hospital Data Seeder..."))
        fake = Faker()

        with transaction.atomic():
            # ----------------------------------------------------
            # 1. SEED DEPARTMENTS
            # ----------------------------------------------------
            self.stdout.write("Seeding clinical departments...")
            depts_dict = {}
            for d_info in DEPARTMENTS_DATA:
                dept, created = Department.objects.get_or_create(
                    name=d_info["name"],
                    defaults={"description": d_info["description"]}
                )
                depts_dict[dept.name] = dept

            # ----------------------------------------------------
            # 2. SEED DOCTORS (50 Clinicians)
            # ----------------------------------------------------
            self.stdout.write("Cleaning existing doctors (preserving admins)...")
            doctor_users = User.objects.filter(doctor_profile__isnull=False)
            doctor_users.delete() # Cascade deletes Doctor profile records

            self.stdout.write("Generating 50 realistic clinician users...")
            # Pre-hashing password to speed up bulk user creations under 5 seconds
            hashed_password = make_password('Secr3tP@ss!')
            doctor_users_to_create = []
            
            for i in range(50):
                first_name = fake.first_name_male() if i % 2 == 0 else fake.first_name_female()
                last_name = fake.last_name()
                username = f"doctor_{i+1}_{first_name.lower()}"
                email = f"{username}@smarthospital.gov"
                user = User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=hashed_password
                )
                doctor_users_to_create.append(user)

            User.objects.bulk_create(doctor_users_to_create)
            doctor_users_list = list(User.objects.filter(username__startswith='doctor_'))

            self.stdout.write("Seeding 50 clinical doctor profiles...")
            doctors_to_create = []
            depts_list = list(depts_dict.values())

            for idx, user in enumerate(doctor_users_list):
                dept = depts_list[idx % len(depts_list)]
                spec_list = SPECIALIZATIONS.get(dept.name, ["General Physician"])
                specialization = random.choice(spec_list)
                phone = f"9{random.randint(100000000, 999999999)}"

                doc_profile = Doctor(
                    user=user,
                    department=dept,
                    specialization=specialization,
                    phone=phone,
                    availability_status=random.choice([True, True, True, False]) # 75% available shifts
                )
                doctors_to_create.append(doc_profile)

            Doctor.objects.bulk_create(doctors_to_create)
            doctors_list = list(Doctor.objects.all())

            # ----------------------------------------------------
            # 3. SEED PATIENTS (3000 Patients)
            # ----------------------------------------------------
            self.stdout.write("Cleaning existing patients...")
            patient_users = User.objects.filter(patient_profile__isnull=False)
            patient_users.delete() # Cascade deletes Patient profile records

            self.stdout.write("Generating 3,000 realistic patient users...")
            patient_users_to_create = []
            
            for i in range(3000):
                first_name = fake.first_name_male() if i % 2 == 0 else fake.first_name_female()
                last_name = fake.last_name()
                username = f"patient_{i+1}_{first_name.lower()}"
                email = f"{username}@patientmail.com"
                user = User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=hashed_password
                )
                patient_users_to_create.append(user)

            User.objects.bulk_create(patient_users_to_create, batch_size=500)
            created_patient_users = list(User.objects.filter(username__startswith='patient_'))

            self.stdout.write("Seeding 3,000 patient profile demographics...")
            patients_to_create = []
            genders = ['Male', 'Female', 'Other']
            gender_weights = [0.48, 0.48, 0.04]

            for user in created_patient_users:
                age = random.randint(1, 95)
                gender = random.choices(genders, weights=gender_weights)[0]
                phone = f"{random.choice([7, 8, 9])}{random.randint(100000000, 999999999)}"
                address = f"{fake.street_address()}, {fake.city()}"

                patient_profile = Patient(
                    user=user,
                    age=age,
                    gender=gender,
                    phone=phone,
                    address=address
                )
                patients_to_create.append(patient_profile)

            Patient.objects.bulk_create(patients_to_create, batch_size=500)
            patients_list = list(Patient.objects.all())

            # ----------------------------------------------------
            # 4. SEED APPOINTMENTS & QUEUES (5000 Appointments)
            # ----------------------------------------------------
            self.stdout.write("Cleaning existing appointments and queue registry...")
            Appointment.objects.all().delete()
            Queue.objects.all().delete()

            self.stdout.write("Generating 5,000 appointments over the past 30 days...")
            today = datetime.date.today()
            
            # 30 historical days + tomorrow
            dates_pool = [today - datetime.timedelta(days=d) for d in range(30)] + [today + datetime.timedelta(days=1)]
            
            # Distribute weights: today and tomorrow get 10% weight, others get equal 3% weights
            date_weights = [0.03] * 30 + [0.1]
            
            raw_appointments = []
            for _ in range(5000):
                patient = random.choice(patients_list)
                doctor = random.choice(doctors_list)
                date = random.choices(dates_pool, weights=date_weights)[0]
                
                raw_appointments.append({
                    "patient": patient,
                    "doctor": doctor,
                    "department": doctor.department,
                    "date": date
                })

            self.stdout.write("Grouping appointments to calculate tokens and queue order...")
            from collections import defaultdict
            grouped = defaultdict(list)
            for raw in raw_appointments:
                key = (raw["doctor"].id, raw["date"])
                grouped[key].append(raw)

            appointments_to_create = []
            for key, items in grouped.items():
                for idx, item in enumerate(items):
                    token_number = idx + 1
                    queue_pos = idx + 1 # default serial position

                    # Status distribution:
                    # Historical dates must be mostly Completed or Cancelled.
                    # Current/Future dates are mostly Pending or Completed.
                    if item["date"] < today:
                        status = random.choices(['Completed', 'Cancelled'], weights=[0.88, 0.12])[0]
                        if status == 'Cancelled':
                            queue_pos = 0
                    else:
                        status = random.choices(['Pending', 'Completed', 'Cancelled'], weights=[0.60, 0.30, 0.10])[0]
                        if status == 'Cancelled' or status == 'Completed':
                            queue_pos = 0

                    app_obj = Appointment(
                        patient=item["patient"],
                        doctor=item["doctor"],
                        department=item["department"],
                        appointment_date=item["date"],
                        token_number=token_number,
                        queue_position=queue_pos,
                        status=status
                    )
                    appointments_to_create.append(app_obj)

            Appointment.objects.bulk_create(appointments_to_create, batch_size=500)
            created_appointments = list(Appointment.objects.all())

            self.stdout.write("Generating associated queue priority metrics...")
            queues_to_create = []

            for app in created_appointments:
                if app.status == 'Cancelled':
                    continue # Cancelled tokens do not remain in the live queue

                # Emergency medicine department has high emergency rates
                if app.department.name == "Emergency Medicine":
                    priority = random.choices(['Emergency', 'Urgent', 'Normal'], weights=[0.80, 0.15, 0.05])[0]
                else:
                    priority = random.choices(['Normal', 'Urgent', 'Emergency'], weights=[0.80, 0.15, 0.05])[0]

                # Estimated wait time
                wait_time = app.queue_position * 15 # 15 minutes average session wait time

                # Live status sync
                if app.status == 'Completed':
                    current_status = 'Completed'
                else:
                    current_status = 'Waiting'
                    # First position is often in active consultation
                    if app.queue_position == 1 and random.choice([True, False]):
                        current_status = 'In Consultation'

                queue_obj = Queue(
                    appointment=app,
                    priority_level=priority,
                    estimated_wait_time=wait_time,
                    current_status=current_status
                )
                queues_to_create.append(queue_obj)

            Queue.objects.bulk_create(queues_to_create, batch_size=500)

            # ----------------------------------------------------
            # 5. SEED WARD BEDS (65 Beds across Wards)
            # ----------------------------------------------------
            self.stdout.write("Cleaning existing bed allocations...")
            Bed.objects.all().delete()

            self.stdout.write("Allocating 65 beds across Intensive Care, Trauma, and General wards...")
            beds_to_create = []

            # 1. ICU ward
            for i in range(1, 16):
                beds_to_create.append(Bed(
                    ward_name="ICU Critical Care",
                    bed_number=f"ICU-{i:02d}",
                    occupied=random.choices([True, False], weights=[0.75, 0.25])[0] # High occupancy rate
                ))

            # 2. Emergency Trauma
            for i in range(1, 21):
                beds_to_create.append(Bed(
                    ward_name="Emergency Trauma",
                    bed_number=f"ER-{i:02d}",
                    occupied=random.choices([True, False], weights=[0.50, 0.50])[0]
                ))

            # 3. General ward A
            for i in range(1, 16):
                beds_to_create.append(Bed(
                    ward_name="General Recovery A",
                    bed_number=f"A-{i:02d}",
                    occupied=random.choices([True, False], weights=[0.40, 0.60])[0]
                ))

            # 4. General ward B
            for i in range(1, 16):
                beds_to_create.append(Bed(
                    ward_name="General Recovery B",
                    bed_number=f"B-{i:02d}",
                    occupied=random.choices([True, False], weights=[0.40, 0.60])[0]
                ))

            Bed.objects.bulk_create(beds_to_create)

        self.stdout.write(self.style.SUCCESS("SmartCare AI Hospital seeding successfully completed!"))
