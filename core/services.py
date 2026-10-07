from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from django.contrib.auth.models import User

from .models import Attendance, Notification, Task


GRADE_LABELS = {
    'A+': 'Outstanding',
    'A': 'Excellent',
    'B': 'Good',
    'C': 'Average',
    'D': 'Needs Improvement',
    'F': 'Critical',
}


def grade_for_score(score):
    score = Decimal(str(score or 0))
    if score >= 90:
        return 'A+'
    if score >= 80:
        return 'A'
    if score >= 70:
        return 'B'
    if score >= 60:
        return 'C'
    if score >= 50:
        return 'D'
    return 'F'


def _percentage(numerator, denominator):
    if not denominator:
        return Decimal('0')
    return (Decimal(numerator) / Decimal(denominator) * 100).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def employee_performance(employee):
    now = timezone.now()
    tasks = Task.objects.filter(assigned_to=employee)
    for task in tasks.exclude(status__in=['completed', 'cancelled']):
        if task.deadline < now and task.deadline_status == 'overdue' and task.status != 'overdue':
            task.status = 'overdue'
            task.save(update_fields=['status', 'updated_at'])
            recipients = list(User.objects.filter(is_staff=True))
            if task.assigned_to.user:
                recipients.append(task.assigned_to.user)
            Notification.objects.bulk_create([
                Notification(recipient=user, title='Task overdue', message=f'{task.title} is overdue.')
                for user in recipients
            ])

    assigned = tasks.exclude(status='cancelled').count()
    completed = tasks.filter(status='completed').count()
    submitted = tasks.filter(submitted_at__isnull=False).exclude(status='cancelled')
    on_time = sum(task.deadline_status == 'on_time' for task in submitted)
    late = sum(task.deadline_status == 'late' for task in submitted)
    pending = tasks.filter(status__in=['todo', 'in_progress', 'submitted', 'review']).count()
    overdue = tasks.filter(status='overdue').count()
    attendance = Attendance.objects.filter(employee=employee)
    present_days = attendance.filter(status__in=['present', 'late']).count()
    attendance_rate = _percentage(present_days, attendance.count())
    completion_rate = _percentage(completed, assigned)
    on_time_rate = _percentage(on_time, completed)
    behaviour_rate = _percentage(completed + on_time, assigned * 2)
    score = (completion_rate * Decimal('.40') + on_time_rate * Decimal('.25') +
             attendance_rate * Decimal('.20') + behaviour_rate * Decimal('.15')).quantize(Decimal('.01'))
    return {
        'total_tasks': assigned, 'completed_tasks': completed, 'pending_tasks': pending,
        'overdue_tasks': overdue, 'on_time_tasks': on_time, 'late_tasks': late,
        'completion_rate': completion_rate, 'on_time_rate': on_time_rate,
        'attendance_rate': attendance_rate, 'behaviour_rate': behaviour_rate,
        'overall_score': score, 'grade': grade_for_score(score),
        'grade_label': GRADE_LABELS[grade_for_score(score)], 'updated_at': now,
    }
