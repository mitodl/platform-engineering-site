# Runbook: Delete Student Grades for a Specific User in a Course

This runbook provides step-by-step instructions for deleting all grades for a specific student in a specific course using the Django shell.

## Key Grade Models in Open edX

- **PersistentCourseGrade**: Course-level grade (overall progress and pass/fail status)
- **PersistentSubsectionGrade**: Grades for individual subsections (chapters)
- **PersistentSubsectionGradeOverride**: Manual overrides to subsection grades
- **StudentModule**: Individual problem/block scores and state

## When to Use This Runbook

- Removing a student's grades due to academic integrity violations
- Testing/debugging grade calculations
- Correcting erroneous bulk grade imports
- Student de-enrollment cleanup

## Prerequisites

```bash
# Activate the virtual environment and navigate to platform root
cd /path/to/edx-platform
source .venv/bin/activate
```

## Step-by-Step Instructions

### 1. Open Django Shell

```bash
python manage.py shell -s lms
```

### 2. Define Required Values

```python
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

# Define the user and course
USERNAME = 'student_username'  # Replace with actual username
COURSE_ID = 'course-v1:OrgX+SC101+2024'  # Replace with actual course ID

# Get the user object
User = get_user_model()
user = User.objects.get(username=USERNAME)
user_id = user.id

# Parse the course key
course_key = CourseKey.from_string(COURSE_ID)

print(f"User ID: {user_id}")
print(f"Course Key: {course_key}")
```

### 3. Delete Course-Level Grades

Delete the student's overall course grade:

```python
from lms.djangoapps.grades.models import PersistentCourseGrade

try:
    grade = PersistentCourseGrade.objects.get(user_id=user_id, course_id=course_key)
    print(f"Deleting course grade: {grade}")
    grade.delete()
    print("✓ Course-level grade deleted")
except PersistentCourseGrade.DoesNotExist:
    print("✗ No course-level grade found")
```

### 4. Delete All Subsection Grades

Delete grades for all subsections/chapters in the course:

```python
from lms.djangoapps.grades.models import PersistentSubsectionGrade

count = PersistentSubsectionGrade.objects.filter(
    user_id=user_id,
    course_id=course_key
).delete()[0]

print(f"✓ Deleted {count} subsection grades")
```

### 5. Delete All Subsection Grade Overrides (Optional)

If there are any manual grade overrides, delete them:

```python
from lms.djangoapps.grades.models import PersistentSubsectionGradeOverride

overrides = PersistentSubsectionGradeOverride.objects.filter(
    grade__user_id=user_id,
    grade__course_id=course_key
)
count = overrides.delete()[0]

print(f"✓ Deleted {count} subsection grade overrides")
```

### 6. Delete Individual Problem/Block Scores (Optional)

If you also want to delete individual problem submissions and state:

```python
from lms.djangoapps.courseware.models import StudentModule

count = StudentModule.objects.filter(
    student_id=user_id,
    course_id=course_key
).delete()[0]

print(f"✓ Deleted {count} StudentModule records (problem submissions)")
```

## Complete Script (All-in-One)

Run this entire script at once to delete all grades for a student in a course:

```python
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from lms.djangoapps.grades.models import (
    PersistentCourseGrade,
    PersistentSubsectionGrade,
    PersistentSubsectionGradeOverride
)
from lms.djangoapps.courseware.models import StudentModule

# Configuration
USERNAME = 'student_username'  # CHANGE THIS
COURSE_ID = 'course-v1:OrgX+SC101+2024'  # CHANGE THIS

# Get user
User = get_user_model()
user = User.objects.get(username=USERNAME)
user_id = user.id
course_key = CourseKey.from_string(COURSE_ID)

print(f"Deleting grades for user_id={user_id}, course={COURSE_ID}")
print("-" * 60)

# Delete course-level grade
try:
    PersistentCourseGrade.objects.get(user_id=user_id, course_id=course_key).delete()
    print("✓ Deleted PersistentCourseGrade")
except PersistentCourseGrade.DoesNotExist:
    print("✗ No PersistentCourseGrade found")

# Delete subsection grades
count = PersistentSubsectionGrade.objects.filter(
    user_id=user_id,
    course_id=course_key
).delete()[0]
print(f"✓ Deleted {count} PersistentSubsectionGrade records")

# Delete grade overrides
count = PersistentSubsectionGradeOverride.objects.filter(
    grade__user_id=user_id,
    grade__course_id=course_key
).delete()[0]
print(f"✓ Deleted {count} PersistentSubsectionGradeOverride records")

# Delete problem submissions (optional)
count = StudentModule.objects.filter(
    student_id=user_id,
    course_id=course_key
).delete()[0]
print(f"✓ Deleted {count} StudentModule records")

print("-" * 60)
print("Grade deletion complete!")
```

## Verification

After deletion, verify that grades were removed:

```python
from lms.djangoapps.grades.models import PersistentCourseGrade, PersistentSubsectionGrade

# Check course grade
try:
    grade = PersistentCourseGrade.objects.get(user_id=user_id, course_id=course_key)
    print(f"✗ Course grade still exists: {grade}")
except PersistentCourseGrade.DoesNotExist:
    print("✓ Course grade successfully deleted")

# Check subsection grades
count = PersistentSubsectionGrade.objects.filter(
    user_id=user_id,
    course_id=course_key
).count()
if count == 0:
    print("✓ All subsection grades deleted")
else:
    print(f"✗ {count} subsection grades still exist")
```

## Important Notes

- **Backup First**: Consider backing up the database before running destructive operations
- **Student Re-enrollment**: Deleting grades does NOT unenroll the student from the course
- **History/Audit Trail**: SimpleHistory may retain records of deleted grades for audit purposes
- **Cached Data**: Deleting grades clears the RequestCache, but consider restarting if issues persist
- **Permissions**: Ensure you have database write permissions before running these commands

## Related Models

| Model | Purpose | Deletion Impact |
|-------|---------|-----------------|
| `PersistentCourseGrade` | Overall course grade & pass status | Recalculated on next submission |
| `PersistentSubsectionGrade` | Grade per subsection/chapter | Recalculated on next submission |
| `StudentModule` | Individual problem scores & state | Lost forever (can't resubmit old work) |
| `StudentModuleHistory` | Audit trail of state changes | Not automatically deleted |

## Troubleshooting

**User not found**:
```python
# List all users matching a pattern
User.objects.filter(username__icontains='student').values_list('username', 'id')
```

**Course not found**:
```python
# List all courses a user is enrolled in
from common.djangoapps.student.models import CourseEnrollment
CourseEnrollment.objects.filter(user_id=user_id).values_list('course_id')
```

**Permission denied**:
- Ensure you're using an admin/staff shell session
- Check database user privileges
- May need to run with elevated permissions or on database primary (not replica)
