from datetime import date, time

from django.utils.dateparse import parse_date, parse_time

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from decimal import Decimal

from .models import (
    Employee,
    Attendance,
    Leave,
    Payroll,
    Task,
    Performance,
    Notification,
    EmployeeApplication,
)
from .forms import (
    AttendanceForm,
    EmployeeForm,
    LeaveForm,
    PayrollForm,
    PerformanceForm,
    TaskForm,
    TaskUpdateForm,
    EmployeeProfileForm,
)
from .services import employee_performance as calculate_performance
def notify_staff(title, message, application=None):
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            title=title,
            message=message,
            application=application,
        )
        for user in User.objects.filter(is_staff=True)
    ])


def admin_required(view):
    return never_cache(user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url='admin_login',
    )(view))


def employee_required(view):
    return never_cache(user_passes_test(
        lambda user: user.is_authenticated and hasattr(user, 'employee_profile'),
        login_url='employee_login',
    )(view))


# =========================================================
# WELCOME PAGE
# =========================================================

def welcome(request):
    """Public landing page shown before login."""

    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard_page')

        if hasattr(request.user, 'employee_profile'):
            return redirect('employee_dashboard')

    return render(
        request,
        'core/welcome.html'
    )


@ensure_csrf_cookie
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_page')
    error = None
    if request.method == 'POST':
        identity = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identity, password=password)
        if user is None and '@' in identity:
            account = User.objects.filter(email__iexact=identity).first()
            if account:
                user = authenticate(request, username=account.username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect(request.POST.get('next') or 'dashboard_page')
        error = 'Invalid administrator credentials.'
    return render(request, 'core/admin_login.html', {'error': error})


def employee_login(request):
    if request.user.is_authenticated and hasattr(request.user, 'employee_profile'):
        return redirect('employee_dashboard')
    error = None
    if request.method == 'POST':
        identity = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        employee = Employee.objects.filter(
            Q(employee_id__iexact=identity) | Q(email__iexact=identity)
        ).select_related('user').first()
        username = employee.user.username if employee and employee.user else identity
        user = authenticate(request, username=username, password=password)
        if user and hasattr(user, 'employee_profile') and user.employee_profile.is_active:
            login(request, user)
            return redirect('employee_dashboard')
        error = 'Invalid employee credentials.'
    return render(request, 'core/employee_login.html', {'error': error})


def logout_view(request):
    was_staff = request.user.is_authenticated and request.user.is_staff
    logout(request)
    return redirect('admin_login' if was_staff else 'employee_login')


@admin_required
def admin_profile(request):
    return render(request, 'core/admin_profile.html', {'admin_user': request.user})


@employee_required
def employee_dashboard(request):
    employee = request.user.employee_profile
    today = timezone.localdate()
    attendance = employee.attendances.filter(date=today).first()
    tasks = employee.tasks.order_by('due_date')
    metrics = calculate_performance(employee)
    context = {
        'employee': employee,
        'today': today,
        'today_attendance': attendance,
        'tasks': tasks,
        'completed_tasks': tasks.filter(status='completed').count(),
        'pending_tasks': tasks.exclude(status__in=['completed', 'cancelled']).count(),
        'metrics': metrics,
        'performance': metrics,
        'leaves': employee.leaves.order_by('-applied_at')[:5],
        'payroll': employee.payrolls.order_by('-month').first(),
    }
    return render(request, 'core/employee_dashboard.html', context)


@employee_required
def employee_attendance(request):
    employee = request.user.employee_profile
    return render(request, 'core/employee_attendance.html', {
        'employee': employee,
        'attendances': employee.attendances.all(),
        'today_attendance': employee.attendances.filter(date=timezone.localdate()).first(),
    })


@employee_required
def employee_check_in(request):
    if request.method != 'POST': return redirect('employee_attendance')
    employee = request.user.employee_profile
    attendance, created = Attendance.objects.get_or_create(
        employee=employee,
        date=timezone.localdate(),
        defaults={
            'status': 'late' if timezone.localtime().time() > time(9, 0) else 'present',
            'check_in': timezone.localtime().time(),
        },
    )
    if created:
        messages.success(request, 'Attendance checked in successfully.')
    else:
        messages.info(request, 'Attendance already marked today.')
    return redirect('employee_attendance')


@employee_required
def employee_check_out(request):
    if request.method != 'POST':
        return redirect('employee_attendance')
    attendance = Attendance.objects.filter(
        employee=request.user.employee_profile,
        date=timezone.localdate(),
    ).first()
    if not attendance or not attendance.check_in:
        messages.error(request, 'Check in before checking out.')
    elif attendance.check_out:
        messages.info(request, 'Attendance is already checked out.')
    else:
        attendance.check_out = timezone.localtime().time()
        attendance.save(update_fields=['check_out'])
        messages.success(request, 'Attendance checked out successfully.')
    return redirect('employee_attendance')


@employee_required
def employee_tasks(request):
    employee = request.user.employee_profile
    metrics = calculate_performance(employee)
    return render(request, 'core/employee_tasks.html', {
        'employee': employee, 'tasks': employee.tasks.all(), 'metrics': metrics,
    })


@employee_required
def employee_complete_task(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id, assigned_to=request.user.employee_profile)
        if task.status in ('cancelled', 'completed'):
            messages.info(request, 'This task is already closed.')
            return redirect('employee_tasks')
        task.status = 'completed'
        task.progress = 100
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'progress', 'completed_at', 'updated_at'])
        notify_staff('Task completed', f'{task.assigned_to.full_name} completed {task.title}.')
        messages.success(request, 'Task marked as completed.')
    return redirect('employee_tasks')

@employee_required
def employee_update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user.employee_profile)
    if request.method == 'POST' and task.status not in ('completed', 'cancelled'):
        form = TaskUpdateForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            if task.progress > 0 and task.started_at is None:
                task.started_at = timezone.now()
            if task.progress >= 100:
                task.status = 'completed'
                task.completed_at = timezone.now()
            else:
                task.status = 'in_progress'
            task.save()
            messages.success(request, 'Task progress updated.')
    return redirect('employee_tasks')


@employee_required
def employee_submit_task(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id, assigned_to=request.user.employee_profile)
        if task.status != 'cancelled' and task.status != 'submitted':
            task.submitted_at = timezone.now()
            task.status = 'completed'
            task.progress = 100
            task.completed_at = task.completed_at or timezone.now()
            task.save(update_fields=['submitted_at', 'status', 'progress', 'completed_at', 'updated_at'])
            messages.success(request, 'Task submitted for review.')
    return redirect('employee_tasks')


@employee_required
def employee_leave(request):
    employee = request.user.employee_profile
    form = LeaveForm(request.POST or None)
    form.fields['employee'].queryset = Employee.objects.filter(pk=employee.pk)
    if request.method == 'POST':
        data = request.POST.copy()
        data['employee'] = employee.pk
        form = LeaveForm(data)
        if form.is_valid():
            leave = form.save()
            refresh_payroll_for_leave(
                leave.employee,
                leave.start_date,
                leave.end_date
            )
            messages.success(request, 'Leave request submitted successfully.')
            notify_staff('New leave request', f'{employee.full_name} submitted a leave request.')
            return redirect('employee_leave')
    return render(request, 'core/employee_leave.html', {'employee': employee, 'form': form, 'leaves': employee.leaves.all()})


@employee_required
def employee_performance(request):
    employee = request.user.employee_profile
    return render(request, 'core/employee_performance.html', {
        'employee': employee,
        'metrics': calculate_performance(employee),
        'performances': employee.performance_records.all(),
    })


@employee_required
def employee_payroll(request):
    employee = request.user.employee_profile
    return render(request, 'core/employee_payroll.html', {'employee': employee, 'payrolls': employee.payrolls.all()})


@employee_required
def employee_profile(request):
    employee = request.user.employee_profile
    form = EmployeeProfileForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        employee = form.save()
        employee.user.email = employee.email
        employee.user.save(update_fields=['email'])
        messages.success(request, 'Profile updated successfully.')
        return redirect('employee_profile')
    return render(request, 'core/employee_profile.html', {'employee': employee, 'form': form})


@employee_required
def employee_password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('employee_profile')
    return render(request, 'registration/password_change_form.html', {'form': form})


# =========================================================
# DASHBOARD
# =========================================================

@admin_required
def dashboard(request):
    all_employees = Employee.objects.all().order_by(
        'employee_id'
    )

    active_employees = all_employees.filter(
        is_active=True
    )

    total_employees = all_employees.count()
    active_employee_count = active_employees.count()
    inactive_employee_count = all_employees.filter(
        is_active=False
    ).count()

    total_tasks = Task.objects.count()

    completed_tasks = Task.objects.filter(
        status='completed'
    ).count()

    pending_tasks = Task.objects.exclude(
        status__in=['completed', 'cancelled']
    ).count()

    total_leaves = Leave.objects.count()

    pending_leaves = Leave.objects.filter(
        status='pending'
    ).count()

    approved_leaves = Leave.objects.filter(
        status='approved'
    ).count()

    today = timezone.localdate()

    today_attendance = Attendance.objects.filter(
        date=today
    )

    present_today = today_attendance.filter(
        status='present'
    ).count()

    late_today = today_attendance.filter(
        status='late'
    ).count()

    present_late_today = present_today + late_today

    absent_today = today_attendance.filter(
        status='absent'
    ).count()

    average_performance = Performance.objects.aggregate(
        average=Avg('overall_score')
    )['average']

    if average_performance is None:
        average_performance = Decimal('0')

    task_status_counts = {
        status: Task.objects.filter(status=status).count()
        for status, _ in Task.STATUS_CHOICES
    }
    attendance_status_counts = {
        status: today_attendance.filter(status=status).count()
        for status, _ in Attendance.STATUS_CHOICES
    }
    payroll_total = Payroll.objects.aggregate(total=Avg('net_salary'))['total'] or Decimal('0')

    context = {
        'employees': all_employees,

        'total_employees': total_employees,
        'active_employees': active_employee_count,
        'inactive_employees': inactive_employee_count,

        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,

        'total_leaves': total_leaves,
        'pending_leaves': pending_leaves,
        'approved_leaves': approved_leaves,

        'present_today': present_today,
        'late_today': late_today,
        'present_late_today': present_late_today,
        'absent_today': absent_today,

        'average_performance': round(
            float(average_performance), 2
        ),
        'task_status_counts': task_status_counts,
        'attendance_status_counts': attendance_status_counts,
        'payroll_average': round(float(payroll_total), 2),
    }

    return render(
        request,
        'core/dashboard.html',
        context
    )


# =========================================================
# EMPLOYEE LIST
# =========================================================

@admin_required
def employee_list(request):
    query = request.GET.get('q', '').strip()
    active_filter = request.GET.get('active', '')
    all_employees = Employee.objects.all()
    employees = all_employees.order_by('employee_id')
    if query:
        employees = employees.filter(
            Q(employee_id__icontains=query)
            | Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(department__icontains=query)
            | Q(designation__icontains=query)
        )
    if active_filter in ('active', 'inactive'):
        employees = employees.filter(is_active=active_filter == 'active')

    return render(
        request,
        'core/employee_list.html',
        {
            'employees': employees,
            'query': query,
            'active_filter': active_filter,
            'total_employees': all_employees.count(),
            'active_employees': all_employees.filter(is_active=True).count(),
            'inactive_employees': all_employees.filter(is_active=False).count(),
        }
    )


# =========================================================
# EMPLOYEE DETAIL
# =========================================================

@admin_required
def employee_detail(request, employee_id):

    employee = get_object_or_404(
        Employee,
        employee_id=employee_id
    )

    attendance_records = employee.attendances.all()

    leave_records = employee.leaves.all()

    task_records = employee.tasks.all()

    performance_records = (
        employee.performance_records.all()
    )

    total_attendance = attendance_records.count()

    present_days = attendance_records.filter(
        status__in=['present', 'late']
    ).count()

    absent_days = attendance_records.filter(
        status='absent'
    ).count()

    half_days = attendance_records.filter(
        status='half_day'
    ).count()

    if total_attendance > 0:

        attendance_percentage = round(
            (
                (
                    present_days
                    + (half_days * 0.5)
                )
                / total_attendance
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    total_tasks = task_records.count()

    completed_tasks = task_records.filter(
        status='completed'
    ).count()

    if total_tasks > 0:

        task_completion_percentage = round(
            (
                completed_tasks /
                total_tasks
            ) * 100,
            2
        )

    else:

        task_completion_percentage = 0

    average_performance = (
        performance_records.aggregate(
            average=Avg('overall_score')
        )['average']
    )

    if average_performance is None:
        average_performance = 0

    context = {
        'employee': employee,
        'attendance_records': attendance_records,
        'leave_records': leave_records,
        'task_records': task_records,
        'performance_records': performance_records,

        'total_attendance': total_attendance,
        'present_days': present_days,
        'absent_days': absent_days,
        'half_days': half_days,
        'attendance_percentage': attendance_percentage,

        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'task_completion_percentage': (
            task_completion_percentage
        ),

        'average_performance': round(
            float(average_performance),
            2
        ),

        'remaining_leave': 0,
    }

    return render(
        request,
        'core/employee_detail.html',
        context
    )


# =========================================================
# EMPLOYEE ADD
# =========================================================

@admin_required
def employee_add(request):
    form = EmployeeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Employee added successfully.')
        return redirect('employee_list')

    return render(
        request,
        'core/employee_add.html',
        {
            'form': form,
        }
    )


# =========================================================
# EMPLOYEE EDIT
# =========================================================

@admin_required
def employee_edit(request, employee_id):

    employee = get_object_or_404(
        Employee,
        employee_id=employee_id
    )

    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Employee updated successfully.')
        return redirect('employee_detail', employee_id=employee.employee_id)

    return render(
        request,
        'core/employee_edit.html',
        {
            'employee': employee,
            'form': form,
        }
    )


# =========================================================
# EMPLOYEE DELETE
# =========================================================

@admin_required
def employee_delete(request, employee_id):

    employee = get_object_or_404(
        Employee,
        employee_id=employee_id
    )

    if request.method == 'POST':

        employee.delete()

        messages.success(
            request,
            'Employee deleted successfully.'
        )

        return redirect(
            'employee_list'
        )

    return render(
        request,
        'core/employee_delete.html',
        {
            'employee': employee
        }
    )


# =========================================================
# TASK LIST
# =========================================================

@admin_required
def task_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    tasks = Task.objects.select_related(
        'assigned_to'
    ).all()
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(assigned_to__full_name__icontains=query))
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)

    context = {
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'completed_tasks': tasks.filter(
            status='completed'
        ).count(),
        'in_progress_tasks': tasks.filter(
            status='in_progress'
        ).count(),
        'pending_tasks': tasks.filter(
            status__in=['todo', 'in_progress', 'review']
        ).count(),
        'query': query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'task_status_choices': Task.STATUS_CHOICES,
        'task_priority_choices': Task.PRIORITY_CHOICES,
    }

    return render(
        request,
        'core/task_list.html',
        context
    )


# =========================================================
# TASK DETAIL
# =========================================================

@admin_required
def task_detail(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id
    )

    return render(
        request,
        'core/task_detail.html',
        {
            'task': task
        }
    )


# =========================================================
# TASK ADD
# =========================================================

@admin_required
def task_add(request):
    form = TaskForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        task = form.save()
        if task.assigned_to.user:
            Notification.objects.create(
                recipient=task.assigned_to.user,
                title='New task assigned', message=f'{task.title} has been assigned to you.',
            )
        messages.success(request, 'Task created successfully.')
        return redirect('task_list')

    return render(
        request,
        'core/task_add.html',
        {
            'form': form,
        }
    )


# =========================================================
# TASK EDIT
# =========================================================

@admin_required
def task_edit(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id
    )

    form = TaskForm(request.POST or None, instance=task)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Task updated successfully.')
        return redirect('task_detail', task_id=task.id)

    return render(
        request,
        'core/task_edit.html',
        {
            'task': task,
            'form': form,
        }
    )


# =========================================================
# TASK DELETE
# =========================================================

@admin_required
def task_delete(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id
    )

    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted successfully.')
        return redirect('task_list')

    return render(request, 'core/task_delete.html', {'task': task})


# =========================================================
# PERFORMANCE LIST
# =========================================================

@admin_required
def performance_list(request):
    employee_filter = request.GET.get('employee', '')
    period_filter = request.GET.get('period', '')
    employees = Employee.objects.filter(is_active=True)
    performances = Performance.objects.select_related('employee').all()
    if employee_filter:
        performances = performances.filter(employee_id=employee_filter)
    if period_filter:
        performances = performances.filter(period=period_filter)

    performance_rows = [
        {'employee': employee, 'metrics': calculate_performance(employee)}
        for employee in employees.filter(**({'id': employee_filter} if employee_filter else {}))
    ]
    return render(
        request,
        'core/performance_list.html',
        {
            'performances': performances,
            'performance_rows': performance_rows,
            'employees': Employee.objects.all(),
            'employee_filter': employee_filter,
            'period_filter': period_filter,
        }
    )


# =========================================================
# PERFORMANCE DETAIL
# =========================================================

@admin_required
def performance_detail(
    request,
    performance_id
):

    performance = get_object_or_404(
        Performance,
        id=performance_id
    )

    metrics = calculate_performance(performance.employee)
    return render(
        request,
        'core/performance_detail.html',
        {
            'performance': performance
            , 'metrics': metrics,
        }
    )


@admin_required
def employee_performance_detail(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    return render(request, 'core/performance_employee.html', {
        'employee': employee,
        'metrics': calculate_performance(employee),
        'tasks': employee.tasks.order_by('-updated_at')[:10],
        'attendances': employee.attendances.all()[:10],
    })


# =========================================================
# EMPLOYEE APPLICATIONS
# =========================================================

@employee_required
def employee_applications(request):
    """
    Employee submits an application with an optional file.
    Administrators receive a notification linked to that application.
    """
    employee = request.user.employee_profile

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        application_type = request.POST.get(
            'application_type',
            'attendance_adjustment'
        )
        application_date = (
            parse_date(request.POST.get('application_date', ''))
            or timezone.localdate()
        )
        start_date = parse_date(request.POST.get('start_date', ''))
        end_date = parse_date(request.POST.get('end_date', ''))
        reason = request.POST.get('reason', '').strip()
        attachment = request.FILES.get('attachment')

        valid_types = {
            value
            for value, _ in EmployeeApplication.APPLICATION_TYPE_CHOICES
        }

        if not title:
            messages.error(request, 'Please enter an application title.')
        elif application_type not in valid_types:
            messages.error(request, 'Invalid application type.')
        elif not reason:
            messages.error(request, 'Please enter the reason.')
        elif start_date and end_date and end_date < start_date:
            messages.error(
                request,
                'End date cannot be earlier than start date.'
            )
        else:
            application = EmployeeApplication.objects.create(
                employee=employee,
                title=title,
                application_type=application_type,
                application_date=application_date,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                attachment=attachment,
            )

            notify_staff(
                'New employee application',
                f'{employee.full_name} submitted "{application.title}".',
                application=application,
            )

            messages.success(
                request,
                'Application submitted successfully.'
            )
            return redirect('employee_applications')

    return render(
        request,
        'core/employee_applications.html',
        {
            'employee': employee,
            'applications': employee.applications.all(),
            'application_types': (
                EmployeeApplication.APPLICATION_TYPE_CHOICES
            ),
        }
    )


# =========================================================
# ADMIN APPLICATION LIST
# =========================================================

@admin_required
def application_list(request):
    status_filter = request.GET.get('status', '').strip()
    employee_filter = request.GET.get('employee', '').strip()

    applications = EmployeeApplication.objects.select_related(
        'employee'
    ).all()

    if status_filter:
        applications = applications.filter(status=status_filter)

    if employee_filter:
        applications = applications.filter(
            employee_id=employee_filter
        )

    return render(
        request,
        'core/application_list.html',
        {
            'applications': applications,
            'employees': Employee.objects.all(),
            'employee_filter': employee_filter,
            'status_filter': status_filter,
            'application_status_choices': (
                EmployeeApplication.STATUS_CHOICES
            ),
        }
    )


# =========================================================
# ADMIN APPLICATION DETAIL / REVIEW
# =========================================================

@admin_required
def application_detail(request, application_id):
    application = get_object_or_404(
        EmployeeApplication.objects.select_related('employee'),
        id=application_id
    )

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action in ('approve', 'reject'):
            application.status = (
                'approved'
                if action == 'approve'
                else 'rejected'
            )
            application.admin_note = request.POST.get(
                'admin_note',
                ''
            ).strip()
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()

            application.save(
                update_fields=[
                    'status',
                    'admin_note',
                    'reviewed_by',
                    'reviewed_at',
                    'updated_at',
                ]
            )

            # Approved attendance-adjustment applications can update
            # the employee's attendance directly from this review page.
            if (
                action == 'approve'
                and application.application_type
                == 'attendance_adjustment'
            ):
                attendance_date = parse_date(
                    request.POST.get('attendance_date', '')
                )

                if attendance_date:
                    attendance_status = request.POST.get(
                        'attendance_status',
                        'present'
                    )

                    valid_statuses = {
                        value
                        for value, _ in Attendance.STATUS_CHOICES
                    }

                    if attendance_status in valid_statuses:
                        check_in = parse_time(
                            request.POST.get('check_in', '')
                        )
                        check_out = parse_time(
                            request.POST.get('check_out', '')
                        )

                        Attendance.objects.update_or_create(
                            employee=application.employee,
                            date=attendance_date,
                            defaults={
                                'status': attendance_status,
                                'check_in': check_in,
                                'check_out': check_out,
                            }
                        )

                        refresh_payroll_for_attendance(
                            application.employee,
                            attendance_date
                        )

            if application.employee.user:
                Notification.objects.create(
                    recipient=application.employee.user,
                    title='Application reviewed',
                    message=(
                        f'Your application "{application.title}" '
                        f'has been '
                        f'{application.get_status_display().lower()}.'
                    ),
                )

            messages.success(
                request,
                'Application review saved successfully.'
            )

            return redirect(
                'application_detail',
                application_id=application.id
            )

    return render(
        request,
        'core/application_detail.html',
        {
            'application': application,
            'attendance_status_choices': Attendance.STATUS_CHOICES,
        }
    )


# =========================================================
# ADMIN APPLICATION DELETE
# =========================================================

@admin_required
@require_POST
def application_delete(request, application_id):
    application = get_object_or_404(
        EmployeeApplication,
        id=application_id
    )

    application.delete()

    messages.success(
        request,
        'Application deleted successfully.'
    )

    return redirect('application_list')


@never_cache
def notification_list(request):
    if not request.user.is_authenticated:
        return redirect('employee_login')
    notifications = request.user.workpulse_notifications.all()[:30]
    return render(request, 'core/notifications.html', {'notifications': notifications})


@never_cache
@require_POST
def notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return redirect('employee_login')
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.read_at = timezone.now()
    notification.save(update_fields=['read_at'])
    return redirect(request.POST.get('next') or 'notification_list')


# =========================================================
# PERFORMANCE ADD
# =========================================================

@admin_required
def performance_add(request):
    form = PerformanceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        performance, created = Performance.objects.update_or_create(
            employee=form.cleaned_data['employee'],
            period=form.cleaned_data['period'],
            defaults={
                field: form.cleaned_data[field]
                for field in (
                    'productivity_score', 'quality_score',
                    'attendance_score', 'task_completion_score',
                    'manager_comment',
                )
            },
        )
        message = 'Performance record created successfully.'
        if not created:
            message = 'Existing performance record updated successfully.'
        messages.success(request, message)
        return redirect('performance_list')

    return render(
        request,
        'core/performance_add.html',
        {
            'form': form,
            'employees': Employee.objects.filter(is_active=True),
        }
    )


# =========================================================
# PERFORMANCE EDIT
# =========================================================

@admin_required
def performance_edit(
    request,
    performance_id
):

    performance = get_object_or_404(
        Performance,
        id=performance_id
    )

    form = PerformanceForm(request.POST or None, instance=performance)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except Exception as exc:
            if 'UNIQUE constraint failed' not in str(exc):
                raise
            messages.error(request, 'That employee already has a record for this period.')
        else:
            messages.success(request, 'Performance updated successfully.')
            return redirect('performance_detail', performance_id=performance.id)

    return render(
        request,
        'core/performance_edit.html',
        {
            'performance': performance,
            'form': form,
        }
    )


# =========================================================
# PERFORMANCE DELETE
# =========================================================

@admin_required
def performance_delete(
    request,
    performance_id
):

    performance = get_object_or_404(
        Performance,
        id=performance_id
    )

    if request.method == 'POST':
        performance.delete()
        messages.success(request, 'Performance record deleted successfully.')
        return redirect('performance_list')

    return render(
        request,
        'core/performance_delete.html',
        {'performance': performance},
    )


# =========================================================
# ATTENDANCE LIST
# =========================================================

@admin_required
def attendance_list(request):
    employee_filter = request.GET.get('employee', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    attendances = Attendance.objects.select_related(
        'employee'
    ).all()
    if employee_filter:
        attendances = attendances.filter(employee_id=employee_filter)
    if status_filter:
        attendances = attendances.filter(status=status_filter)
    if date_filter:
        attendances = attendances.filter(date=date_filter)

    return render(
        request,
        'core/attendance_list.html',
        {
            'attendances': attendances
            , 'employees': Employee.objects.all(),
            'employee_filter': employee_filter,
            'status_filter': status_filter,
            'date_filter': date_filter,
            'attendance_status_choices': Attendance.STATUS_CHOICES,
        }
    )


# =========================================================
# ATTENDANCE ADD
# =========================================================

@admin_required
def attendance_add(request):
    form = AttendanceForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            attendance = form.save()
        except Exception as exc:
            if 'UNIQUE constraint failed' not in str(exc):
                raise
            form.add_error(
                None,
                'Attendance for this employee on this date already exists.'
            )
        else:
            refresh_payroll_for_attendance(
                attendance.employee,
                attendance.date
            )
            messages.success(
                request,
                'Attendance added successfully and payroll updated.'
            )
            return redirect('attendance_list')

    return render(
        request,
        'core/attendance_add.html',
        {
            'form': form,
            'employees': Employee.objects.filter(is_active=True),
        }
    )




# =========================================================
# ATTENDANCE EDIT
# =========================================================

@admin_required
def attendance_edit(
    request,
    attendance_id
):
    attendance = get_object_or_404(
        Attendance,
        id=attendance_id
    )

    form = AttendanceForm(
        request.POST or None,
        instance=attendance
    )

    if request.method == 'POST' and form.is_valid():
        try:
            attendance = form.save()
        except Exception as exc:
            if 'UNIQUE constraint failed' not in str(exc):
                raise
            form.add_error(
                None,
                'Attendance for this employee on this date already exists.'
            )
        else:
            refresh_payroll_for_attendance(
                attendance.employee,
                attendance.date
            )
            messages.success(
                request,
                'Attendance updated successfully and payroll refreshed.'
            )
            return redirect('attendance_list')

    return render(
        request,
        'core/attendance_edit.html',
        {
            'attendance': attendance,
            'form': form,
            'employees': Employee.objects.filter(is_active=True),
        }
    )




# =========================================================
# ATTENDANCE DELETE
# =========================================================

@admin_required
def attendance_delete(
    request,
    attendance_id
):
    attendance = get_object_or_404(
        Attendance,
        id=attendance_id
    )

    if request.method == 'POST':
        employee = attendance.employee
        attendance_date = attendance.date
        attendance.delete()

        refresh_payroll_for_attendance(
            employee,
            attendance_date
        )

        messages.success(
            request,
            'Attendance deleted successfully and payroll refreshed.'
        )
        return redirect('attendance_list')

    return render(
        request,
        'core/attendance_delete.html',
        {'attendance': attendance}
    )




# =========================================================
# LEAVE LIST
# =========================================================

@admin_required
def leave_list(request):
    employee_filter = request.GET.get('employee', '')
    status_filter = request.GET.get('status', '')
    leave_type_filter = request.GET.get('leave_type', '')
    leaves = Leave.objects.select_related(
        'employee'
    ).all()
    if employee_filter:
        leaves = leaves.filter(employee_id=employee_filter)
    if status_filter:
        leaves = leaves.filter(status=status_filter)
    if leave_type_filter:
        leaves = leaves.filter(leave_type=leave_type_filter)

    return render(
        request,
        'core/leave_list.html',
        {
            'leaves': leaves
            , 'employees': Employee.objects.all(),
            'employee_filter': employee_filter,
            'status_filter': status_filter,
            'leave_type_filter': leave_type_filter,
            'leave_status_choices': Leave.STATUS_CHOICES,
            'leave_type_choices': Leave.LEAVE_TYPE_CHOICES,
        }
    )


# =========================================================
# LEAVE ADD
# =========================================================

@admin_required
def leave_add(request):
    form = LeaveForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        leave = form.save()

        refresh_payroll_for_leave(
            leave.employee,
            leave.start_date,
            leave.end_date
        )

        messages.success(
            request,
            'Leave request added successfully and payroll updated.'
        )
        return redirect('leave_list')

    return render(
        request,
        'core/leave_add.html',
        {
            'form': form,
            'employees': Employee.objects.filter(is_active=True),
            'error': '; '.join(
                str(error) for error in form.non_field_errors()
            ) or None,
        }
    )




# =========================================================
# LEAVE EDIT
# =========================================================

@admin_required
def leave_edit(
    request,
    leave_id
):
    leave = get_object_or_404(
        Leave,
        id=leave_id
    )

    old_employee = leave.employee
    old_start_date = leave.start_date
    old_end_date = leave.end_date

    form = LeaveForm(
        request.POST or None,
        instance=leave
    )

    if request.method == 'POST' and form.is_valid():
        leave = form.save()

        refresh_payroll_for_leave(
            old_employee,
            old_start_date,
            old_end_date
        )
        refresh_payroll_for_leave(
            leave.employee,
            leave.start_date,
            leave.end_date
        )

        messages.success(
            request,
            'Leave updated successfully and payroll refreshed.'
        )
        return redirect('leave_list')

    return render(
        request,
        'core/leave_edit.html',
        {
            'leave': leave,
            'form': form,
        }
    )




# =========================================================
# LEAVE DELETE
# =========================================================

@admin_required
def leave_delete(
    request,
    leave_id
):
    leave = get_object_or_404(
        Leave,
        id=leave_id
    )

    if request.method == 'POST':
        employee = leave.employee
        start_date = leave.start_date
        end_date = leave.end_date
        leave.delete()

        refresh_payroll_for_leave(
            employee,
            start_date,
            end_date
        )

        messages.success(
            request,
            'Leave request deleted successfully and payroll refreshed.'
        )
        return redirect('leave_list')

    return render(
        request,
        'core/leave_delete.html',
        {'leave': leave}
    )




# =========================================================
# PAYROLL LIST
# =========================================================

@admin_required
def payroll_list(request):
    employee_filter = request.GET.get('employee', '')
    month_filter = request.GET.get('month', '')

    payrolls = Payroll.objects.select_related(
        'employee'
    ).all()

    if employee_filter:
        payrolls = payrolls.filter(employee_id=employee_filter)

    if month_filter:
        payrolls = payrolls.filter(month=month_filter)

    # Automatic payrolls always reflect the latest attendance/leave data.
    for payroll in payrolls:
        if not payroll.manual_override:
            payroll.save()

    return render(
        request,
        'core/payroll_list.html',
        {
            'payrolls': payrolls,
            'employees': Employee.objects.all(),
            'employee_filter': employee_filter,
            'month_filter': month_filter,
        }
    )




@admin_required
def payroll_detail(request, payroll_id):
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee'),
        id=payroll_id
    )

    if not payroll.manual_override:
        payroll.save()
        payroll.refresh_from_db()

    return render(
        request,
        'core/payroll_detail.html',
        {'payroll': payroll}
    )


# =========================================================
# PAYROLL ADD
# =========================================================


# =========================================================
# PAYROLL ADD
# =========================================================

@admin_required
def payroll_add(request):
    form = PayrollForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        employee = form.cleaned_data['employee']
        month = form.cleaned_data['month']

        if Payroll.objects.filter(
            employee=employee,
            month=month
        ).exists():
            form.add_error(
                None,
                'Payroll for this employee and month already exists.'
            )
        else:
            payroll = form.save()
            if not payroll.manual_override:
                payroll.save()

            messages.success(
                request,
                'Payroll generated successfully from attendance and leave data.'
            )
            return redirect('payroll_list')

    return render(
        request,
        'core/payroll_add.html',
        {
            'form': form,
        }
    )




# =========================================================
# PAYROLL EDIT
# =========================================================

@admin_required
def payroll_edit(request, payroll_id):
    payroll = get_object_or_404(
        Payroll,
        id=payroll_id
    )

    if not payroll.manual_override and request.method != 'POST':
        payroll.save()
        payroll.refresh_from_db()

    form = PayrollForm(
        request.POST or None,
        instance=payroll
    )

    if request.method == 'POST' and form.is_valid():
        employee = form.cleaned_data['employee']
        month = form.cleaned_data['month']

        if Payroll.objects.filter(
            employee=employee,
            month=month
        ).exclude(id=payroll.id).exists():
            form.add_error(
                None,
                'Payroll for this employee and month already exists.'
            )
        else:
            payroll = form.save()

            if not payroll.manual_override:
                payroll.save()

            messages.success(
                request,
                'Payroll updated successfully.'
            )
            return redirect('payroll_list')

    return render(
        request,
        'core/payroll_edit.html',
        {
            'payroll': payroll,
            'form': form,
        }
    )




# =========================================================
# PAYROLL DELETE
# =========================================================

@admin_required
def payroll_delete(request, payroll_id):

    payroll = get_object_or_404(
        Payroll,
        id=payroll_id
    )

    if request.method == 'POST':
        payroll.delete()
        messages.success(request, 'Payroll deleted successfully.')
        return redirect('payroll_list')

    return render(request, 'core/payroll_delete.html', {'payroll': payroll})