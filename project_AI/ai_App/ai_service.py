import os
from groq import Groq
from django.conf import settings
from dotenv import load_dotenv

import json

class GroqAIService:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv(os.path.join(settings.BASE_DIR, '.env'))
        
        # Initialize Groq client using environment variable
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

    def _get_hospital_summary(self):
        from ai_App.models import Patient, Doctor, Bed
        patients = Patient.objects.count()
        doctors = Doctor.objects.filter(availability_status=True).count()
        beds = Bed.objects.filter(occupied=False).count()
        return json.dumps({
            "total_patients": patients,
            "active_doctors_on_duty": doctors,
            "available_beds": beds
        })
        
    def _get_active_doctors(self):
        from ai_App.models import Doctor
        doctors = Doctor.objects.filter(availability_status=True)
        return json.dumps([{"name": d.user.get_full_name() or d.user.username, "department": d.department.name} for d in doctors])
        
    def _get_department_crowd(self, department_name):
        from ai_App.models import Queue, Department
        try:
            dept = Department.objects.get(name__icontains=department_name)
            waiting = Queue.objects.filter(department=dept, status='waiting').count()
            return json.dumps({"department": dept.name, "waiting_patients": waiting})
        except:
            return json.dumps({"error": f"Department {department_name} not found."})
            
    def _check_icu_beds(self):
        from ai_App.models import Bed, Department
        try:
            icu = Department.objects.get(name__icontains='ICU')
            total = Bed.objects.filter(department=icu).count()
            available = Bed.objects.filter(department=icu, occupied=False).count()
            return json.dumps({"total_icu_beds": total, "available_icu_beds": available})
        except:
            return json.dumps({"error": "ICU department not found."})

    def _book_appointment(self, username, doctor_name, department_name, date_str):
        from ai_App.models import Patient, Doctor, Department, Appointment
        from django.contrib.auth.models import User
        import datetime
        from django.db.models import Max, Q
        
        try:
            user = User.objects.get(username=username)
            patient = Patient.objects.get(user=user)
            
            dept = Department.objects.filter(name__icontains=department_name).first()
            if not dept:
                return json.dumps({"error": f"Department {department_name} not found."})
                
            doctor = None
            cleaned_name = doctor_name.replace('Dr.', '').replace('Dr', '').strip()
            
            # Try finding doctor by matching the cleaned string against first/last/username
            doctor = Doctor.objects.filter(
                Q(department=dept),
                Q(user__first_name__icontains=cleaned_name) | 
                Q(user__last_name__icontains=cleaned_name) |
                Q(user__username__icontains=cleaned_name)
            ).first()
            
            # If full string fails, split it into words (e.g. 'Rahul Kumar' -> 'Rahul', 'Kumar') and match
            if not doctor:
                for part in cleaned_name.split():
                    if len(part) < 3: continue
                    doctor = Doctor.objects.filter(
                        Q(department=dept),
                        Q(user__first_name__icontains=part) | 
                        Q(user__last_name__icontains=part)
                    ).first()
                    if doctor: break
            
            if not doctor:
                # If still not found, just pick any active doctor in the department to be helpful
                doctor = Doctor.objects.filter(department=dept, availability_status=True).first()
                if not doctor:
                    return json.dumps({"error": f"No active doctors found in {dept.name}."})
                    
            if date_str.lower() == "today":
                date_obj = datetime.date.today()
            elif date_str.lower() == "tomorrow":
                date_obj = datetime.date.today() + datetime.timedelta(days=1)
            else:
                try:
                    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    date_obj = datetime.date.today()
                    
            last_appointment = Appointment.objects.filter(doctor=doctor, appointment_date=date_obj).aggregate(Max('token_number'))
            last_token = last_appointment['token_number__max'] or 0
            new_token = last_token + 1
            
            apt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                department=dept,
                appointment_date=date_obj,
                token_number=new_token,
                queue_position=new_token,
                status='Pending',
                consultation_medium='In-Hospital'
            )
            
            return json.dumps({
                "success": True,
                "message": f"Appointment booked successfully with Dr. {doctor.user.first_name} {doctor.user.last_name} in {dept.name}.",
                "date": str(date_obj),
                "token_number": new_token,
                "queue_position": new_token
            })
            
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_my_appointments(self, username):
        from ai_App.models import Appointment
        from django.contrib.auth.models import User
        from django.utils import timezone
        try:
            user = User.objects.get(username=username)
            today = timezone.now().date()
            if hasattr(user, 'doctor_profile'):
                apps = Appointment.objects.filter(doctor=user.doctor_profile, appointment_date=today)
            elif hasattr(user, 'patient_profile'):
                apps = Appointment.objects.filter(patient=user.patient_profile, appointment_date=today)
            else:
                return json.dumps({"error": "No associated patient or doctor profile found for this user."})
            
            if not apps.exists():
                return json.dumps({"message": "You have no appointments today."})
                
            res = []
            for app in apps:
                res.append(f"[ID: {app.id}] Token #{app.token_number}: {app.patient.user.username} with Dr. {app.doctor.user.username} at {app.department.name} ({app.status})")
            return json.dumps({"appointments_today": res})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _cancel_appointment(self, username, appointment_id):
        from ai_App.models import Appointment
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
            if hasattr(user, 'doctor_profile'):
                app = Appointment.objects.get(id=appointment_id, doctor=user.doctor_profile)
            elif hasattr(user, 'patient_profile'):
                app = Appointment.objects.get(id=appointment_id, patient=user.patient_profile)
            else:
                return json.dumps({"error": "Unauthorized."})
            
            if app.status == 'Cancelled':
                return json.dumps({"message": f"Appointment {appointment_id} is already cancelled."})
                
            app.status = 'Cancelled'
            app.save()
            
            if hasattr(app, 'queue_entry'):
                app.queue_entry.delete()
                
            return json.dumps({"success": True, "message": f"Successfully cancelled appointment {appointment_id}."})
        except Appointment.DoesNotExist:
            return json.dumps({"error": f"Appointment with ID {appointment_id} not found or you don't have permission to cancel it."})
        except Exception as e:
            return json.dumps({"error": f"Failed to cancel: {str(e)}"})

    def get_ai_response(self, system_prompt, user_query, context, username=None, chat_history=None, use_tools=True):
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n[Hospital Context Data]:\n{context}"}
        ]
        
        if chat_history:
            messages.extend(chat_history)
            
        messages.append({"role": "user", "content": user_query})
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_hospital_summary",
                    "description": "Get a summary of the hospital including total patients, active doctors, and available beds.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_active_doctors",
                    "description": "Get a list of all active doctors currently on duty and their departments.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_department_crowd",
                    "description": "Check how many patients are currently waiting in a specific department's queue.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "department_name": {"type": "string", "description": "The name of the department (e.g., Cardiology, ICU)"}
                        },
                        "required": ["department_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_icu_beds",
                    "description": "Check the total and available number of ICU beds.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_appointment",
                    "description": "Book a new hospital appointment for the user with a specific doctor and department.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "The first or last name of the doctor (e.g., 'Rahul')"},
                            "department_name": {"type": "string", "description": "The department name (e.g., 'Pediatrics', 'Cardiology')"},
                            "date": {"type": "string", "description": "The date of the appointment (e.g., 'Today', 'Tomorrow', or 'YYYY-MM-DD')"}
                        },
                        "required": ["doctor_name", "department_name", "date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_my_appointments",
                    "description": "Get a list of the user's scheduled hospital appointments for today. This returns the appointment IDs which are needed for cancellation.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_appointment",
                    "description": "Cancel a hospital appointment for the user. Requires the specific appointment ID. Always call get_my_appointments first to find the correct appointment ID before calling this.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "integer", "description": "The unique ID of the appointment to cancel."}
                        },
                        "required": ["appointment_id"]
                    }
                }
            }
        ]
        
        # Initial call
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        if use_tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
            
        try:
            response = self.client.chat.completions.create(**kwargs)
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
        except Exception as e:
            error_str = str(e)
            if "tool_use_failed" in error_str and "failed_generation" in error_str:
                import re
                match = re.search(r"<function=(\w+)(.*?)</function>", error_str)
                if match:
                    func_name = match.group(1)
                    args_str = match.group(2)
                    if args_str.startswith(">"): args_str = args_str[1:]
                    try:
                        args = json.loads(args_str)
                        class MockFunction:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = arguments
                        class MockToolCall:
                            def __init__(self, id, type, function):
                                self.id = id
                                self.type = type
                                self.function = function
                        class MockMessage:
                            def __init__(self, content, tool_calls):
                                self.content = content
                                self.tool_calls = tool_calls
                        
                        mock_tool_call = MockToolCall("call_recovered", "function", MockFunction(func_name, json.dumps(args)))
                        response_message = MockMessage(None, [mock_tool_call])
                        tool_calls = response_message.tool_calls
                    except Exception as inner_e:
                        raise e
                else:
                    raise e
            else:
                raise e
        
        if tool_calls:
            # Append the assistant's tool call message
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": t.id,
                        "type": t.type,
                        "function": {
                            "name": t.function.name,
                            "arguments": t.function.arguments
                        }
                    } for t in tool_calls
                ]
            })
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_hospital_summary":
                    function_response = self._get_hospital_summary()
                elif function_name == "get_active_doctors":
                    function_response = self._get_active_doctors()
                elif function_name == "get_department_crowd":
                    function_response = self._get_department_crowd(function_args.get("department_name", ""))
                elif function_name == "check_icu_beds":
                    function_response = self._check_icu_beds()
                elif function_name == "book_appointment":
                    function_response = self._book_appointment(
                        username, 
                        function_args.get("doctor_name", ""),
                        function_args.get("department_name", ""),
                        function_args.get("date", "Today")
                    )
                elif function_name == "get_my_appointments":
                    function_response = self._get_my_appointments(username)
                elif function_name == "cancel_appointment":
                    function_response = self._cancel_appointment(username, function_args.get("appointment_id"))
                else:
                    function_response = json.dumps({"error": "Unknown function"})
                    
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
                
            # Second API call to get the final answer after tool execution
            second_response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.2,
                max_tokens=1024
            )
            return second_response.choices[0].message.content
            
        return response_message.content

    def transcribe_audio(self, file_path):
        with open(file_path, "rb") as file:
            transcription = self.client.audio.transcriptions.create(
              file=(os.path.basename(file_path), file.read()),
              model="whisper-large-v3",
              prompt="Specify context or leave blank",  
              response_format="text",  
              language="en"
            )
            return transcription
