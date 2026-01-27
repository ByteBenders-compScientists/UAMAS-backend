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

Create `.env` files in each service directory using the provided `.env.example` templates:

```bash
# Copy example files
cp Authentication/.env.example Authentication/.env
cp backend/.env.example backend/.env
cp api-gateway/.env.example api-gateway/.env

# Then edit each .env file with your actual values
```

**Important Cookie Configuration:**
- For **HTTP deployment** (development/testing): Set `JWT_COOKIE_SECURE=False` and `JWT_COOKIE_SAMESITE=Lax`
- For **HTTPS deployment** (production): Set `JWT_COOKIE_SECURE=True` and `JWT_COOKIE_SAMESITE=None`

See `.env.example` files for all available options.

For detailed cookie troubleshooting, see [COOKIE_FIX_GUIDE.md](COOKIE_FIX_GUIDE.md).

### 5. Deploy with Docker Compose

```bash
docker-compose up -d --build
```

### 6. Configure Nginx (for production deployment)

For production deployment with Nginx, see [nginx.conf.example](nginx.conf.example) for a complete configuration template.


### 7. Run the app locally (without Docker)

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
