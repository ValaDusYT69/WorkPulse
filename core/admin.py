from django.contrib import admin
from .models import (
    Employee,
    Leave,
    Attendance,
    CompanyPolicy,
    Payroll,
    Task,
    Performance,
    Notification,
)


# =========================================================
# EMPLOYEE ADMIN
# =========================================================

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        'employee_id',
        'user',
        'full_name',
        'department',
        'designation',
        'email',
        'monthly_salary',
        'is_active',
    )

    list_filter = (
        'department',
        'designation',
        'is_active',
    )

    search_fields = (
        'employee_id',
        'full_name',
        'email',
        'phone',
        'department',
        'designation',
    )

    ordering = (
        'employee_id',
    )


# =========================================================
# ATTENDANCE ADMIN
# =========================================================

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'date',
        'status',
        'check_in',
        'check_out',
    )

    list_filter = (
        'status',
        'date',
    )

    search_fields = (
        'employee__employee_id',
        'employee__full_name',
    )

    ordering = (
        '-date',
    )


# =========================================================
# LEAVE ADMIN
# =========================================================

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'leave_type',
        'start_date',
        'end_date',
        'days',
        'status',
        'applied_at',
    )

    list_filter = (
        'leave_type',
        'status',
        'start_date',
    )

    search_fields = (
        'employee__employee_id',
        'employee__full_name',
        'reason',
    )

    readonly_fields = (
        'days',
        'applied_at',
    )

    ordering = (
        '-applied_at',
    )


# =========================================================
# COMPANY POLICY ADMIN
# =========================================================

@admin.register(CompanyPolicy)
class CompanyPolicyAdmin(admin.ModelAdmin):

    list_display = (
        'company_name',
        'annual_leave_limit',
        'deduction_enabled',
        'working_days_per_month',
        'updated_at',
    )

    list_filter = (
        'deduction_enabled',
    )

    search_fields = (
        'company_name',
    )

    ordering = (
        '-updated_at',
    )


# =========================================================
# PAYROLL ADMIN
# =========================================================

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'month',
        'basic_salary',
        'working_days',
        'present_days',
        'leave_days',
        'deductions',
        'net_salary',
        'generated_at',
    )

    list_filter = (
        'month',
        'employee',
    )

    search_fields = (
        'employee__employee_id',
        'employee__full_name',
    )

    readonly_fields = (
        'basic_salary',
        'working_days',
        'present_days',
        'leave_days',
        'net_salary',
        'generated_at',
    )

    ordering = (
        '-month',
    )


# =========================================================
# TASK ADMIN
# =========================================================

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'assigned_to',
        'priority',
        'status',
        'progress',
        'due_date',
        'estimated_hours',
        'actual_hours',
        'updated_at',
    )

    list_filter = (
        'priority',
        'status',
        'due_date',
        'assigned_to',
    )

    search_fields = (
        'title',
        'description',
        'assigned_to__employee_id',
        'assigned_to__full_name',
    )

    list_editable = (
        'priority',
        'status',
        'progress',
    )

    ordering = (
        'due_date',
        '-priority',
    )


# =========================================================
# PERFORMANCE ADMIN
# =========================================================

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'period',
        'productivity_score',
        'quality_score',
        'attendance_score',
        'task_completion_score',
        'overall_score',
        'updated_at',
    )

    list_filter = (
        'period',
        'employee',
    )

    search_fields = (
        'employee__employee_id',
        'employee__full_name',
        'manager_comment',
    )

    readonly_fields = (
        'overall_score',
        'created_at',
        'updated_at',
    )

    ordering = (
        '-period',
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'created_at', 'read_at')
    list_filter = ('read_at', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')