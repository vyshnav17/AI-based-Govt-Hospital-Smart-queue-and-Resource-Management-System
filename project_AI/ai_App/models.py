from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='doctors')
    specialization = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    availability_status = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.user.first_name or self.user.username} ({self.department.name})"

class Nurse(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nurse_profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='nurses')
    phone = models.CharField(max_length=15)
    shift_status = models.BooleanField(default=True)

    def __str__(self):
        return f"Nurse {self.user.first_name or self.user.username} ({self.department.name})"

class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    medical_history = models.TextField(blank=True, null=True, help_text="Past medical history (e.g., surgeries, chronic conditions, allergies)")

    def __str__(self):
        return f"{self.user.first_name or self.user.username} (Age: {self.age})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled')
    ]
    CONSULTATION_MEDIUM_CHOICES = [
        ('In-Hospital', 'In-Hospital Physical Visit'),
        ('Video-Call', 'Online Video Consultation')
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    token_number = models.PositiveIntegerField()
    queue_position = models.PositiveIntegerField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    consultation_medium = models.CharField(max_length=20, choices=CONSULTATION_MEDIUM_CHOICES, default='In-Hospital')

    class Meta:
        ordering = ['appointment_date', 'token_number']

    def __str__(self):
        return f"Token #{self.token_number} - {self.patient.user.username} to {self.doctor}"

class Queue(models.Model):
    PRIORITY_CHOICES = [
        ('Normal', 'Normal'),
        ('Urgent', 'Urgent'),
        ('Emergency', 'Emergency')
    ]
    STATUS_CHOICES = [
        ('Waiting', 'Waiting'),
        ('In Consultation', 'In Consultation'),
        ('Completed', 'Completed')
    ]
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='queue_entry')
    priority_level = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='Normal')
    estimated_wait_time = models.PositiveIntegerField(help_text="Estimated wait time in minutes")
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Waiting')

    class Meta:
        ordering = ['priority_level', 'appointment__token_number']

    def __str__(self):
        return f"Queue position for {self.appointment.patient.user.username} - Status: {self.current_status}"

    @property
    def formatted_wait_time(self):
        if not self.estimated_wait_time:
            return "0 mins"
        m = self.estimated_wait_time
        if m < 60:
            return f"{m} mins"
        h = m // 60
        rem = m % 60
        if rem == 0:
            return f"{h} hr{'s' if h > 1 else ''}"
        return f"{h} hr{'s' if h > 1 else ''} {rem} min{'s' if rem > 1 else ''}"

class Bed(models.Model):
    ward_name = models.CharField(max_length=100)
    bed_number = models.CharField(max_length=10)
    occupied = models.BooleanField(default=False)
    current_patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_beds')

    class Meta:
        unique_together = ('ward_name', 'bed_number')

    def __str__(self):
        state = "Occupied" if self.occupied else "Available"
        return f"Ward: {self.ward_name} - Bed: {self.bed_number} ({state})"

class Prescription(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='prescription')
    diagnosis = models.TextField(help_text="Clinical diagnosis notes")
    medications = models.TextField(help_text="List of prescribed medicines, dosage, and frequency")
    instructions = models.TextField(blank=True, null=True, help_text="Patient instructions")
    aftercare_plan = models.TextField(blank=True, null=True, help_text="AI Generated Diet and Aftercare Plan")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.appointment.patient.user.username} - Date: {self.created_at.date()}"

class TelehealthSession(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='telehealth_session')
    room_token = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    is_on_hold = models.BooleanField(default=False, help_text="True if doctor puts call on hold for AI handover")
    sdp_offer = models.TextField(blank=True, null=True, help_text="SDP Offer signal string")
    sdp_answer = models.TextField(blank=True, null=True, help_text="SDP Answer signal string")
    ice_candidates_doc = models.TextField(blank=True, null=True, help_text="Doctor ICE candidates JSON array string")
    ice_candidates_pat = models.TextField(blank=True, null=True, help_text="Patient ICE candidates JSON array string")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Telehealth Session for {self.appointment.patient.user.username} with {self.appointment.doctor} - Active: {self.is_active}"

class PatientVitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals_logs')
    recorded_by = models.ForeignKey(Nurse, on_delete=models.SET_NULL, null=True, blank=True)
    heart_rate = models.PositiveIntegerField(blank=True, null=True, help_text="bpm")
    blood_pressure = models.CharField(max_length=15, blank=True, null=True, help_text="e.g. 120/80")
    temperature = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True, help_text="°F")
    blood_oxygen = models.PositiveIntegerField(blank=True, null=True, help_text="%")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Vitals for {self.patient.user.username} at {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"

class AIClinicalReport(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ai_reports')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='ai_reports')
    department = models.CharField(max_length=100)
    report_type = models.CharField(max_length=100, help_text="e.g. Cardiac Risk Profiler")
    report_data = models.TextField(help_text="JSON string of the AI output")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AI Report: {self.report_type} for {self.patient.user.username}"

class AIChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_messages')
    role = models.CharField(max_length=15, help_text="e.g., 'user', 'assistant', 'system'")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.role} - {self.created_at}"
