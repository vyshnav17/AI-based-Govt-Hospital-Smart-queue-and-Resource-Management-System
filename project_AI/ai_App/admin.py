from django.contrib import admin
from .models import Department, Doctor, Patient, Appointment, Queue, Bed

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department', 'specialization', 'phone', 'availability_status')
    list_filter = ('department', 'availability_status')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialization')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'age', 'gender', 'phone', 'address')
    list_filter = ('gender',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'department', 'appointment_date', 'token_number', 'queue_position', 'status')
    list_filter = ('status', 'appointment_date', 'department')
    search_fields = ('patient__user__username', 'doctor__user__username', 'token_number')

@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'priority_level', 'estimated_wait_time', 'current_status')
    list_filter = ('priority_level', 'current_status')
    search_fields = ('appointment__patient__user__username', 'appointment__token_number')

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('id', 'ward_name', 'bed_number', 'occupied')
    list_filter = ('occupied', 'ward_name')
    search_fields = ('ward_name', 'bed_number')
