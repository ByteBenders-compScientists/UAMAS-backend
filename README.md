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
cd uamas-backend
````

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set environment variables

Create a `.env` file and add:

```env
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=postgresql://user:password@localhost/uamas_db
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key
```

### 5. Run the app

```bash
flask run
```

---

## 🧪 Running Tests

```bash
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
