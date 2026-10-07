from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from .models import (
    Attendance,
    Employee,
    Leave,
    Payroll,
    Performance,
    Task,
)


# =========================================================
# EMPLOYEE
# =========================================================

class EmployeeForm(forms.ModelForm):

    account_password = forms.CharField(
        required=False,
        label='Employee Login Password',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Set employee login password'
            }
        ),
        help_text=(
            'Employee can log in using Employee ID or Email '
            'with this password.'
        )
    )

    class Meta:
        model = Employee

        fields = (
            'employee_id',
            'full_name',
            'email',
            'phone',
            'department',
            'designation',
            'joining_date',
            'monthly_salary',
            'is_active',
        )

        widgets = {
            'joining_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),
        }

    # ---------------------------------------------------------
    # EMPLOYEE ID VALIDATION
    # ---------------------------------------------------------

    def clean_employee_id(self):
        employee_id = self.cleaned_data['employee_id'].strip()

        if not employee_id:
            raise forms.ValidationError(
                'Employee ID is required.'
            )

        # Employee ID must be unique
        queryset = Employee.objects.filter(
            employee_id__iexact=employee_id
        )

        # When editing an existing employee,
        # exclude the current employee.
        if self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise forms.ValidationError(
                'This Employee ID is already in use.'
            )

        # Employee ID is also used as Django username.
        # So prevent username conflict.
        user_queryset = User.objects.filter(
            username__iexact=employee_id
        )

        if self.instance.user_id:
            user_queryset = user_queryset.exclude(
                pk=self.instance.user_id
            )

        if user_queryset.exists():
            raise forms.ValidationError(
                'This Employee ID is already connected '
                'to another login account.'
            )

        return employee_id

    # ---------------------------------------------------------
    # PASSWORD VALIDATION
    # ---------------------------------------------------------

    def clean_account_password(self):
        password = self.cleaned_data.get(
            'account_password'
        )

        # New employee must have a password.
        if not self.instance.pk and not password:
            raise forms.ValidationError(
                'Please set a login password for the employee.'
            )

        return password

    # ---------------------------------------------------------
    # SAVE EMPLOYEE + AUTOMATIC LOGIN ACCOUNT
    # ---------------------------------------------------------

    def save(self, commit=True):

        employee = super().save(
            commit=commit
        )

        if not commit:
            return employee

        password = self.cleaned_data.get(
            'account_password'
        )

        # -------------------------------------------------
        # AUTOMATIC LOGIN ACCOUNT
        #
        # Employee ID = Django username
        # -------------------------------------------------

        username = employee.employee_id

        user = employee.user

        # -------------------------------------------------
        # CREATE LOGIN ACCOUNT
        # -------------------------------------------------

        if user is None:

            user = User.objects.create_user(
                username=username,
                email=employee.email,
                password=password
            )

            # Connect Django User with Employee
            employee.user = user

            employee.save(
                update_fields=['user']
            )

        # -------------------------------------------------
        # UPDATE EXISTING LOGIN ACCOUNT
        # -------------------------------------------------

        else:

            # Keep username synchronized
            if user.username != username:
                user.username = username

            # Keep email synchronized
            user.email = employee.email

            # Only change password if admin
            # entered a new password.
            if password:
                user.set_password(password)

            user.save()

        return employee


# =========================================================
# EMPLOYEE PROFILE
# =========================================================

class EmployeeProfileForm(forms.ModelForm):

    class Meta:
        model = Employee

        fields = (
            'full_name',
            'email',
            'phone',
        )


# =========================================================
# ATTENDANCE
# =========================================================

class AttendanceForm(forms.ModelForm):

    class Meta:
        model = Attendance

        fields = (
            'employee',
            'date',
            'status',
            'check_in',
            'check_out',
        )

        widgets = {

            'date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'check_in': forms.TimeInput(
                attrs={
                    'type': 'time'
                }
            ),

            'check_out': forms.TimeInput(
                attrs={
                    'type': 'time'
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        check_in = cleaned_data.get(
            'check_in'
        )

        check_out = cleaned_data.get(
            'check_out'
        )

        if (
            check_in
            and check_out
            and check_out < check_in
        ):
            raise ValidationError(
                'Check-out cannot be earlier than check-in.'
            )

        return cleaned_data


# =========================================================
# LEAVE
# =========================================================

class LeaveForm(forms.ModelForm):

    class Meta:
        model = Leave

        fields = (
            'employee',
            'leave_type',
            'start_date',
            'end_date',
            'reason',
            'status',
        )

        widgets = {

            'start_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'end_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get(
            'start_date'
        )

        end_date = cleaned_data.get(
            'end_date'
        )

        if (
            start_date
            and end_date
            and end_date < start_date
        ):
            raise ValidationError(
                'End date cannot be earlier than start date.'
            )

        return cleaned_data


# =========================================================
# TASK
# =========================================================

class TaskForm(forms.ModelForm):

    class Meta:
        model = Task

        fields = (
            'title',
            'description',
            'assigned_to',
            'priority',
            'status',
            'progress',
            'due_date',
            'estimated_hours',
            'actual_hours',
        )

        widgets = {
            'due_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            )
        }

    def clean_progress(self):

        progress = self.cleaned_data[
            'progress'
        ]

        if progress > 100:
            raise forms.ValidationError(
                'Progress cannot be greater than 100%.'
            )

        return progress


# =========================================================
# TASK UPDATE
# =========================================================

class TaskUpdateForm(forms.ModelForm):

    class Meta:
        model = Task

        fields = (
            'progress',
        )

    def clean_progress(self):

        progress = self.cleaned_data[
            'progress'
        ]

        if progress > 100:
            raise forms.ValidationError(
                'Progress cannot be greater than 100%.'
            )

        return progress


# =========================================================
# PERFORMANCE
# =========================================================

class PerformanceForm(forms.ModelForm):

    class Meta:
        model = Performance

        fields = (
            'employee',
            'period',
            'productivity_score',
            'quality_score',
            'attendance_score',
            'task_completion_score',
            'manager_comment',
        )

        widgets = {
            'period': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            )
        }

    def clean(self):

        cleaned_data = super().clean()

        score_fields = (
            'productivity_score',
            'quality_score',
            'attendance_score',
            'task_completion_score',
        )

        for field_name in score_fields:

            value = cleaned_data.get(
                field_name
            )

            if (
                value is not None
                and not 0 <= value <= 10
            ):
                self.add_error(
                    field_name,
                    'Score must be between 0 and 10.'
                )

        return cleaned_data

    def validate_unique(self):

        # The add view intentionally upserts
        # an existing employee-period row.
        return None

    def _post_clean(self):

        super()._post_clean()

        if self._errors.get('__all__'):
            del self._errors['__all__']


# =========================================================
# PAYROLL
# =========================================================

class PayrollForm(forms.ModelForm):

    class Meta:
        model = Payroll

        fields = (
            'employee',
            'month',
            'basic_salary',
            'manual_override',
            'working_days',
            'present_days',
            'leave_days',
            'deductions',
            'net_salary',
            'manual_working_days',
            'manual_present_days',
            'manual_paid_leave_days',
            'manual_unpaid_leave_days',
            'manual_deductions',
            'manual_net_salary',
        )

        widgets = {
            'month': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'working_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'readonly': True,
                }
            ),

            'present_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'readonly': True,
                }
            ),

            'leave_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'readonly': True,
                }
            ),

            'net_salary': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'readonly': True,
                }
            ),

            'manual_working_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'placeholder': 'Manual working days'
                }
            ),

            'manual_present_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'placeholder': 'Manual present days'
                }
            ),

            'manual_paid_leave_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'placeholder': 'Manual paid leave days'
                }
            ),

            'manual_unpaid_leave_days': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'placeholder': 'Manual unpaid leave days'
                }
            ),

            'manual_deductions': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'placeholder': 'Manual deductions'
                }
            ),

            'manual_net_salary': forms.NumberInput(
                attrs={
                    'min': 0,
                    'step': '0.01',
                    'placeholder': 'Manual net salary'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Automatic values are calculated by Payroll.save().
        # They are displayed but should not be edited directly.
        for field_name in (
            'working_days',
            'present_days',
            'leave_days',
            'net_salary',
        ):
            self.fields[field_name].required = False

        # Manual fields are optional until manual override is enabled.
        for field_name in (
            'manual_working_days',
            'manual_present_days',
            'manual_paid_leave_days',
            'manual_unpaid_leave_days',
            'manual_deductions',
            'manual_net_salary',
        ):
            self.fields[field_name].required = False

        # Existing payroll records show the saved automatic/manual mode.
        if self.instance and self.instance.pk:
            self.initial['manual_override'] = self.instance.manual_override

    def clean(self):
        cleaned_data = super().clean()

        month = cleaned_data.get('month')
        employee = cleaned_data.get('employee')
        manual_override = cleaned_data.get('manual_override')

        if month and month.day != 1:
            self.add_error(
                'month',
                'Use the first day of the payroll month.'
            )

        # Do not silently allow two payroll records for the same
        # employee/month.
        if employee and month:
            queryset = Payroll.objects.filter(
                employee=employee,
                month=month
            )

            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                self.add_error(
                    'month',
                    'A payroll record already exists for this employee and month.'
                )

        # In manual mode, validate the manual values.
        if manual_override:

            manual_working_days = cleaned_data.get(
                'manual_working_days'
            )

            manual_present_days = cleaned_data.get(
                'manual_present_days'
            )

            manual_paid_leave_days = cleaned_data.get(
                'manual_paid_leave_days'
            )

            manual_unpaid_leave_days = cleaned_data.get(
                'manual_unpaid_leave_days'
            )

            manual_deductions = cleaned_data.get(
                'manual_deductions'
            )

            manual_net_salary = cleaned_data.get(
                'manual_net_salary'
            )

            if (
                manual_working_days is not None
                and manual_working_days < 0
            ):
                self.add_error(
                    'manual_working_days',
                    'Working days cannot be negative.'
                )

            for field_name, value in (
                ('manual_present_days', manual_present_days),
                ('manual_paid_leave_days', manual_paid_leave_days),
                ('manual_unpaid_leave_days', manual_unpaid_leave_days),
                ('manual_deductions', manual_deductions),
                ('manual_net_salary', manual_net_salary),
            ):
                if value is not None and value < 0:
                    self.add_error(
                        field_name,
                        'Value cannot be negative.'
                    )

            if (
                manual_working_days is not None
                and manual_present_days is not None
                and manual_present_days > manual_working_days
            ):
                self.add_error(
                    'manual_present_days',
                    'Present days cannot exceed working days.'
                )

        return cleaned_data
