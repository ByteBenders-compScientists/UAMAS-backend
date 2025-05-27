# 🎓 UAMAS Backend

University Assessment & Marking Automation System (UAMAS) – Backend

This Flask-based backend powers the UAMAS platform, enabling lecturers to generate assessments and mark handwritten exams using GPT-4.o, OCR, and custom grading logic. It integrates with PostgreSQL for persistent data storage and supports role-based access control for admins, lecturers, and students.

---

## 🚀 Features

- AI-powered assessment and exam generation (GPT-4.o)
- Handwritten exam marking via OCR + AI grading logic
- Role-based access control (Admin, Lecturer, Student)
- Upload and manage marking schemes
- Automated email notifications
- Assignment creation, deadlines, and student submission tracking
- PostgreSQL integration

---

## ⚙️ Technologies Used

- **Flask** (Python)
- **PostgreSQL**
- **GPT-4.o (OpenAI API)**
- **OCR** (e.g., Tesseract, Azure OCR, or Google Vision API)
- **Flask-CORS**, **Flask-JWT-Extended**
- **SQLAlchemy**

---

## 📦 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/GROUP-12-COMPUTER-SCIENCE/UAMAS-backend.git
cd UAMAS-backend
````

### 2. Create a virtual environment

```bash
# do for every flask (service: Authentication, backend, api-gateway)
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
# do for every flask (service)
pip install -r requirements.txt
```

### 4. Set environment variables

Create a `.env` file and add:

```env
# api-gateway/.env

HOST='0.0.0.0'
PORT=8080
DEBUG=True
ORIGINS_URL='http://localhost:5173'
AUTH_URL='http://localhost:8000'
BACKEND_URL='http://localhost:5000'
LOGGING_FILE_PATH='logs/api-gateway.log'
LOGGING_LEVEL='INFO'
SECRET_KEY='67hsg0pxsgaSfgJKhsgyshuw/ksos9q0iecjuuhue'

# Authentication/.env

HOST='0.0.0.0'
PORT=8000
DEBUG=True
DB_URI='postgresql://waltertaya:Walter_8236!@localhost/uamas_db'
TRACK_MODIFICATIONS=False
JWT_SECRET_KEY='bgtyWEyt2n4mdj48cn9w2904ndduuLL&*jsnxjksuhus'
SECRET_KEY='67hsg0pxsgaSfgJKhsgyshuw/ksos9q0iecjuuhue'

# backend/.env

HOST='0.0.0.0'
PORT=5000
DEBUG=True
DB_URI='postgresql://waltertaya:Walter_8236!@localhost/uamas_db'
# DB_URI='sqlite:///uamas.db' # For local testing
TRACK_MODIFICATIONS=False
JWT_SECRET_KEY='bgtyWEyt2n4mdj48cn9w2904ndduuLL&*jsnxjksuhus'
SECRET_KEY='67hsg0pxsgaSfgJKhsgyshuw/ksos9q0iecjuuhue'
UPLOAD_FOLDER='uploads/'
OPENAI_API_KEY=API_KEY
NVIDIA_API_KEY=API_KEY
```

### 5. Run the app

```bash
# running the auth microservice
cd Authentication
python3 app.py
```

```bash
# running api-gateway
cd api-gateway
python3 app.py
```

```bash
# running backend microservice
## yet to be implemented
```

---

## 🧪 Running Tests

```bash
# coming soon
pytest
```

---

## 📁 Project Structure

```bash
.
├── api-gateway
│   └── app.py
├── Authentication
│   └── app.py
├── backend
│   └── app.py
├── README.md
└── requirements.txt

4 directories, 5 files
```

---

## 📄 License

This project is licensed under the MIT License.
