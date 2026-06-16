# 🏥 AI-Based Govt Hospital Smart Queue and Resource Management System

![Project Banner](https://img.shields.io/badge/Project-Hospital%20Management-blue.svg?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-Web%20Framework-092E20?style=for-the-badge&logo=django)
![AI/ML](https://img.shields.io/badge/AI%20Powered-Yes-brightgreen?style=for-the-badge)

Welcome to the **AI-Based Govt Hospital Smart Queue and Resource Management System**. This project is a comprehensive, intelligent healthcare platform designed to modernize operations in government hospitals. By leveraging advanced Machine Learning models and real-time management tools, this system aims to reduce wait times, optimize resource allocation, and enhance the overall quality of patient care.

## ✨ Key Features

### 🤖 AI-Powered Clinical Intelligence
- **Symptom & Trauma Triage**: AI models rapidly assess patient symptoms and trauma severity to prioritize critical cases.
- **Predictive Diagnostics**: Dedicated analyzers for ECG, Heart Failure (HF), Cognitive, and Cardiac risks.
- **Automated Treatment Planning**: Generates preliminary prescriptions, rehab plans, and aftercare routines based on patient history.
- **Complication Predictor**: Identifies potential surgical or treatment complications before they occur.
- **Smart Chatbot**: 24/7 AI chatbot assistant to guide patients, answer queries, and perform initial screening.

### 👥 Multi-Role Dashboards
- **Patient Portal**: Easy appointment booking, telehealth consultations, access to medical history, and real-time queue status tracking.
- **Doctor Hub**: Streamlined interface for managing daily appointments, accessing AI clinical reports, writing smart prescriptions, and monitoring patient vitals.
- **Nurse Station**: Tools for recording patient vitals, managing ward beds, and updating patient statuses in real-time.
- **Admin Dashboard**: Comprehensive control over hospital resources, staff management, departments, and overall system analytics.

### ⏱️ Smart Queue & Resource Management
- **Intelligent Routing**: Dynamic queue management ensures patients are directed to the right specialist efficiently.
- **Real-time Bed Tracking**: Live monitoring of bed availability across different wards and departments to prevent overcrowding.
- **Resource Optimization**: AI-driven insights to ensure medical supplies and staff are allocated where they are needed most.

### 📹 Telehealth Integration
- **Virtual Consultations**: Secure, built-in telehealth rooms allowing doctors and patients to connect remotely.

## 🛠️ Technology Stack

- **Backend**: Django (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Machine Learning**: Scikit-learn, Pandas, NumPy (Pre-trained `.pkl` models)
- **Database**: SQLite (Development)

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/vyshnav17/AI-based-Govt-Hospital-Smart-queue-and-Resource-Management-System.git
   cd AI-based-Govt-Hospital-Smart-queue-and-Resource-Management-System
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv env
   # On Windows:
   env\Scripts\activate
   # On Linux/Mac:
   source env/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**
   ```bash
   cd project_AI
   python manage.py migrate
   ```

5. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```
   *Access the application at `http://127.0.0.1:8000/`*
