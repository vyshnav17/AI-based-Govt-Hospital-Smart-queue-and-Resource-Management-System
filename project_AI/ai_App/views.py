from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.timezone import now
import datetime

from .models import Department, Doctor, Patient, Appointment, Queue, Bed, Prescription, Nurse, PatientVitals, AIClinicalReport
from .forms import (
    PatientRegistrationForm, DoctorRegistrationForm, NurseRegistrationForm, UserForm, DoctorForm, PatientForm,
    AppointmentForm, DepartmentForm, BedForm, PrescriptionForm
)

# ==========================================
# ROLE VERIFICATION HELPERS
# ==========================================

def get_role_redirect(user):
    if user.is_superuser or user.is_staff:
        return 'admin_dashboard'
    elif hasattr(user, 'doctor_profile'):
        return 'doctor_dashboard'
    elif hasattr(user, 'nurse_profile'):
        return 'nurse_dashboard'
    elif hasattr(user, 'patient_profile'):
        return 'patient_dashboard'
    return 'home'

def is_admin(user):
    return user.is_superuser or user.is_staff

def is_doctor(user):
    return hasattr(user, 'doctor_profile')

def is_patient(user):
    return hasattr(user, 'patient_profile')

def is_nurse(user):
    return hasattr(user, 'nurse_profile')

def is_clinical_staff(user):
    return is_doctor(user) or is_nurse(user)

# ==========================================
# PUBLIC / AUTH VIEWS
# ==========================================

def home(request):
    return render(request, 'home.html')

def register(request):
    role = request.GET.get('role', 'patient')
    if role not in ['patient', 'doctor', 'nurse']:
        role = 'patient'

    if request.method == "POST":
        role = request.POST.get('role', 'patient')
        if role == 'doctor':
            form = DoctorRegistrationForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password'])
                    user.save()
                    
                    Doctor.objects.create(
                        user=user,
                        department=form.cleaned_data['department'],
                        specialization=form.cleaned_data['specialization'],
                        phone=form.cleaned_data['phone'],
                        availability_status=True
                    )
                messages.success(request, "Doctor account registered successfully! You are now logged in.")
                login(request, user)
                return redirect('doctor_dashboard')
        elif role == 'nurse':
            form = NurseRegistrationForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password'])
                    user.save()
                    
                    Nurse.objects.create(
                        user=user,
                        department=form.cleaned_data['department'],
                        phone=form.cleaned_data['phone'],
                        shift_status=True
                    )
                messages.success(request, "Nurse account registered successfully! You are now logged in.")
                login(request, user)
                return redirect('nurse_dashboard')
        else:
            form = PatientRegistrationForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    # Save base User model
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password'])
                    user.save()
                    
                    # Save Patient profile model
                    Patient.objects.create(
                        user=user,
                        age=form.cleaned_data['age'],
                        gender=form.cleaned_data['gender'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address']
                    )
                
                messages.success(request, "Patient account registered successfully! You are now logged in.")
                login(request, user)
                return redirect('patient_dashboard')
    else:
        if role == 'doctor':
            form = DoctorRegistrationForm()
        elif role == 'nurse':
            form = NurseRegistrationForm()
        else:
            form = PatientRegistrationForm()
    
    return render(request, 'register.html', {'form': form, 'role': role})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, "Please enter username and password.")
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(get_role_redirect(user))
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'login.html')

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')

@login_required
def dashboard_redirect(request):
    return redirect(get_role_redirect(request.user))


# ==========================================
# NURSE FEATURES
# ==========================================

@login_required
@user_passes_test(is_nurse, login_url='home')
def nurse_dashboard(request):
    nurse = request.user.nurse_profile
    today = datetime.date.today()
    
    # Active appointments/queues for the nurse's department
    active_queues = Queue.objects.filter(
        appointment__department=nurse.department,
        appointment__appointment_date=today,
        appointment__status='Pending'
    ).order_by('priority_level', 'appointment__token_number')
    
    # Bed management for their department
    # Assuming ward_name matches department loosely, or just show all beds
    beds = Bed.objects.all() # Or filter by ward_name if you have a mapping
    
    # Process vitals form submission
    if request.method == "POST" and "log_vitals" in request.POST:
        patient_id = request.POST.get('patient_id')
        hr = request.POST.get('heart_rate')
        bp = request.POST.get('blood_pressure')
        temp = request.POST.get('temperature')
        o2 = request.POST.get('blood_oxygen')
        
        try:
            patient = Patient.objects.get(id=patient_id)
            PatientVitals.objects.create(
                patient=patient,
                recorded_by=nurse,
                heart_rate=hr if hr else None,
                blood_pressure=bp if bp else None,
                temperature=temp if temp else None,
                blood_oxygen=o2 if o2 else None
            )
            messages.success(request, f"Vitals successfully logged for {patient.user.first_name or patient.user.username}.")
        except Exception as e:
            messages.error(request, "Failed to log vitals. Please check the inputs.")
            
        return redirect('nurse_dashboard')

    context = {
        'nurse': nurse,
        'active_queues': active_queues,
        'beds': beds
    }
    return render(request, 'nurse/nurse_dashboard.html', context)


# ==========================================
# PATIENT FEATURES
# ==========================================

@login_required
@user_passes_test(is_patient, login_url='home')
def patient_dashboard(request):
    patient = request.user.patient_profile
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    
    # Active Appointments
    upcoming_appointments = appointments.filter(status='Pending', appointment_date__gte=datetime.date.today())
    
    # Check if there is an active queue entry
    active_queue = Queue.objects.filter(
        appointment__patient=patient, 
        appointment__status='Pending', 
        appointment__appointment_date=datetime.date.today()
    ).first()

    # AI Reports sent by doctors
    import json
    ai_reports_raw = patient.ai_reports.all()
    ai_reports = []
    for report in ai_reports_raw:
        try:
            report.data_dict = json.loads(report.report_data)
        except Exception:
            report.data_dict = {}
        ai_reports.append(report)

    context = {
        'upcoming_appointments': upcoming_appointments,
        'active_queue': active_queue,
        'history': appointments.filter(status__in=['Completed', 'Cancelled'])[:5],
        'ai_reports': ai_reports,
    }
    return render(request, 'patient/patient_dashboard.html', context)

@login_required
@user_passes_test(is_patient, login_url='home')
def book_appointment(request):
    patient = request.user.patient_profile
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            doctor = form.cleaned_data['doctor']
            department = form.cleaned_data['department']
            date = form.cleaned_data['appointment_date']
            priority = form.cleaned_data['priority_level']
            consultation_medium = form.cleaned_data.get('consultation_medium', 'In-Hospital')

            with transaction.atomic():
                # Count total appointments for that doctor on that date to assign token number
                token_count = Appointment.objects.filter(doctor=doctor, appointment_date=date).count()
                token_number = token_count + 1
                
                # Active/Pending appointments on that day to assign queue position
                active_count = Appointment.objects.filter(doctor=doctor, appointment_date=date, status='Pending').count()
                queue_pos = active_count + 1
                
                # Create Appointment
                appointment = Appointment.objects.create(
                    patient=patient,
                    doctor=doctor,
                    department=department,
                    appointment_date=date,
                    token_number=token_number,
                    queue_position=queue_pos,
                    status='Pending',
                    consultation_medium=consultation_medium
                )

                # Wait Estimation (e.g. 15 minutes average per client)
                estimated_time = queue_pos * 15
                
                # Create Queue mapping
                Queue.objects.create(
                    appointment=appointment,
                    priority_level=priority,
                    estimated_wait_time=estimated_time,
                    current_status='Waiting'
                )

            messages.success(request, f"Appointment booked! Your Token Number is #{token_number}. Position: {queue_pos}.")
            return redirect('patient_dashboard')
    else:
        form = AppointmentForm()
    
    return render(request, 'patient/book_appointment.html', {'form': form})

@login_required
@user_passes_test(is_patient, login_url='home')
def appointment_history(request):
    patient = request.user.patient_profile
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    paginator = Paginator(appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'patient/appointment_history.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_patient, login_url='home')
def queue_status(request):
    patient = request.user.patient_profile
    active_appointments = Appointment.objects.filter(patient=patient, status='Pending').order_by('appointment_date')
    
    queues = []
    for app in active_appointments:
        queue_item = Queue.objects.filter(appointment=app).first()
        if queue_item:
            queues.append(queue_item)

    return render(request, 'patient/queue_status.html', {'queues': queues})

@login_required
@user_passes_test(is_patient, login_url='home')
def cancel_appointment(request, appointment_id):
    patient = request.user.patient_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    
    if appointment.status == 'Pending':
        with transaction.atomic():
            appointment.status = 'Cancelled'
            appointment.queue_position = 0
            appointment.save()

            # Shift/Decrement queue position for all subsequent active appointments for that doctor and date
            subsequent_apps = Appointment.objects.filter(
                doctor=appointment.doctor,
                appointment_date=appointment.appointment_date,
                status='Pending',
                token_number__gt=appointment.token_number
            )
            for sub_app in subsequent_apps:
                if sub_app.queue_position > 1:
                    sub_app.queue_position -= 1
                    sub_app.save()
                    
                    # Update active queue item wait time
                    queue_item = Queue.objects.filter(appointment=sub_app).first()
                    if queue_item:
                        queue_item.estimated_wait_time = sub_app.queue_position * 15
                        queue_item.save()

            # Delete the queue item
            Queue.objects.filter(appointment=appointment).delete()

        messages.success(request, "Appointment cancelled successfully. Live queues have updated.")
    else:
        messages.error(request, "Only pending appointments can be cancelled.")
        
    return redirect('patient_dashboard')


# ==========================================
# DOCTOR FEATURES
# ==========================================

@login_required
@user_passes_test(is_doctor, login_url='home')
def doctor_dashboard(request):
    doctor = request.user.doctor_profile
    today = datetime.date.today()
    
    # Active queues for today
    today_appointments = Appointment.objects.filter(doctor=doctor, appointment_date=today).order_by('token_number')
    pending_appointments = today_appointments.filter(status='Pending')
    
    # Emergency Cases
    emergencies = Queue.objects.filter(
        appointment__doctor=doctor,
        appointment__appointment_date=today,
        appointment__status='Pending',
        priority_level='Emergency'
    )

    context = {
        'doctor': doctor,
        'appointments': today_appointments,
        'pending_count': pending_appointments.count(),
        'emergencies': emergencies,
        'completed_count': today_appointments.filter(status='Completed').count(),
    }
    return render(request, 'doctor/doctor_dashboard.html', context)

@login_required
@user_passes_test(is_doctor, login_url='home')
def get_patient_data_api(request, patient_id):
    from django.http import JsonResponse
    try:
        patient = Patient.objects.get(id=patient_id)
        latest_vitals = patient.vitals_logs.first()
        data = {
            'age': patient.age,
            'gender': patient.gender,
            'vitals': {
                'bp': latest_vitals.blood_pressure if latest_vitals else "",
                'hr': latest_vitals.heart_rate if latest_vitals else "",
                'temp': latest_vitals.temperature if latest_vitals else "",
                'spo2': latest_vitals.blood_oxygen if latest_vitals else "",
            } if latest_vitals else None
        }
        return JsonResponse(data)
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)

from django.views.decorators.csrf import csrf_exempt

@login_required
@user_passes_test(is_doctor, login_url='home')
@csrf_exempt
def save_ai_report_api(request):
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            patient_id = data.get('patient_id')
            report_type = data.get('report_type')
            report_data = data.get('report_data')

            if not patient_id or not report_type or not report_data:
                return JsonResponse({'error': 'Missing data'}, status=400)

            patient = Patient.objects.get(id=patient_id)
            doctor = request.user.doctor_profile
            
            AIClinicalReport.objects.create(
                patient=patient,
                doctor=doctor,
                department=doctor.department.name,
                report_type=report_type,
                report_data=json.dumps(report_data)
            )
            return JsonResponse({'success': True, 'message': 'Report securely saved to Patient EMR'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
@user_passes_test(is_doctor, login_url='home')
def todays_patients(request):
    doctor = request.user.doctor_profile
    appointments = Appointment.objects.filter(doctor=doctor, appointment_date=datetime.date.today()).order_by('token_number')
    return render(request, 'doctor/todays_patients.html', {'appointments': appointments})

@login_required
@user_passes_test(is_doctor, login_url='home')
def patient_details(request, appointment_id):
    doctor = request.user.doctor_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    return render(request, 'doctor/patient_details.html', {'appointment': appointment})

@login_required
@user_passes_test(is_doctor, login_url='home')
def complete_appointment(request, appointment_id):
    doctor = request.user.doctor_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)

    if appointment.status != 'Pending':
        messages.error(request, "This appointment has already been updated.")
        return redirect('doctor_dashboard')

    if request.method == "POST":
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Save prescription record
                prescription = form.save(commit=False)
                prescription.appointment = appointment
                prescription.save()

                # Mark appointment completed
                appointment.status = 'Completed'
                appointment.queue_position = 0
                appointment.save()

                # Decrement subsequent pending queue positions
                subsequent_apps = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appointment.appointment_date,
                    status='Pending',
                    token_number__gt=appointment.token_number
                )
                for sub_app in subsequent_apps:
                    if sub_app.queue_position > 1:
                        sub_app.queue_position -= 1
                        sub_app.save()
                        
                        queue_item = Queue.objects.filter(appointment=sub_app).first()
                        if queue_item:
                            queue_item.estimated_wait_time = sub_app.queue_position * 15
                            queue_item.save()

                # Update Queue Status to Completed
                queue_item = Queue.objects.filter(appointment=appointment).first()
                if queue_item:
                    queue_item.current_status = 'Completed'
                    queue_item.save()

            messages.success(request, f"Consultation completed and prescription registered for Patient {appointment.patient.user.username}.")
            return redirect('doctor_dashboard')
    else:
        form = PrescriptionForm()

    return render(request, 'doctor/write_prescription.html', {
        'form': form,
        'appointment': appointment
    })

@login_required
@user_passes_test(is_doctor, login_url='home')
def toggle_availability(request):
    doctor = request.user.doctor_profile
    doctor.availability_status = not doctor.availability_status
    doctor.save()
    messages.success(request, f"Availability toggled to {'Available' if doctor.availability_status else 'Unavailable'}.")
    return redirect('doctor_dashboard')


# ==========================================
# ADMIN PANEL FEATURES
# ==========================================

@login_required
@user_passes_test(is_admin, login_url='home')
def admin_dashboard(request):
    today = datetime.date.today()
    
    # Detailed Data for the enhanced Admin Portal
    patients = Patient.objects.all().order_by('-id')
    doctors = Doctor.objects.all()
    nurses = Nurse.objects.all()
    beds = Bed.objects.all()
    all_appointments = Appointment.objects.all().order_by('-appointment_date', '-token_number')
    
    # Statistics
    total_patients_today = Appointment.objects.filter(appointment_date=today).count()
    active_doctors = Doctor.objects.filter(availability_status=True).count()
    available_beds = beds.filter(occupied=False).count()
    total_beds = beds.count()
    
    # Emergency Cases today
    emergencies = Queue.objects.filter(
        appointment__appointment_date=today,
        priority_level='Emergency',
        appointment__status='Pending'
    ).count()

    # Department statistics for charts
    departments = Department.objects.all()
    dept_labels = [dept.name for dept in departments]
    dept_counts = [Appointment.objects.filter(department=dept, appointment_date=today).count() for dept in departments]

    context = {
        'total_patients_today': total_patients_today,
        'active_doctors': active_doctors,
        'available_beds': available_beds,
        'occupied_beds': total_beds - available_beds,
        'emergencies': emergencies,
        'dept_labels': dept_labels,
        'dept_counts': dept_counts,
        'active_queues': Queue.objects.filter(appointment__appointment_date=today, appointment__status='Pending').order_by('priority_level')[:10],
        # New Context variables for full visibility
        'patients': patients,
        'doctors': doctors,
        'nurses': nurses,
        'beds': beds,
        'all_appointments': all_appointments
    }
    return render(request, 'adminpanel/admin_dashboard.html', context)


# --- Department CRUD ---

@login_required
@user_passes_test(is_admin, login_url='home')
def manage_departments(request):
    departments = Department.objects.all()
    return render(request, 'adminpanel/manage_departments.html', {'departments': departments})

@login_required
@user_passes_test(is_admin, login_url='home')
def add_department(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added successfully!")
            return redirect('manage_departments')
    else:
        form = DepartmentForm()
    return render(request, 'adminpanel/manage_departments.html', {'form': form, 'add_mode': True, 'departments': Department.objects.all()})

@login_required
@user_passes_test(is_admin, login_url='home')
def edit_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('manage_departments')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'adminpanel/manage_departments.html', {'form': form, 'edit_mode': True, 'dept': dept, 'departments': Department.objects.all()})

@login_required
@user_passes_test(is_admin, login_url='home')
def delete_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.delete()
    messages.success(request, "Department deleted successfully!")
    return redirect('manage_departments')


# --- Doctor CRUD ---

@login_required
@user_passes_test(is_admin, login_url='home')
def manage_doctors(request):
    doctors = Doctor.objects.all()
    return render(request, 'adminpanel/manage_doctors.html', {'doctors': doctors})

@login_required
@user_passes_test(is_admin, login_url='home')
def add_doctor(request):
    if request.method == "POST":
        user_form = UserForm(request.POST)
        doctor_form = DoctorForm(request.POST)
        password = request.POST.get('password')
        
        if user_form.is_valid() and doctor_form.is_valid() and password:
            with transaction.atomic():
                user = user_form.save(commit=False)
                user.set_password(password)
                user.save()
                
                doctor = doctor_form.save(commit=False)
                doctor.user = user
                doctor.save()
                
            messages.success(request, "Doctor registered successfully!")
            return redirect('manage_doctors')
        else:
            messages.error(request, "Validation error. Please verify forms and fields.")
    else:
        user_form = UserForm()
        doctor_form = DoctorForm()
    
    return render(request, 'adminpanel/manage_doctors.html', {
        'user_form': user_form,
        'doctor_form': doctor_form,
        'add_mode': True,
        'doctors': Doctor.objects.all()
    })

@login_required
@user_passes_test(is_admin, login_url='home')
def edit_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=doctor.user)
        doctor_form = DoctorForm(request.POST, instance=doctor)
        
        if user_form.is_valid() and doctor_form.is_valid():
            with transaction.atomic():
                user_form.save()
                doctor_form.save()
            messages.success(request, "Doctor updated successfully!")
            return redirect('manage_doctors')
    else:
        user_form = UserForm(instance=doctor.user)
        doctor_form = DoctorForm(instance=doctor)
        
    return render(request, 'adminpanel/manage_doctors.html', {
        'user_form': user_form,
        'doctor_form': doctor_form,
        'edit_mode': True,
        'doctor': doctor,
        'doctors': Doctor.objects.all()
    })

@login_required
@user_passes_test(is_admin, login_url='home')
def delete_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    user = doctor.user
    with transaction.atomic():
        doctor.delete()
        user.delete()
    messages.success(request, "Doctor account deleted successfully!")
    return redirect('manage_doctors')


# --- Patient CRUD ---

@login_required
@user_passes_test(is_admin, login_url='home')
def manage_patients(request):
    patients = Patient.objects.all()
    return render(request, 'adminpanel/manage_patients.html', {'patients': patients})

@login_required
@user_passes_test(is_admin, login_url='home')
def add_patient(request):
    if request.method == "POST":
        user_form = UserForm(request.POST)
        patient_form = PatientForm(request.POST)
        password = request.POST.get('password')
        
        if user_form.is_valid() and patient_form.is_valid() and password:
            with transaction.atomic():
                user = user_form.save(commit=False)
                user.set_password(password)
                user.save()
                
                patient = patient_form.save(commit=False)
                patient.user = user
                patient.save()
                
            messages.success(request, "Patient registered successfully!")
            return redirect('manage_patients')
    else:
        user_form = UserForm()
        patient_form = PatientForm()
        
    return render(request, 'adminpanel/manage_patients.html', {
        'user_form': user_form,
        'patient_form': patient_form,
        'add_mode': True,
        'patients': Patient.objects.all()
    })

@login_required
@user_passes_test(is_admin, login_url='home')
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=patient.user)
        patient_form = PatientForm(request.POST, instance=patient)
        
        if user_form.is_valid() and patient_form.is_valid():
            with transaction.atomic():
                user_form.save()
                patient_form.save()
            messages.success(request, "Patient updated successfully!")
            return redirect('manage_patients')
    else:
        user_form = UserForm(instance=patient.user)
        patient_form = PatientForm(instance=patient)
        
    return render(request, 'adminpanel/manage_patients.html', {
        'user_form': user_form,
        'patient_form': patient_form,
        'edit_mode': True,
        'patient': patient,
        'patients': Patient.objects.all()
    })

@login_required
@user_passes_test(is_admin, login_url='home')
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    user = patient.user
    with transaction.atomic():
        patient.delete()
        user.delete()
    messages.success(request, "Patient registry deleted successfully!")
    return redirect('manage_patients')


# --- Bed CRUD ---

@login_required
@user_passes_test(is_admin, login_url='home')
def bed_management(request):
    beds = Bed.objects.all()
    form = BedForm()
    return render(request, 'adminpanel/bed_management.html', {'beds': beds, 'form': form})

@login_required
@user_passes_test(is_admin, login_url='home')
def add_bed(request):
    if request.method == "POST":
        form = BedForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bed resource registered successfully!")
    return redirect('bed_management')

@login_required
@user_passes_test(is_admin, login_url='home')
def toggle_bed_occupancy(request, pk):
    bed = get_object_or_404(Bed, pk=pk)
    bed.occupied = not bed.occupied
    bed.save()
    messages.success(request, f"Bed {bed.bed_number} status updated successfully.")
    return redirect('bed_management')

@login_required
@user_passes_test(is_admin, login_url='home')
def delete_bed(request, pk):
    bed = get_object_or_404(Bed, pk=pk)
    bed.delete()
    messages.success(request, "Bed resource removed successfully.")
    return redirect('bed_management')


# ==========================================
# AI CHATBOT FEATURES
# ==========================================

@login_required
def chatbot_view(request):
    """
    Renders the beautiful AI chatbot hub.
    """
    from .models import AIChatMessage
    chats = AIChatMessage.objects.filter(user=request.user).order_by('created_at')
    return render(request, 'ai/chatbot.html', {'chats': chats})

@csrf_exempt
@login_required
def chatbot_api(request):
    """
    POST API for the Chatbot. Replaced local fallback with Groq.
    """
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService
    from .models import AIChatMessage

    if request.method == 'POST':
        try:
            # Check if this is an audio upload
            if 'audio' in request.FILES:
                audio_file = request.FILES['audio']
                
                # Save temporarily
                tmp_path = f"/tmp/{audio_file.name}"
                with open(tmp_path, "wb") as f:
                    for chunk in audio_file.chunks(): f.write(chunk)
                    
                ai_service = GroqAIService()
                transcription = ai_service.transcribe_audio(tmp_path).text
                import os; os.remove(tmp_path)
                return JsonResponse({'response': transcription, 'transcript': transcription})
                
            data = json.loads(request.body)
            user_query = data.get("message", "").strip()
            
            if not user_query:
                return JsonResponse({'response': "Please enter a message."})

            ai_service = GroqAIService()
            
            role_str = "an Administrator"
            if hasattr(request.user, 'doctor_profile'):
                role_str = f"Dr. {request.user.first_name or request.user.username} ({request.user.doctor_profile.department.name} Department)"
            elif hasattr(request.user, 'patient_profile'):
                role_str = f"a Patient ({request.user.first_name or request.user.username})"
            elif hasattr(request.user, 'nurse_profile'):
                role_str = f"Nurse {request.user.first_name or request.user.username}"

            context = f"The logged-in user is {role_str} (username: {request.user.username}). You MUST tailor your responses based on their role."
            system_prompt = "You are SmartCare AI, a helpful medical assistant for SmartCare Hospital. You have access to real hospital data. You MUST STRICTLY REFUSE to answer any questions that are not related to healthcare, medical advice, or this hospital's operations. If a user asks about politics, celebrities, general knowledge, or other off-topic subjects (like who is the PM/CM), politely tell them that you are a hospital AI and cannot answer that."
            
            # Fetch last 10 messages for context
            past_messages = AIChatMessage.objects.filter(user=request.user).order_by('-created_at')[:10]
            chat_history = [{"role": msg.role, "content": msg.content} for msg in reversed(past_messages)]
            
            # Save user message
            AIChatMessage.objects.create(user=request.user, role='user', content=user_query)
            
            # Get AI response
            ai_reply = ai_service.get_ai_response(system_prompt, user_query, context, request.user.username, chat_history)
            
            # Save AI response
            AIChatMessage.objects.create(user=request.user, role='assistant', content=ai_reply)

            return JsonResponse({'response': ai_reply, 'transcript': None})

        except Exception as e:
            print(e)
            return JsonResponse({'response': "An operational error occurred with Groq API."})

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_patient, login_url='home')
def patient_prescriptions(request):
    patient = request.user.patient_profile
    prescriptions = Prescription.objects.filter(appointment__patient=patient).order_by('-created_at')
    return render(request, 'patient/patient_prescriptions.html', {'prescriptions': prescriptions})

def public_queues(request):
    """
    Public-facing waiting room TV dashboard.
    """
    today = datetime.date.today()
    active_queues = Queue.objects.filter(
        appointment__appointment_date=today,
        appointment__status='Pending'
    ).order_by('priority_level', 'appointment__token_number')

    # Group loads
    departments = Department.objects.all()
    dept_loads = []
    for dept in departments:
        count = Appointment.objects.filter(department=dept, appointment_date=today, status='Pending').count()
        if count > 0:
            dept_loads.append({'name': dept.name, 'count': count})

    context = {
        'active_queues': active_queues[:15],
        'dept_loads': dept_loads,
        'today': today
    }
    return render(request, 'public_queues.html', context)

@login_required
def ai_symptom_triage(request):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            symptoms = data.get("symptoms", "").strip()

            if not symptoms:
                return JsonResponse({'error': "Please describe your symptoms to analyze."}, status=400)

            ai_service = GroqAIService()
            system_prompt = """
            You are 'SmartCare AI', an advanced medical triage assistant.
            Analyze the patient's symptoms and return a clean, structured JSON response exactly matching these keys:
            - "recommended_department": Must match exactly one: "Cardiology", "Neurology", "Orthopedics", "Emergency Medicine", "ENT Care", "Pediatrics", "Oncology", "Dermatology", "General Medicine" (choose "Emergency Medicine" if critical).
            - "urgency_rating": Choose exactly one: "Normal", "Urgent", "Emergency".
            - "clinical_justification": 2-3 sentences explaining the reasoning.
            - "emergency_warning": 1 short warning if applicable, else empty string.
            Only return the raw JSON object. Do not include markdown or backticks.
            """
            
            reply = ai_service.get_ai_response(system_prompt, f"Patient symptoms: {symptoms}", "")
            import re
            json_str = re.sub(r'```json\n|```', '', reply).strip()
            parsed_json = json.loads(json_str)

            return JsonResponse({
                'recommended_department': parsed_json.get('recommended_department', 'General Medicine'),
                'urgency_rating': parsed_json.get('urgency_rating', 'Normal'),
                'clinical_justification': parsed_json.get('clinical_justification', ''),
                'emergency_warning': parsed_json.get('emergency_warning', '')
            })

        except Exception as e:
            return JsonResponse({'error': "An operational error occurred in Groq AI core."}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_doctor, login_url='home')
def doctor_beds(request):
    beds = Bed.objects.all().order_by('ward_name', 'bed_number')
    admitted_patients = Bed.objects.filter(occupied=True).values_list('current_patient_id', flat=True)
    unassigned_patients = Patient.objects.exclude(id__in=admitted_patients)
    
    return render(request, 'doctor/doctor_beds.html', {
        'beds': beds,
        'patients': unassigned_patients
    })

@login_required
@user_passes_test(is_doctor, login_url='home')
def admit_patient(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)
    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            with transaction.atomic():
                bed.occupied = True
                bed.current_patient = patient
                bed.save()
            messages.success(request, f"Patient {patient.user.username} admitted successfully to Bed {bed.bed_number} in {bed.ward_name}.")
        else:
            messages.error(request, "Please select a patient to admit.")
    return redirect('doctor_beds')

@login_required
@user_passes_test(is_doctor, login_url='home')
def discharge_patient(request, bed_id):
    bed = get_object_or_404(Bed, id=bed_id)
    if bed.occupied:
        patient_name = bed.current_patient.user.username if bed.current_patient else "Unknown"
        with transaction.atomic():
            bed.occupied = False
            bed.current_patient = None
            bed.save()
        messages.success(request, f"Patient {patient_name} discharged successfully from Bed {bed.bed_number}.")
    else:
        messages.error(request, "This bed is already vacant.")
    return redirect('doctor_beds')

def get_doctors_api(request):
    """
    Returns JSON list of doctors filtered by department.
    """
    from django.http import JsonResponse
    department_id = request.GET.get('department_id')
    if not department_id:
        return JsonResponse({'doctors': []})
        
    doctors = Doctor.objects.filter(department_id=department_id, availability_status=True)
    doctors_data = [
        {
            'id': doc.id,
            'name': f"Dr. {doc.user.first_name or doc.user.username} ({doc.specialization})"
        }
        for doc in doctors
    ]
    return JsonResponse({'doctors': doctors_data})

@login_required
def appointment_status_api(request, appointment_id):
    """
    Returns the live status of an appointment.
    Useful for patient dashboard dynamic background status polling.
    """
    from django.http import JsonResponse
    
    # Restrict lookup based on user type to preserve data isolation
    if hasattr(request.user, 'patient_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient_profile)
    elif hasattr(request.user, 'doctor_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor_profile)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id)

    has_pres = Prescription.objects.filter(appointment=appointment).exists()
    has_call = getattr(appointment, 'telehealth_session', None) and appointment.telehealth_session.is_active
    
    return JsonResponse({
        'id': appointment.id,
        'status': appointment.status,
        'queue_position': appointment.queue_position,
        'has_prescription': has_pres,
        'has_active_call': bool(has_call),
        'doctor_name': f"Dr. {appointment.doctor.user.first_name or appointment.doctor.user.username}",
        'department_name': appointment.department.name,
    })

@login_required
@user_passes_test(is_doctor, login_url='home')
def ai_prescription_suggest(request):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            symptoms = data.get("symptoms", "").strip()
            appointment_id = data.get("appointment_id")

            if not symptoms or not appointment_id:
                return JsonResponse({'error': "Please supply patient symptoms and appointment ID."}, status=400)

            doctor = request.user.doctor_profile
            appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
            
            ai_service = GroqAIService()
            system_prompt = f"""
            You are an advanced digital medical scribe. The attending physician is Dr. {doctor.user.username} (Specialty: {doctor.specialization}).
            Analyze the patient symptoms/doctor notes and return a strict JSON output:
            - "diagnosis": A detailed clinical diagnosis (single string).
            - "medications": A single string containing a numbered list of recommended medications, doses, and durations.
            - "instructions": Key lifestyle or rest instructions (single string).
            Return ONLY raw JSON, no markdown.
            """
            
            reply = ai_service.get_ai_response(system_prompt, f"Symptoms/Notes: {symptoms}", "")
            import re
            json_str = re.sub(r'```json\n|```', '', reply).strip()
            parsed = json.loads(json_str)
            
            meds = parsed.get('medications', '')
            if isinstance(meds, list):
                if len(meds) > 0 and isinstance(meds[0], dict):
                    meds = '\n'.join([f"{i+1}. " + ", ".join([f"{k}: {v}" for k, v in x.items()]) for i, x in enumerate(meds)])
                else:
                    meds = '\n'.join([f"{i+1}. {str(x)}" for i, x in enumerate(meds)])
            elif isinstance(meds, dict):
                meds = ", ".join([f"{k}: {v}" for k, v in meds.items()])
            else:
                meds = str(meds)
                
            instructions = parsed.get('instructions', '')
            if isinstance(instructions, list):
                instructions = '\n'.join([str(x) for x in instructions])
            else:
                instructions = str(instructions)
            
            return JsonResponse({
                'diagnosis': str(parsed.get('diagnosis', '')),
                'medications': meds,
                'instructions': instructions
            })
        except Exception as e:
            return JsonResponse({'error': "An operational error occurred in our AI prescription engine."}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
def ai_aftercare_suggest(request, pres_id):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService
    
    if request.method == "GET":
        try:
            prescription = get_object_or_404(Prescription, id=pres_id)
            
            # Auths
            if hasattr(request.user, 'patient_profile') and prescription.appointment.patient != request.user.patient_profile:
                return JsonResponse({'error': "Unauthorized access."}, status=403)
            elif hasattr(request.user, 'doctor_profile') and prescription.appointment.doctor != request.user.doctor_profile:
                return JsonResponse({'error': "Unauthorized access."}, status=403)
            
            if prescription.aftercare_plan:
                return JsonResponse({'plan': prescription.aftercare_plan})

            ai_service = GroqAIService()
            system_prompt = """
            You are a specialized medical aftercare planner.
            Generate a concise, easy-to-read markdown plan for patient recovery at home based on their diagnosis.
            Include ## Dietary Guidelines, ## General Aftercare & Lifestyle, and ## Warning Signs.
            Output ONLY the markdown.
            """
            
            plan = ai_service.get_ai_response(system_prompt, f"Diagnosis: {prescription.diagnosis}", "").strip()

            prescription.aftercare_plan = plan
            prescription.save()

            return JsonResponse({'plan': prescription.aftercare_plan})
        except Exception as e:
            return JsonResponse({'error': "An operational error occurred in our AI aftercare engine."}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_doctor, login_url='home')
def ai_scribe_transcribe(request):
    from django.http import JsonResponse
    from .ai_service import GroqAIService

    if request.method == "POST":
        try:
            if 'audio' not in request.FILES:
                return JsonResponse({'error': 'No audio file provided.'}, status=400)
                
            file = request.FILES['audio']
            tmp_path = "tmp_scribe.webm"
            with open(tmp_path, "wb") as f:
                for chunk in file.chunks(): f.write(chunk)
                
            ai_service = GroqAIService()
            transcription = ai_service.transcribe_audio(tmp_path).text
            import os; os.remove(tmp_path)
            
            return JsonResponse({'transcript': transcription})
        except Exception as e:
            return JsonResponse({'error': 'Audio transcription failed via Groq.'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_clinical_staff, login_url='home')
def ai_vitals_analyze(request):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            hr = int(data.get("hr", 75))
            o2 = int(data.get("o2", 98))

            ai_service = GroqAIService()
            system_prompt = """
            Analyze vitals. Return JSON with 'status' (Normal, Warning, Critical) and 'message'.
            Raw JSON only.
            """
            
            reply = ai_service.get_ai_response(system_prompt, f"HR: {hr}, O2: {o2}", "")
            import re
            json_str = re.sub(r'```json\n|```', '', reply).strip()
            parsed = json.loads(json_str)

            return JsonResponse({
                "status": parsed.get('status', 'Normal'),
                "message": parsed.get('message', 'Vitals analyzed.')
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_clinical_staff, login_url='home')
def ai_shift_handover(request):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            raw_notes = data.get("notes", "")
            
            if not raw_notes:
                return JsonResponse({'error': 'No notes provided.'}, status=400)

            ai_service = GroqAIService()
            system_prompt = """
            You are a clinical AI assistant. Rewrite the following rough shift notes into a professional clinical handover report using the SBAR format (Situation, Background, Assessment, Recommendation).
            Make it concise, professional, and easy to read. Output only the formatted report, no markdown code blocks, just raw text formatted nicely with line breaks.
            """
            
            reply = ai_service.get_ai_response(system_prompt, raw_notes, "")
            
            return JsonResponse({'report': reply.strip()})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
@user_passes_test(is_admin, login_url='home')
def ai_resource_predict(request):
    import json
    from django.http import JsonResponse
    from .ai_service import GroqAIService
    from datetime import date
    
    try:
        today = date.today()
        patients = Appointment.objects.filter(appointment_date=today).count()
        beds = Bed.objects.filter(occupied=False).count()
        
        ai_service = GroqAIService()
        system_prompt = """
        Analyze hospital load. Return JSON:
        'forecast_summary': string
        'recommended_actions': list of strings
        'risk_level': Low, Medium, High
        Raw JSON only.
        """
        
        reply = ai_service.get_ai_response(system_prompt, f"Patients: {patients}, Available Beds: {beds}", "")
        import re
        json_str = re.sub(r'```json\n|```', '', reply).strip()
        parsed = json.loads(json_str)

        return JsonResponse({
            "forecast_summary": parsed.get('forecast_summary', 'Stable.'),
            "recommended_actions": parsed.get('recommended_actions', []),
            "risk_level": parsed.get('risk_level', 'Low')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_doctor, login_url='home')
def start_telehealth(request, appointment_id):
    """
    Initializes a new TelehealthSession for the appointment, sets it active,
    and redirects the doctor to the telehealth consultation room.
    """
    import uuid
    from django.db import transaction
    from .models import TelehealthSession
    
    doctor = request.user.doctor_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    
    with transaction.atomic():
        session, created = TelehealthSession.objects.get_or_create(
            appointment=appointment,
            defaults={'room_token': uuid.uuid4().hex}
        )
        session.is_active = True
        session.sdp_offer = None
        session.sdp_answer = None
        session.ice_candidates_doc = None
        session.ice_candidates_pat = None
        session.is_on_hold = False
        session.save()
        
    messages.success(request, f"Telehealth video consultation session initiated.")
    return redirect('telehealth_room', appointment_id=appointment.id)

@login_required
def join_telehealth(request, appointment_id):
    """
    Validates patient/doctor credentials and joins an active TelehealthSession.
    """
    from .models import TelehealthSession
    
    if hasattr(request.user, 'patient_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient_profile)
    elif hasattr(request.user, 'doctor_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor_profile)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
    session = getattr(appointment, 'telehealth_session', None)
    if not session or not session.is_active:
        messages.warning(request, "This video consultation session is not currently active.")
        if hasattr(request.user, 'patient_profile'):
            return redirect('patient_dashboard')
        return redirect('doctor_dashboard')
        
    return redirect('telehealth_room', appointment_id=appointment.id)

@login_required
def telehealth_room(request, appointment_id):
    """
    Renders the WebRTC telehealth consultation chamber.
    """
    from .models import TelehealthSession
    
    if hasattr(request.user, 'patient_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient_profile)
        role = 'patient'
    elif hasattr(request.user, 'doctor_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor_profile)
        role = 'doctor'
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        role = 'admin'
        
    session = get_object_or_404(TelehealthSession, appointment=appointment)
    
    if not session.is_active:
        from django.contrib import messages
        messages.warning(request, "This video consultation session is no longer active.")
        if role == 'patient':
            return redirect('patient_dashboard')
        else:
            return redirect('doctor_dashboard')
    
    return render(request, 'telehealth_room.html', {
        'appointment': appointment,
        'session': session,
        'role': role
    })

@login_required
def telehealth_signal_api(request, appointment_id):
    """
    Real-time AJAX signaling exchange endpoint. Handles WebRTC SDP offers/answers
    and ICE candidates between clinician and patient.
    """
    import json
    from django.http import JsonResponse
    from .models import TelehealthSession
    
    if hasattr(request.user, 'patient_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient_profile)
        role = 'patient'
    elif hasattr(request.user, 'doctor_profile'):
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor_profile)
        role = 'doctor'
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        role = 'admin'
        
    session = get_object_or_404(TelehealthSession, appointment=appointment)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            signal_type = data.get('type')
            payload = data.get('payload')
            
            from django.db import transaction
            with transaction.atomic():
                session = TelehealthSession.objects.select_for_update().get(appointment=appointment)
                
                if signal_type == 'offer' and role == 'doctor':
                    session.sdp_offer = json.dumps(payload) if isinstance(payload, dict) else payload
                elif signal_type == 'answer' and role == 'patient':
                    session.sdp_answer = json.dumps(payload) if isinstance(payload, dict) else payload
                elif signal_type == 'ice_candidate':
                    if role == 'doctor':
                        current_candidates = json.loads(session.ice_candidates_doc) if session.ice_candidates_doc else []
                        current_candidates.append(payload)
                        session.ice_candidates_doc = json.dumps(current_candidates)
                    elif role == 'patient':
                        current_candidates = json.loads(session.ice_candidates_pat) if session.ice_candidates_pat else []
                        current_candidates.append(payload)
                        session.ice_candidates_pat = json.dumps(current_candidates)
                elif signal_type == 'terminate':
                    session.is_active = False
                elif signal_type == 'hold':
                    if role == 'doctor': session.is_on_hold = True
                elif signal_type == 'resume':
                    if role == 'doctor': session.is_on_hold = False
                
                session.save()
            return JsonResponse({'status': 'Signal synced.'})
        except Exception as e:
            return JsonResponse({'error': 'Signal sync failed.'}, status=400)
            
    def _parse_signal(val):
        if not val or val == 'simulation_active': return val
        try: return json.loads(val)
        except: return val

    return JsonResponse({
        'sdp_offer': _parse_signal(session.sdp_offer),
        'sdp_answer': _parse_signal(session.sdp_answer),
        'ice_candidates_doc': json.loads(session.ice_candidates_doc) if session.ice_candidates_doc else [],
        'ice_candidates_pat': json.loads(session.ice_candidates_pat) if session.ice_candidates_pat else [],
        'is_active': session.is_active,
        'is_on_hold': session.is_on_hold
    })


# --- NEXT-LEVEL SPECIALIST HUB ---

@login_required
@user_passes_test(is_doctor, login_url='home')
def specialist_hub(request):
    """
    Renders the specialized department hub for the logged-in doctor.
    """
    doctor = request.user.doctor_profile
    department_name = doctor.department.name
    
    # Get patients for this doctor (using today's appointments for context)
    from django.utils import timezone
    today = timezone.now().date()
    appointments = Appointment.objects.filter(doctor=doctor, appointment_date=today).select_related('patient', 'patient__user')
    patients = {app.patient for app in appointments}
    
    context = {
        'doctor': doctor,
        'department_name': department_name,
        'patients': patients
    }
    return render(request, 'doctor/specialist_hub.html', context)

@login_required
@user_passes_test(is_doctor, login_url='home')
def specialist_ai_api(request):
    """
    Universal API endpoint for department-specific AI tools.
    Reverted back to Groq Generative AI.
    """
    import json
    import re
    from django.http import JsonResponse
    from .ai_service import GroqAIService
    
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method.'}, status=400)
        
    try:
        payload = json.loads(request.body)
        tool_name = payload.get("tool_name", "")
        data = payload.get("data", {})
        
        system_prompts = {
            'trauma_triage': "Analyze trauma vitals. Return JSON with keys: 'priority' (str), 'hemorrhage_risk' (str), 'teams' (list of str).",
            'complication_predictor': "Predict ICU complications. Return JSON with keys: 'complications' (list of objects with 'name' (str), 'probability' (str), 'timeline' (str)).",
            'gs_complication_predictor': "Predict surgical complications. Return JSON with keys: 'risk_percentage' (str), 'pre_op_prep' (str), 'likely_complications' (list of str).",
            'cardiac_risk': "Evaluate cardiac risk. Return JSON with keys: 'risk_score' (str), 'assessment' (str), 'plan' (list of str).",
            'hf_analyzer': "Analyze heart failure. Return JSON with keys: 'diagnosis' (str), 'insight' (str), 'gdmt' (list of str), 'radar' (object with integer 0-100 values for 'contractility', 'fluid', 'valve', 'wall', 'ischemia').",
            'rehab_generator': "Generate rehab plan. Return JSON with keys: 'phase1' (list of str), 'phase2' (list of str), 'precautions' (list of str).",
            'ecg_analyzer': "Analyze ECG rhythm. Return JSON with keys: 'diagnosis' (str), 'confidence' (str), 'interventions' (list of str).",
            'pediatric_nutrition': "Analyze the patient's age, weight, allergies, and dietary goals. Return ONLY a JSON object with keys: 'meal_plan' (list of objects with 'type' (str, e.g. Breakfast) and 'suggestion' (str)), 'allergy_warnings' (list of str for specific foods to strictly avoid based on known allergies), and 'expert_tip' (str). Do NOT use any external tools or functions.",
            'pediatric_dosage': "Analyze the given medication, prescribed dose, child's weight, and age. Return ONLY a JSON object with keys: 'status' (str 'Safe', 'Unsafe', 'Check Weight'), 'analysis' (str detailing standard mg/kg range vs prescribed), and 'warnings' (list of str for contraindications). Do NOT use any external tools or functions.",
            'cognitive_analyzer': "Analyze cognitive transcript. Return JSON with keys: 'cognitive_status' (str), 'findings' (str), 'recommendation' (str).",
            'growth_percentile': "Analyze the patient's age, weight, and height to provide an estimated pediatric growth percentile assessment. You must return ONLY a JSON object with keys: 'percentile' (str e.g. '75th'), 'analysis' (str). Do NOT use any external tools or functions.",
            'milestone_assessor': "Assess pediatric milestones. Return JSON with keys: 'status' (str), 'analysis' (str), 'activities' (list of str).",
            'chemo_analyzer': "Analyze chemo regimen. Return JSON with keys: 'severe_interactions' (str), 'palliative_care' (str), 'side_effects' (list of str).",
            'trauma_prioritizer': "Score trauma severity. Return JSON with keys: 'triage_level' (str), 'justification' (str), 'immediate_action' (str).",
            'fracture_risk': "Analyze patient age, T-score, and prior fracture history to predict bone fracture risk. Return ONLY a JSON object with keys: 'risk_level' (str e.g. 'Low', 'Moderate', 'High', 'Severe'), 'analysis' (str), and 'preventive_interventions' (list of str). Do NOT use any external tools or functions."
        }

        if tool_name not in system_prompts:
            return JsonResponse({'error': 'Unsupported AI tool'}, status=400)

        ai_service = GroqAIService()
        system_prompt = system_prompts[tool_name] + " Return ONLY raw JSON without markdown formatting or backticks."
        context_str = json.dumps(data)
        
        reply = ai_service.get_ai_response(system_prompt, f"Patient Data: {context_str}", "", use_tools=False)
        
        json_str = re.sub(r'```json\n|```', '', reply).strip()
        response_data = json.loads(json_str)

        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"AI API Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)