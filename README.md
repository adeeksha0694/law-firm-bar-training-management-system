
# Integrated Law Firm & BAR Exam Training Management System

A full-stack web-based management system developed during my internship using Django and PostgreSQL. The system combines law firm management and BAR exam training into a single platform with role-based access for administrators, advocates, accountants, trainers, and students.

## Features

- User authentication and role-based access
- Client and case management
- Advocate management
- Hearing and task management
- Document management
- Batch, course, subject, and lesson management
- Training materials and assignments
- Assignment submissions
- Mock tests and evaluations
- Student performance tracking
- Announcements
- Invoice and expense management
- Student fee management
- Role-specific dashboards

## Technologies Used

- Python
- Django
- PostgreSQL
- HTML
- CSS
- Bootstrap
- JavaScript
- Git & GitHub

## Project Structure

```text
lawfirm_erp/
├── accounts/
├── audit/
├── cases/
├── clients/
├── documents/
├── finance/
├── lawfirm_erp/
├── notifications/
├── pages/
├── static/
├── tasks/
├── templates/
├── training/
├── users/
├── utils/
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md

## My Contribution

During my internship, I worked on:

* Django models, views, URLs, and templates
* PostgreSQL database integration
* User authentication and role-based access
* Client and case management
* Advocate dashboard and case interfaces
* BAR exam training and student modules
* Assignment and mock test functionality
* Finance and billing modules
* Frontend development using HTML, CSS, Bootstrap, and JavaScript

## Installation

### Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/law-firm-bar-exam-management-system.git
cd law-firm-bar-exam-management-system
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure PostgreSQL

Create a PostgreSQL database and configure your database credentials in a `.env` file.

```env
SECRET_KEY=your-secret-key
DB_NAME=your-database-name
DB_USER=your-postgres-user
DB_PASSWORD=your-postgres-password
DB_HOST=localhost
DB_PORT=5432
```

### Apply Migrations

```bash
python manage.py migrate
```

### Create Admin User

```bash
python manage.py createsuperuser
```

### Run the Project

```bash
python manage.py runserver
```

Open the application at:

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Project Type

Internship Project

## Author

**Adeeksha Shettigar**

MCA, Manipal Institute of Technology
