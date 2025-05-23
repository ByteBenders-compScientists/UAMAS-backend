## 1. Obtain a JWT (Login)

**Request**

```
POST https://<your-api-host>/auth/login
Headers:
  Content-Type: application/json
Body (raw JSON):
{
  "email": "admin@university.edu",
  "password": "yourAdminPassword"
}
```

**Response**

```json
{
  "access_token": "<JWT_TOKEN>",
  "role": "admin"
}
```

---

## 2. Create a Course

**Request**

```
POST https://<your-api-host>/admin/courses
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>
Body (raw JSON):
{
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "department": "Computer Science",
  "school": "Engineering"
}
```

**Response**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "department": "Computer Science",
  "school": "Engineering",
  "units": []
}
```

---

## 3. Create a Unit

**Request**

```
POST https://<your-api-host>/admin/units
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>
Body (raw JSON):
{
  "unit_code": "CS101-1",
  "unit_name": "Programming Basics",
  "level": 1,
  "course_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "unit_code": "CS101-1",
  "unit_name": "Programming Basics",
  "level": 1,
  "course_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 4. Create a Student

**Request**

```
POST https://<your-api-host>/admin/students
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>
Body (raw JSON):
{
  "reg_number": "STU12345",
  "year_of_study": 1,
  "firstname": "Alice",
  "surname": "Wambui",
  "othernames": "Njeri",
  "course_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

> **What happens?**
>
> * A `User` with email `STU12345@university.edu` is created.
> * A `Student` record is created pointing at that course.
> * Their `units` property will automatically pull all level-1 units for that course.

**Response**

```json
{
  "student": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "reg_number": "STU12345",
    "year_of_study": 1,
    "firstname": "Alice",
    "surname": "Wambui",
    "othernames": "Njeri",
    "course": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "code": "CS101",
      "name": "Introduction to Computer Science",
      "department": "Computer Science",
      "school": "Engineering",
      "units": [
        {
          "id": "660e8400-e29b-41d4-a716-446655440001",
          "unit_code": "CS101-1",
          "unit_name": "Programming Basics",
          "level": 1,
          "course_id": "550e8400-e29b-41d4-a716-446655440000"
        }
      ]
    },
    "units": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "unit_code": "CS101-1",
        "unit_name": "Programming Basics",
        "level": 1,
        "course_id": "550e8400-e29b-41d4-a716-446655440000"
      }
    ]
  }
}
```

---

## 5. Create a Lecturer

**Request**

```
POST https://<your-api-host>/admin/lecturers
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>
Body (raw JSON):
{
  "email": "john.doe@university.edu",
  "firstname": "John",
  "surname": "Doe",
  "othernames": "Kibet"
}
```

**Response**

```json
{
  "lecturer": {
    "id": "990e8400-e29b-41d4-a716-446655440004",
    "user_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "firstname": "John",
    "surname": "Doe",
    "othernames": "Kibet",
    "units": []
  },
  "temp_password": "Ab3dE9xY"
}
```

---

## 6. Assign Units to a Lecturer

**Request**

```
POST https://<your-api-host>/admin/lecturers/990e8400-e29b-41d4-a716-446655440004/units
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>
Body (raw JSON):
{
  "unit_ids": [
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response**

```json
{
  "units": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "unit_code": "CS101-1",
      "unit_name": "Programming Basics",
      "level": 1,
      "course_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

---

### Tips for Postman

1. **Environments**: Create variables for `{{base_url}}` and `{{jwt_token}}`.
2. **Authorization**: In the **Authorization** tab choose “Bearer Token” and set it to `{{jwt_token}}`.
3. **Chaining**: After login, save the returned token into `{{jwt_token}}` via a test script:

   ```js
   pm.environment.set("jwt_token", pm.response.json().access_token);
   ```
4. **Reuse IDs**: When you create a Course/Unit/Student/Lecturer, copy the returned `id` into subsequent calls.
