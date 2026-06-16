from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import datetime
import json


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        
        # Create a standard user for login testing
        self.username = "testuser"
        self.email = "testuser@example.com"
        self.password = "Secr3tP@ss!" # satisfies strong password validation rules
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password
        )

    def test_registration_success(self):
        """Test successful user registration with valid data."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongP@ss123',
            'confirm_password': 'StrongP@ss123',
            'age': 30,
            'gender': 'Male',
            'phone': '1234567890',
            'address': '123 Smart St, Delhi'
        }
        response = self.client.post(self.register_url, data)
        self.assertRedirects(response, reverse('patient_dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_mismatched_passwords(self):
        """Test registration fails when password and confirm password do not match."""
        data = {
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password': 'StrongP@ss123',
            'confirm_password': 'DifferentP@ss123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200) # Re-renders register page
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())

    def test_registration_duplicate_username(self):
        """Test registration fails if username already exists."""
        data = {
            'username': self.username,
            'email': 'different_email@example.com',
            'password': 'StrongP@ss123',
            'confirm_password': 'StrongP@ss123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        # Should not create a duplicate
        self.assertEqual(User.objects.filter(username=self.username).count(), 1)

    def test_registration_duplicate_email(self):
        """Test registration fails if email already exists."""
        data = {
            'username': 'different_user',
            'email': self.email,
            'password': 'StrongP@ss123',
            'confirm_password': 'StrongP@ss123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='different_user').exists())

    def test_registration_weak_password(self):
        """Test registration fails if password does not meet strong criteria."""
        data = {
            'username': 'weakpassuser',
            'email': 'weak@example.com',
            'password': 'password', # no uppercase, no number, no special char
            'confirm_password': 'password'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='weakpassuser').exists())

    def test_registration_invalid_username(self):
        """Test registration fails if username contains invalid characters."""
        data = {
            'username': 'invalid-user!', # has hyphen and exclamation
            'email': 'invaliduser@example.com',
            'password': 'StrongP@ss123',
            'confirm_password': 'StrongP@ss123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='invalid-user!').exists())

    def test_login_success(self):
        """Test successful login with valid credentials."""
        data = {
            'username': self.username,
            'password': self.password
        }
        response = self.client.post(self.login_url, data)
        self.assertRedirects(response, '/')
        # Verify user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_invalid_credentials(self):
        """Test login fails with incorrect password."""
        data = {
            'username': self.username,
            'password': 'WrongPassword123!'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_logout(self):
        """Test logout clears session and redirects to login."""
        self.client.login(username=self.username, password=self.password)
        self.assertTrue('_auth_user_id' in self.client.session)
        
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_views_when_authenticated(self):
        """Test that register and login pages render 'Active Session Detected' card when logged in."""
        self.client.login(username=self.username, password=self.password)
        
        # Test register view
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Session Detected")
        self.assertContains(response, self.username)
        
        # Test login view
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Session Detected")
        self.assertContains(response, self.username)

    def test_chatbot_view_unauthenticated(self):
        """Test that unauthenticated users are redirected to login when accessing chatbot."""
        response = self.client.get(reverse('ai_chatbot'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_chatbot_view_authenticated(self):
        """Test that authenticated users can successfully access chatbot page."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('ai_chatbot'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SmartCare AI Assistant")

    def test_ask_ai_api(self):
        """Test that the ask-ai POST endpoint returns valid JSON with AI response."""
        self.client.login(username=self.username, password=self.password)
        import json
        data = {'message': "Which doctors are available now?"}
        response = self.client.post(
            reverse('ask_ai'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        
        # Verify JSON key contains operational info
        res_data = json.loads(response.content)
        self.assertTrue('response' in res_data)
        self.assertTrue(len(res_data['response']) > 0)

    def test_doctor_registration_success(self):
        """Test successful doctor self-registration and profile generation."""
        from ai_App.models import Department
        dept = Department.objects.create(name="Cardiology", description="Heart Specialist Ward")
        
        data = {
            'role': 'doctor',
            'username': 'newdoctor',
            'email': 'newdoctor@example.com',
            'password': 'StrongP@ss123',
            'confirm_password': 'StrongP@ss123',
            'department': dept.id,
            'specialization': 'Senior Cardiologist',
            'phone': '9876543210'
        }
        # Post request with query param role=doctor
        response = self.client.post(self.register_url + "?role=doctor", data)
        self.assertRedirects(response, reverse('doctor_dashboard'))
        self.assertTrue(User.objects.filter(username='newdoctor').exists())
        new_doc = User.objects.get(username='newdoctor')
        self.assertTrue(hasattr(new_doc, 'doctor_profile'))
        self.assertEqual(new_doc.doctor_profile.specialization, 'Senior Cardiologist')

    def test_clinical_prescription_flow(self):
        """Test complete clinician consultation with prescription and queue decrements."""
        from ai_App.models import Department, Doctor, Patient, Appointment, Queue, Prescription
        
        dept = Department.objects.create(name="Dermatology", description="Skin Ward")
        
        # Doctor
        doc_user = User.objects.create_user(username="doc_derm", password="StrongP@ss123!")
        doctor = Doctor.objects.create(user=doc_user, department=dept, specialization="Dermatologist", phone="1234")
        
        # Patient
        pat_user = User.objects.create_user(username="pat_skin", password="StrongP@ss123!")
        patient = Patient.objects.create(user=pat_user, age=25, gender="Female", phone="5678", address="Delhi")
        
        # Appointment
        app = Appointment.objects.create(
            patient=patient, doctor=doctor, department=dept,
            appointment_date=datetime.date.today(), token_number=1, queue_position=1, status='Pending'
        )
        Queue.objects.create(appointment=app, priority_level='Normal', estimated_wait_time=15, current_status='Waiting')
        
        self.client.login(username="doc_derm", password="StrongP@ss123!")
        
        # GET complete appointment page -> renders form
        complete_url = reverse('complete_appointment', args=[app.id])
        response = self.client.get(complete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Write Digital Prescription")
        
        # POST prescription form -> completes appointment
        pres_data = {
            'diagnosis': "Atopic Dermatitis",
            'medications': "Hydrocortisone cream 1% - apply twice daily (5 days)",
            'instructions': "Keep skin hydrated."
        }
        post_response = self.client.post(complete_url, pres_data)
        self.assertRedirects(post_response, reverse('doctor_dashboard'))
        
        # Check database records
        app.refresh_from_db()
        self.assertEqual(app.status, 'Completed')
        self.assertEqual(app.queue_position, 0)
        self.assertTrue(Prescription.objects.filter(appointment=app).exists())
        self.assertEqual(app.prescription.diagnosis, "Atopic Dermatitis")

    def test_tv_queue_board_public(self):
        """Test public wait room TV queue board renders successfully without auth."""
        response = self.client.get(reverse('public_queues'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Outpatient Queue Status")
        self.assertContains(response, "Live Waiting Room TV Display")

    def test_doctor_beds_admissions(self):
        """Test clinician bed admissions and discharge controls."""
        from ai_App.models import Bed, Patient
        
        pat_user = User.objects.create_user(username="bed_patient", password="StrongP@ss123!")
        patient = Patient.objects.create(user=pat_user, age=40, gender="Male", phone="1234", address="Mumbai")
        
        bed = Bed.objects.create(ward_name="ICU Critical Care", bed_number="ICU-99", occupied=False)
        
        # Login as doctor
        from ai_App.models import Department, Doctor
        dept = Department.objects.create(name="ICU Wards", description="ICU")
        doc_user = User.objects.create_user(username="doc_icu", password="StrongP@ss123!")
        Doctor.objects.create(user=doc_user, department=dept, specialization="Intensivist", phone="99")
        
        self.client.login(username="doc_icu", password="StrongP@ss123!")
        
        # GET beds dashboard
        response = self.client.get(reverse('doctor_beds'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admissions & Ward Bed Registry")
        
        # POST admit patient
        admit_url = reverse('admit_patient', args=[bed.id])
        admit_response = self.client.post(admit_url, {'patient_id': patient.id})
        self.assertRedirects(admit_response, reverse('doctor_beds'))
        
        bed.refresh_from_db()
        self.assertTrue(bed.occupied)
        self.assertEqual(bed.current_patient, patient)
        
        # POST discharge patient
        discharge_url = reverse('discharge_patient', args=[bed.id])
        discharge_response = self.client.post(discharge_url)
        self.assertRedirects(discharge_response, reverse('doctor_beds'))
        
        bed.refresh_from_db()
        self.assertFalse(bed.occupied)
        self.assertIsNone(bed.current_patient)

    def test_get_doctors_api(self):
        """Test that get-doctors API filters and returns correct JSON list of physicians."""
        from ai_App.models import Department, Doctor
        
        dept1 = Department.objects.create(name="Cardiology Special", description="Cardio")
        dept2 = Department.objects.create(name="Neurology Special", description="Neuro")
        
        doc_user1 = User.objects.create_user(username="doc_c1", password="StrongP@ss123!")
        doc1 = Doctor.objects.create(user=doc_user1, department=dept1, specialization="Heart Surgeon", phone="1")
        
        doc_user2 = User.objects.create_user(username="doc_n1", password="StrongP@ss123!")
        doc2 = Doctor.objects.create(user=doc_user2, department=dept2, specialization="Brain Surgeon", phone="2")
        
        # Call API for Cardiology Special
        response = self.client.get(reverse('get_doctors_api'), {'department_id': dept1.id})
        self.assertEqual(response.status_code, 200)
        
        import json
        res_data = json.loads(response.content)
        self.assertTrue('doctors' in res_data)
        self.assertEqual(len(res_data['doctors']), 1)
        self.assertEqual(res_data['doctors'][0]['id'], doc1.id)

    def test_appointment_status_polling_api(self):
        """Test that the live appointment status polling endpoint returns correct details."""
        from ai_App.models import Department, Doctor, Patient, Appointment, Queue
        
        dept = Department.objects.create(name="ENT Care", description="Ear Nose Throat")
        doc_user = User.objects.create_user(username="doc_ent", password="StrongP@ss123!")
        doctor = Doctor.objects.create(user=doc_user, department=dept, specialization="ENT Specialist", phone="911")
        
        pat_user = User.objects.create_user(username="pat_ent", password="StrongP@ss123!")
        patient = Patient.objects.create(user=pat_user, age=12, gender="Male", phone="222", address="Noida")
        
        app = Appointment.objects.create(
            patient=patient, doctor=doctor, department=dept,
            appointment_date=datetime.date.today(), token_number=1, queue_position=1, status='Pending'
        )
        Queue.objects.create(appointment=app, priority_level='Normal', estimated_wait_time=15, current_status='Waiting')
        
        # Test auth isolation: unauthenticated query should redirect
        status_url = reverse('appointment_status_api', args=[app.id])
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 302) # redirects to login/home
        
        # Login as patient and query status
        self.client.login(username="pat_ent", password="StrongP@ss123!")
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 200)
        
        import json
        res_data = json.loads(response.content)
        self.assertEqual(res_data['id'], app.id)
        self.assertEqual(res_data['status'], 'Pending')
        self.assertEqual(res_data['queue_position'], 1)
        self.assertFalse(res_data['has_prescription'])
        self.assertEqual(res_data['doctor_name'], "Dr. doc_ent")
        self.assertEqual(res_data['department_name'], "ENT Care")

    def test_ai_prescription_suggest_api(self):
        """Test that the AI prescription co-pilot recommendation API behaves correctly."""
        from ai_App.models import Department, Doctor, Patient, Appointment
        
        dept = Department.objects.create(name="Pediatrics", description="Peds Ward")
        doc_user = User.objects.create_user(username="doc_peds", password="StrongP@ss123!")
        doctor = Doctor.objects.create(user=doc_user, department=dept, specialization="Pediatrician", phone="777")
        
        pat_user = User.objects.create_user(username="pat_kid", password="StrongP@ss123!")
        patient = Patient.objects.create(user=pat_user, age=8, gender="Female", phone="111", address="Pune")
        
        app = Appointment.objects.create(
            patient=patient, doctor=doctor, department=dept,
            appointment_date=datetime.date.today(), token_number=1, queue_position=1, status='Pending'
        )
        
        url = reverse('ai_prescription_suggest')
        
        # Test auth isolation: unauthenticated query should redirect
        response = self.client.post(
            url,
            data=json.dumps({'symptoms': "mild fever", 'appointment_id': app.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
        
        # Login as patient (which has different role check: is_doctor fails)
        self.client.login(username="pat_kid", password="StrongP@ss123!")
        response = self.client.post(
            url,
            data=json.dumps({'symptoms': "mild fever", 'appointment_id': app.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302) # redirects since patient is not doctor
        
        # Login as doctor and query status
        self.client.login(username="doc_peds", password="StrongP@ss123!")
        response = self.client.post(
            url,
            data=json.dumps({'symptoms': "mild fever", 'appointment_id': app.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        res_data = json.loads(response.content)
        self.assertTrue('diagnosis' in res_data)
        self.assertTrue('medications' in res_data)
        self.assertTrue('instructions' in res_data)

    def test_telehealth_session_flow(self):
        """Test complete telehealth consult start, signaling exchanges, and status integration."""
        from ai_App.models import Department, Doctor, Patient, Appointment, TelehealthSession
        
        dept = Department.objects.create(name="Cardiology Call", description="Cardiology Wards")
        doc_user = User.objects.create_user(username="doc_call", password="StrongP@ss123!")
        doctor = Doctor.objects.create(user=doc_user, department=dept, specialization="Cardiologist", phone="123")
        
        pat_user = User.objects.create_user(username="pat_call", password="StrongP@ss123!")
        patient = Patient.objects.create(user=pat_user, age=45, gender="Male", phone="456", address="Bangalore")
        
        app = Appointment.objects.create(
            patient=patient, doctor=doctor, department=dept,
            appointment_date=datetime.date.today(), token_number=1, queue_position=1, status='Pending'
        )
        
        # Start call consult as doctor
        self.client.login(username="doc_call", password="StrongP@ss123!")
        start_url = reverse('start_telehealth', args=[app.id])
        response = self.client.get(start_url)
        self.assertRedirects(response, reverse('telehealth_room', args=[app.id]))
        
        # Verify TelehealthSession exists and is active
        session = TelehealthSession.objects.get(appointment=app)
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.room_token)
        
        # Verify patient status polling API returns has_active_call as True
        self.client.login(username="pat_call", password="StrongP@ss123!")
        status_url = reverse('appointment_status_api', args=[app.id])
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code, 200)
        
        status_data = json.loads(status_response.content)
        self.assertTrue(status_data['has_active_call'])
        
        # Join consult as patient
        join_url = reverse('join_telehealth', args=[app.id])
        join_response = self.client.get(join_url)
        self.assertRedirects(join_response, reverse('telehealth_room', args=[app.id]))
        
        # Exchange WebRTC signals via signal API
        signal_url = reverse('telehealth_signal_api', args=[app.id])
        
        # Doctor sends offer
        self.client.login(username="doc_call", password="StrongP@ss123!")
        offer_response = self.client.post(
            signal_url,
            data=json.dumps({'type': 'offer', 'payload': 'test-offer-sdp'}),
            content_type='application/json'
        )
        self.assertEqual(offer_response.status_code, 200)
        
        session.refresh_from_db()
        self.assertEqual(session.sdp_offer, 'test-offer-sdp')
        
        # Patient retrieves signal details and responds with answer
        self.client.login(username="pat_call", password="StrongP@ss123!")
        get_response = self.client.get(signal_url)
        self.assertEqual(get_response.status_code, 200)
        get_data = json.loads(get_response.content)
        self.assertEqual(get_data['sdp_offer'], 'test-offer-sdp')
        
        answer_response = self.client.post(
            signal_url,
            data=json.dumps({'type': 'answer', 'payload': 'test-answer-sdp'}),
            content_type='application/json'
        )
        self.assertEqual(answer_response.status_code, 200)
        
        session.refresh_from_db()
        self.assertEqual(session.sdp_answer, 'test-answer-sdp')



