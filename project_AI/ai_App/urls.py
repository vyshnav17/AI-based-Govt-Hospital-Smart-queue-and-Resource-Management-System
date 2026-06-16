from django.urls import path
from . import views

urlpatterns = [
    # Global Auth / Public URLs
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    # Patient URLs
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book/', views.book_appointment, name='book_appointment'),
    path('patient/history/', views.appointment_history, name='appointment_history'),
    path('patient/queue/', views.queue_status, name='queue_status'),
    path('patient/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),

    # Doctor URLs
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('nurse/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),
    path('doctor/patients/', views.todays_patients, name='todays_patients'),
    path('doctor/patient/<int:appointment_id>/', views.patient_details, name='patient_details'),
    path('doctor/complete/<int:appointment_id>/', views.complete_appointment, name='complete_appointment'),
    path('doctor/toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('doctor/specialist-hub/', views.specialist_hub, name='specialist_hub'),

    # Admin Panel URLs
    path('adminpanel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Department CRUD
    path('adminpanel/departments/', views.manage_departments, name='manage_departments'),
    path('adminpanel/departments/add/', views.add_department, name='add_department'),
    path('adminpanel/departments/edit/<int:pk>/', views.edit_department, name='edit_department'),
    path('adminpanel/departments/delete/<int:pk>/', views.delete_department, name='delete_department'),
    
    # Doctor CRUD
    path('adminpanel/doctors/', views.manage_doctors, name='manage_doctors'),
    path('adminpanel/doctors/add/', views.add_doctor, name='add_doctor'),
    path('adminpanel/doctors/edit/<int:pk>/', views.edit_doctor, name='edit_doctor'),
    path('adminpanel/doctors/delete/<int:pk>/', views.delete_doctor, name='delete_doctor'),
    
    # Patient CRUD
    path('adminpanel/patients/', views.manage_patients, name='manage_patients'),
    path('adminpanel/patients/add/', views.add_patient, name='add_patient'),
    path('adminpanel/patients/edit/<int:pk>/', views.edit_patient, name='edit_patient'),
    path('adminpanel/patients/delete/<int:pk>/', views.delete_patient, name='delete_patient'),
    
    # Bed Management
    path('adminpanel/beds/', views.bed_management, name='bed_management'),
    path('adminpanel/beds/add/', views.add_bed, name='add_bed'),
    path('adminpanel/beds/toggle/<int:pk>/', views.toggle_bed_occupancy, name='toggle_bed_occupancy'),
    path('adminpanel/beds/delete/<int:pk>/', views.delete_bed, name='delete_bed'),

    # AI Chatbot Routes
    path('ai-chatbot/', views.chatbot_view, name='ai_chatbot'),
    path('ask-ai/', views.chatbot_api, name='ask_ai'),

    # Advanced Medical Services Routes
    path('patient/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),
    path('public-queues/', views.public_queues, name='public_queues'),
    path('ai-triage/', views.ai_symptom_triage, name='ai_symptom_triage'),
    path('doctor/beds/', views.doctor_beds, name='doctor_beds'),
    path('doctor/beds/admit/<int:bed_id>/', views.admit_patient, name='admit_patient'),
    path('doctor/beds/discharge/<int:bed_id>/', views.discharge_patient, name='discharge_patient'),
    
    # Dynamic Doctor Filter API Route
    path('api/get-doctors/', views.get_doctors_api, name='get_doctors_api'),
    
    # Live Appointment Status Polling Route
    path('api/appointment-status/<int:appointment_id>/', views.appointment_status_api, name='appointment_status_api'),
    
    # AI Prescription Suggestion API Route
    path('api/ai-prescription-suggest/', views.ai_prescription_suggest, name='ai_prescription_suggest'),
    
    # AI Diet & Aftercare API Route
    path('api/ai-aftercare/<int:pres_id>/', views.ai_aftercare_suggest, name='ai_aftercare_suggest'),
    
    # AI Scribe Audio Transcription Route
    path('api/ai-scribe-transcribe/', views.ai_scribe_transcribe, name='ai_scribe_transcribe'),
    
    # AI Patient Vitals Anomaly Detection Route
    path('api/ai-vitals-analyze/', views.ai_vitals_analyze, name='ai_vitals_analyze'),
    
    # AI Shift Handover Route
    path('api/ai-shift-handover/', views.ai_shift_handover, name='ai_shift_handover'),

    # AI Predictive Resource Allocation Route
    path('api/ai-resource-predict/', views.ai_resource_predict, name='ai_resource_predict'),
    
    # AI Specialist Hub Generic Endpoint
    path('api/specialist-ai/', views.specialist_ai_api, name='specialist_ai_api'),
    path('api/patient/<int:patient_id>/data/', views.get_patient_data_api, name='get_patient_data_api'),
    path('api/patient/send-ai-report/', views.save_ai_report_api, name='save_ai_report_api'),
    
    # Telehealth Video Consult Routes
    path('telehealth/start/<int:appointment_id>/', views.start_telehealth, name='start_telehealth'),
    path('telehealth/join/<int:appointment_id>/', views.join_telehealth, name='join_telehealth'),
    path('telehealth/room/<int:appointment_id>/', views.telehealth_room, name='telehealth_room'),
    path('api/telehealth/signal/<int:appointment_id>/', views.telehealth_signal_api, name='telehealth_signal_api'),
]