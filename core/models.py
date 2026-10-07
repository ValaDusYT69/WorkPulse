from datetime import datetime, time
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.utils import timezone


# =========================================================
# EMPLOYEE
# =========================================================

class Employee(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile'
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    full_name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True
    )

    phone = models.CharField(
        max_length=20
    )

    department = models.CharField(
        max_length=100
    )

    designation = models.CharField(
        max_length=100
    )

    joining_date = models.DateField()

    monthly_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"


# =========================================================
# ATTENDANCE
# =========================================================

class Attendance(models.Model):

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendances'
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='present'
    )

    check_in = models.TimeField(
        null=True,
        blank=True
    )

    check_out = models.TimeField(
        null=True,
        blank=True
    )

    @property
    def working_minutes(self):
        if not self.check_in or not self.check_out:
            return 0

        return (
            self.check_out.hour * 60 +
            self.check_out.minute
        ) - (
            self.check_in.hour * 60 +
            self.check_in.minute
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date'],
                name='unique_employee_attendance_per_day'
            )
        ]

        ordering = ['-date']

    def __str__(self):
        return (
            f"{self.employee.employee_id} - "
            f"{self.date} - "
            f"{self.status}"
        )


# =========================================================
# COMPANY POLICY
# =========================================================

class CompanyPolicy(models.Model):

    company_name = models.CharField(
        max_length=200
    )

    annual_leave_limit = models.PositiveIntegerField(
        default=15
    )

    deduction_enabled = models.BooleanField(
        default=True
    )

    working_days_per_month = models.PositiveIntegerField(
        default=30
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Company Policy"
        verbose_name_plural = "Company Policies"

    def __str__(self):
        return f"{self.company_name} Policy"


# =========================================================
# LEAVE
# =========================================================

class Leave(models.Model):

    LEAVE_TYPE_CHOICES = [
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('emergency', 'Emergency Leave'),
        ('unpaid', 'Unpaid Leave'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leaves'
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_TYPE_CHOICES
    )

    start_date = models.DateField()

    end_date = models.DateField()

    days = models.PositiveIntegerField(
        default=1
    )

    reason = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    applied_at = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError(
                    "End date cannot be earlier than start date."
                )

    def save(self, *args, **kwargs):

        if self.start_date and self.end_date:
            self.days = (
                self.end_date - self.start_date
            ).days + 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return (
            f"{self.employee.employee_id} - "
            f"{self.leave_type} - "
            f"{self.status}"
        )


# =========================================================
# PAYROLL
# =========================================================

class Payroll(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payrolls'
    )

    month = models.DateField(
        help_text="Use the first day of the payroll month."
    )

    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # -----------------------------------------------------
    # AUTOMATIC / CURRENT VALUES
    # -----------------------------------------------------

    working_days = models.PositiveIntegerField(
        default=30
    )

    present_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    leave_days = models.PositiveIntegerField(
        default=0
    )

    deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # -----------------------------------------------------
    # AUTOMATIC VALUES STORED FOR REFERENCE
    # -----------------------------------------------------

    auto_working_days = models.PositiveIntegerField(
        default=30
    )

    auto_present_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    auto_paid_leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    auto_unpaid_leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    auto_leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    auto_net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # -----------------------------------------------------
    # MANUAL OVERRIDE
    # -----------------------------------------------------

    manual_override = models.BooleanField(
        default=False,
        help_text=(
            "When enabled, admin values are used instead "
            "of automatic attendance/payroll values."
        )
    )

    manual_working_days = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    manual_present_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    manual_paid_leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    manual_unpaid_leave_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    manual_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    manual_net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    generated_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'month'],
                name='unique_employee_payroll_per_month'
            )
        ]

        ordering = ['-month']

    # =====================================================
    # MONTH RANGE
    # =====================================================

    def get_month_range(self):

        month_start = self.month.replace(day=1)

        if month_start.month == 12:

            next_month = month_start.replace(
                year=month_start.year + 1,
                month=1
            )

        else:

            next_month = month_start.replace(
                month=month_start.month + 1
            )

        return month_start, next_month

    # =====================================================
    # AUTOMATIC CALCULATION
    # =====================================================

    def calculate_automatic_values(self):

        if not self.employee or not self.month:
            return {
                'working_days': 30,
                'present_days': Decimal('0'),
                'paid_leave_days': Decimal('0'),
                'unpaid_leave_days': Decimal('0'),
                'leave_days': Decimal('0'),
                'net_salary': Decimal('0'),
            }

        month_start, next_month = self.get_month_range()

        # -------------------------------------------------
        # Company Policy
        # -------------------------------------------------

        policy = CompanyPolicy.objects.first()

        if policy:
            working_days = policy.working_days_per_month
        else:
            working_days = 30

        # -------------------------------------------------
        # Attendance
        # -------------------------------------------------

        attendance = Attendance.objects.filter(
            employee=self.employee,
            date__gte=month_start,
            date__lt=next_month
        )

        present = attendance.filter(
            status='present'
        ).count()

        late = attendance.filter(
            status='late'
        ).count()

        half_day = attendance.filter(
            status='half_day'
        ).count()

        present_days = (
            Decimal(present)
            + Decimal(late)
            + (
                Decimal(half_day) *
                Decimal('0.5')
            )
        )

        # -------------------------------------------------
        # Approved Leaves
        # -------------------------------------------------

        approved_leaves = Leave.objects.filter(
            employee=self.employee,
            status='approved',
            start_date__lt=next_month,
            end_date__gte=month_start
        )

        paid_leave = Decimal('0')
        unpaid_leave = Decimal('0')

        last_day = next_month.fromordinal(
            next_month.toordinal() - 1
        )

        for leave in approved_leaves:

            leave_start = max(
                leave.start_date,
                month_start
            )

            leave_end = min(
                leave.end_date,
                last_day
            )

            days = Decimal(
                (
                    leave_end - leave_start
                ).days + 1
            )

            if leave.leave_type == 'unpaid':
                unpaid_leave += days
            else:
                paid_leave += days

        leave_days = (
            paid_leave +
            unpaid_leave
        )

        # -------------------------------------------------
        # Basic Salary
        # -------------------------------------------------

        basic_salary = Decimal(
            str(
                self.basic_salary or
                self.employee.monthly_salary or
                '0'
            )
        )

        # -------------------------------------------------
        # Deductions
        # -------------------------------------------------

        deductions = Decimal(
            str(self.deductions or '0')
        )

        if working_days > 0:

            daily_salary = (
                basic_salary /
                Decimal(str(working_days))
            )

            payable_days = (
                present_days +
                paid_leave
            )

            earned_salary = (
                daily_salary *
                payable_days
            )

        else:

            earned_salary = Decimal('0')

        calculated_salary = (
            earned_salary -
            deductions
        )

        if calculated_salary < 0:
            calculated_salary = Decimal('0')

        return {
            'working_days': working_days,
            'present_days': present_days,
            'paid_leave_days': paid_leave,
            'unpaid_leave_days': unpaid_leave,
            'leave_days': leave_days,
            'net_salary': calculated_salary,
        }

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        # -------------------------------------------------
        # Basic salary
        # -------------------------------------------------

        self.basic_salary = Decimal(
            str(self.basic_salary or '0')
        )

        if self.employee and not self.basic_salary:

            self.basic_salary = Decimal(
                str(
                    self.employee.monthly_salary or
                    '0'
                )
            )

        # -------------------------------------------------
        # Calculate automatic values
        # -------------------------------------------------

        automatic = (
            self.calculate_automatic_values()
        )

        self.auto_working_days = (
            automatic['working_days']
        )

        self.auto_present_days = (
            automatic['present_days']
        )

        self.auto_paid_leave_days = (
            automatic['paid_leave_days']
        )

        self.auto_unpaid_leave_days = (
            automatic['unpaid_leave_days']
        )

        self.auto_leave_days = (
            automatic['leave_days']
        )

        self.auto_net_salary = (
            automatic['net_salary']
        )

        # -------------------------------------------------
        # Automatic mode
        # -------------------------------------------------

        if not self.manual_override:

            self.working_days = (
                automatic['working_days']
            )

            self.present_days = (
                automatic['present_days']
            )

            self.leave_days = int(
                automatic['leave_days']
            )

            self.net_salary = (
                automatic['net_salary']
            )

            self.deductions = Decimal(
                str(self.deductions or '0')
            )

        # -------------------------------------------------
        # Manual Override mode
        # -------------------------------------------------

        else:

            # Working days
            if self.manual_working_days is not None:
                self.working_days = (
                    self.manual_working_days
                )
            else:
                self.working_days = (
                    automatic['working_days']
                )

            # Present days
            if self.manual_present_days is not None:
                self.present_days = Decimal(
                    str(self.manual_present_days)
                )
            else:
                self.present_days = (
                    automatic['present_days']
                )

            # Paid leave
            if self.manual_paid_leave_days is not None:
                paid_leave = Decimal(
                    str(
                        self.manual_paid_leave_days
                    )
                )
            else:
                paid_leave = (
                    automatic['paid_leave_days']
                )

            # Unpaid leave
            if self.manual_unpaid_leave_days is not None:
                unpaid_leave = Decimal(
                    str(
                        self.manual_unpaid_leave_days
                    )
                )
            else:
                unpaid_leave = (
                    automatic['unpaid_leave_days']
                )

            self.leave_days = int(
                paid_leave + unpaid_leave
            )

            # Deductions
            if self.manual_deductions is not None:

                self.deductions = Decimal(
                    str(
                        self.manual_deductions
                    )
                )

            else:

                self.deductions = Decimal(
                    str(
                        self.deductions or '0'
                    )
                )

            # -------------------------------------------------
            # Manual Net Salary
            # -------------------------------------------------

            if self.manual_net_salary is not None:

                self.net_salary = Decimal(
                    str(
                        self.manual_net_salary
                    )
                )

            else:

                if self.working_days > 0:

                    daily_salary = (
                        self.basic_salary /
                        Decimal(
                            str(
                                self.working_days
                            )
                        )
                    )

                    payable_days = (
                        self.present_days +
                        paid_leave
                    )

                    earned_salary = (
                        daily_salary *
                        payable_days
                    )

                else:

                    earned_salary = Decimal('0')

                calculated_salary = (
                    earned_salary -
                    self.deductions
                )

                if calculated_salary < 0:
                    calculated_salary = Decimal('0')

                self.net_salary = (
                    calculated_salary
                )

        # -------------------------------------------------
        # Safety
        # -------------------------------------------------

        if self.working_days < 0:
            self.working_days = 0

        if self.present_days < 0:
            self.present_days = Decimal('0')

        if self.leave_days < 0:
            self.leave_days = 0

        if self.deductions < 0:
            self.deductions = Decimal('0')

        if self.net_salary < 0:
            self.net_salary = Decimal('0')

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.employee.employee_id} - "
            f"{self.month.strftime('%B %Y')}"
        )


# =========================================================
# EMPLOYEE APPLICATION
# =========================================================

class EmployeeApplication(models.Model):

    APPLICATION_TYPE_CHOICES = [
        (
            'attendance_adjustment',
            'Attendance Adjustment'
        ),
        (
            'leave_application',
            'Leave Application'
        ),
        (
            'other',
            'Other Application'
        ),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    title = models.CharField(
        max_length=200
    )

    application_type = models.CharField(
        max_length=30,
        choices=APPLICATION_TYPE_CHOICES,
        default='attendance_adjustment'
    )

    application_date = models.DateField(
        default=timezone.localdate
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    reason = models.TextField()

    attachment = models.FileField(
        upload_to='employee_applications/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'pdf',
                    'jpg',
                    'jpeg',
                    'png',
                    'doc',
                    'docx'
                ]
            )
        ]
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    admin_note = models.TextField(
        blank=True
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_employee_applications'
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):

        if (
            self.start_date and
            self.end_date and
            self.end_date < self.start_date
        ):

            raise ValidationError(
                "End date cannot be earlier than start date."
            )

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_approved(self):
        return self.status == 'approved'

    @property
    def is_rejected(self):
        return self.status == 'rejected'

    def __str__(self):

        return (
            f"{self.employee.employee_id} - "
            f"{self.title}"
        )

    class Meta:

        ordering = ['-created_at']


# =========================================================
# TASK
# =========================================================

class Task(models.Model):

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )

    progress = models.PositiveIntegerField(
        default=0
    )

    due_date = models.DateField()

    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    assigned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):

        if self.progress > 100:

            raise ValidationError(
                "Progress cannot be greater than 100%."
            )

    def save(self, *args, **kwargs):

        if self.assigned_at is None:
            self.assigned_at = timezone.now()

        if self.status == 'completed':

            self.progress = 100

            if self.completed_at is None:
                self.completed_at = timezone.now()

        if (
            self.progress >= 100 and
            self.status not in (
                'submitted',
                'cancelled'
            )
        ):

            self.progress = 100
            self.status = 'completed'

        super().save(*args, **kwargs)

    class Meta:

        ordering = [
            'due_date',
            '-priority'
        ]

    def __str__(self):
        return self.title

    @property
    def deadline(self):

        return timezone.make_aware(
            datetime.combine(
                self.due_date,
                time.max
            )
        )

    @property
    def deadline_status(self):

        if self.status == 'cancelled':
            return 'cancelled'

        if self.submitted_at:

            return (
                'on_time'
                if self.submitted_at <= self.deadline
                else 'late'
            )

        return (
            'overdue'
            if timezone.now() > self.deadline
            else 'pending'
        )


# =========================================================
# NOTIFICATION
# =========================================================

class Notification(models.Model):

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workpulse_notifications'
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    # -----------------------------------------------------
    # Optional application connection
    # -----------------------------------------------------

    application = models.ForeignKey(
        EmployeeApplication,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:

        ordering = ['-created_at']

    @property
    def is_read(self):
        return self.read_at is not None


# =========================================================
# PERFORMANCE
# =========================================================

class Performance(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='performance_records'
    )

    period = models.DateField(
        help_text="Use the first day of the evaluation month."
    )

    productivity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    attendance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    task_completion_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    manager_comment = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # OVERALL PERFORMANCE CALCULATION
    # =====================================================

    def calculate_overall_score(self):

        productivity = Decimal(
            str(
                self.productivity_score or
                '0'
            )
        )

        quality = Decimal(
            str(
                self.quality_score or
                '0'
            )
        )

        attendance = Decimal(
            str(
                self.attendance_score or
                '0'
            )
        )

        task_completion = Decimal(
            str(
                self.task_completion_score or
                '0'
            )
        )

        score = (
            productivity +
            quality +
            attendance +
            task_completion
        ) / Decimal('4')

        return score.quantize(
            Decimal('0.01')
        )

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        self.productivity_score = Decimal(
            str(
                self.productivity_score or
                '0'
            )
        )

        self.quality_score = Decimal(
            str(
                self.quality_score or
                '0'
            )
        )

        self.attendance_score = Decimal(
            str(
                self.attendance_score or
                '0'
            )
        )

        self.task_completion_score = Decimal(
            str(
                self.task_completion_score or
                '0'
            )
        )

        self.overall_score = (
            self.calculate_overall_score()
        )

        if kwargs.get('update_fields') is not None:

            update_fields = set(
                kwargs['update_fields']
            )

            update_fields.add(
                'overall_score'
            )

            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    # =====================================================
    # META
    # =====================================================

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'employee',
                    'period'
                ],
                name='unique_employee_performance_period'
            )
        ]

        ordering = ['-period']

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.employee.employee_id} - "
            f"{self.period.strftime('%B %Y')}"
        )