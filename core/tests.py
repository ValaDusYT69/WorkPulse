from datetime import date
from django.utils import timezone

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Attendance, Employee, Leave, Notification, Payroll, Performance, Task
from .services import employee_performance


class WorkpulseWorkflowTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user('test-admin', password='admin-pass', is_staff=True)
		self.client.force_login(self.admin)
		self.employee = Employee.objects.create(
			employee_id='EMP-001',
			full_name='Ada Lovelace',
			email='ada@example.com',
			phone='5550100',
			department='Engineering',
			designation='Developer',
			joining_date=date(2026, 1, 1),
			monthly_salary='5000.00',
		)

	def test_primary_pages_render_and_search_works(self):
		for name in (
			'dashboard_page', 'employee_list', 'employee_add',
			'attendance_list', 'attendance_add', 'leave_list', 'leave_add',
			'task_list', 'task_add', 'performance_list', 'performance_add',
			'payroll_list', 'payroll_add',
		):
			self.assertEqual(self.client.get(reverse(name)).status_code, 200)

		response = self.client.get(reverse('employee_list'), {'q': 'ada'})
		self.assertContains(response, 'Ada Lovelace')
		self.assertContains(response, 'value="ada"')

	def test_leave_rejects_reversed_dates(self):
		response = self.client.post(reverse('leave_add'), {
			'employee': self.employee.id,
			'leave_type': 'annual',
			'start_date': '2026-08-10',
			'end_date': '2026-08-01',
			'status': 'pending',
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Leave.objects.count(), 0)
		self.assertContains(response, 'End date cannot be earlier')

	def test_performance_duplicate_updates_existing_record(self):
		payload = {
			'employee': self.employee.id,
			'period': '2026-08-01',
			'productivity_score': '8',
			'quality_score': '7',
			'attendance_score': '9',
			'task_completion_score': '6',
			'manager_comment': 'Initial review',
		}
		self.assertEqual(self.client.post(reverse('performance_add'), payload).status_code, 302)
		payload['productivity_score'] = '10'
		self.assertEqual(self.client.post(reverse('performance_add'), payload).status_code, 302)
		performance = Performance.objects.get()
		self.assertEqual(performance.productivity_score, 10)
		self.assertEqual(performance.overall_score, 8)

	def test_delete_confirmation_requires_post(self):
		attendance = Attendance.objects.create(employee=self.employee, date=date(2026, 8, 1))
		self.assertEqual(self.client.get(reverse('attendance_delete', args=[attendance.id])).status_code, 200)
		self.assertEqual(self.client.post(reverse('attendance_delete', args=[attendance.id])).status_code, 302)
		self.assertFalse(Attendance.objects.filter(id=attendance.id).exists())

		task = Task.objects.create(
			title='Test task', assigned_to=self.employee, due_date=date(2026, 8, 2)
		)
		self.assertEqual(self.client.get(reverse('task_delete', args=[task.id])).status_code, 200)
		self.assertEqual(self.client.post(reverse('task_delete', args=[task.id])).status_code, 302)
		self.assertFalse(Task.objects.filter(id=task.id).exists())

	def test_remaining_create_workflows(self):
		self.assertEqual(self.client.post(reverse('attendance_add'), {
			'employee': self.employee.id, 'date': '2026-08-03', 'status': 'present',
			'check_in': '09:00', 'check_out': '17:00',
		}).status_code, 302)
		self.assertEqual(self.client.post(reverse('leave_add'), {
			'employee': self.employee.id, 'leave_type': 'sick',
			'start_date': '2026-08-04', 'end_date': '2026-08-05', 'status': 'pending',
		}).status_code, 302)
		self.assertEqual(self.client.post(reverse('task_add'), {
			'title': 'Ship feature', 'assigned_to': self.employee.id,
			'priority': 'high', 'status': 'todo', 'progress': '0',
			'due_date': '2026-08-10', 'estimated_hours': '4', 'actual_hours': '0',
		}).status_code, 302)
		self.assertEqual(self.client.post(reverse('payroll_add'), {
			'employee': self.employee.id, 'month': '2026-08-01',
			'basic_salary': '5000', 'working_days': '30', 'deductions': '100',
		}).status_code, 302)
		performance = Performance.objects.create(
			employee=self.employee, period=date(2026, 7, 1),
			productivity_score=8, quality_score=8,
			attendance_score=8, task_completion_score=8,
		)
		self.assertEqual(self.client.get(reverse('performance_delete', args=[performance.id])).status_code, 200)
		self.assertEqual(self.client.post(reverse('performance_delete', args=[performance.id])).status_code, 302)
		self.assertFalse(Performance.objects.filter(id=performance.id).exists())

	def test_admin_and_employee_roles_are_separated(self):
		employee_user = User.objects.create_user('ada-login', password='employee-pass')
		self.employee.user = employee_user
		self.employee.save(update_fields=['user'])

		self.client.logout()
		self.assertEqual(self.client.get(reverse('employee_list')).status_code, 302)
		self.client.login(username='test-admin', password='admin-pass')
		self.assertEqual(self.client.get(reverse('employee_list')).status_code, 200)
		self.client.logout()

		self.client.login(username='ada-login', password='employee-pass')
		self.assertEqual(self.client.get(reverse('employee_dashboard')).status_code, 200)
		self.assertEqual(self.client.get(reverse('employee_list')).status_code, 302)
		self.assertEqual(self.client.get(reverse('employee_payroll')).status_code, 200)

	def test_employee_account_password_is_hashed(self):
		self.client.logout()
		response = self.client.post(reverse('admin_login'), {
			'username': 'missing', 'password': 'bad',
		})
		self.assertEqual(response.status_code, 200)
		self.client.force_login(User.objects.create_superuser('admin2', 'admin2@example.com', 'pass-12345'))
		self.client.post(reverse('employee_add'), {
			'employee_id': 'EMP-002', 'full_name': 'Grace Hopper',
			'email': 'grace@example.com', 'phone': '5550101',
			'department': 'Engineering', 'designation': 'Scientist',
			'joining_date': '2026-02-01', 'monthly_salary': '6000',
			'is_active': 'on', 'account_username': 'grace-login',
			'account_password': 'secret-pass',
		})
		user = User.objects.get(username='grace-login')
		self.assertNotEqual(user.password, 'secret-pass')
		self.assertTrue(user.check_password('secret-pass'))

	def test_employee_id_login_and_scoped_actions(self):
		user = User.objects.create_user('ada-portal', password='portal-pass')
		self.employee.user = user
		self.employee.save(update_fields=['user'])
		self.client.logout()
		response = self.client.post(reverse('employee_login'), {
			'username': 'EMP-001', 'password': 'portal-pass',
		})
		self.assertRedirects(response, reverse('employee_dashboard'))
		self.assertEqual(self.client.get(reverse('employee_dashboard')).status_code, 200)
		self.assertEqual(self.client.post(reverse('employee_check_in')).status_code, 302)
		self.assertEqual(Attendance.objects.filter(employee=self.employee).count(), 1)
		other = Employee.objects.create(
			employee_id='EMP-002', full_name='Grace Hopper', email='grace2@example.com',
			phone='5550102', department='Science', designation='Scientist',
			joining_date=date(2026, 1, 1),
		)
		foreign_task = Task.objects.create(
			title='Private task', assigned_to=other, due_date=date(2026, 8, 30)
		)
		self.assertEqual(self.client.post(reverse('employee_complete_task', args=[foreign_task.id])).status_code, 404)

	def test_employee_email_login_task_submission_and_live_metrics(self):
		employee_user = User.objects.create_user('ada-email', password='portal-pass')
		self.employee.user = employee_user
		self.employee.save(update_fields=['user'])
		task = Task.objects.create(title='Release build', assigned_to=self.employee, due_date=timezone.localdate())
		self.client.logout()
		self.assertEqual(self.client.post(reverse('employee_login'), {
			'username': 'ada@example.com', 'password': 'portal-pass',
		}).status_code, 302)
		self.assertEqual(self.client.post(reverse('employee_update_task', args=[task.id]), {'progress': 100}).status_code, 302)
		self.assertEqual(self.client.post(reverse('employee_submit_task', args=[task.id])).status_code, 302)
		task.refresh_from_db()
		self.assertEqual(task.status, 'completed')
		self.assertIsNotNone(task.submitted_at)
		metrics = employee_performance(self.employee)
		self.assertEqual(metrics['completed_tasks'], 1)
		self.assertEqual(metrics['on_time_tasks'], 1)

	def test_notifications_are_scoped_and_can_be_read(self):
		notification = Notification.objects.create(
			recipient=self.admin, title='Test', message='A workflow event',
		)
		self.assertContains(self.client.get(reverse('notification_list')), 'A workflow event')
		response = self.client.post(reverse('notification_read', args=[notification.id]))
		self.assertEqual(response.status_code, 302)
		notification.refresh_from_db()
		self.assertIsNotNone(notification.read_at)

	def test_role_logouts_and_employee_profile_password(self):
		self.assertEqual(self.client.get(reverse('dashboard_page')).headers['Cache-Control'], 'max-age=0, no-cache, no-store, must-revalidate, private')
		self.assertEqual(self.client.get(reverse('logout')).status_code, 302)
		self.assertEqual(self.client.get(reverse('admin_login')).status_code, 200)
		employee_user = User.objects.create_user('profile-user', password='old-password')
		self.employee.user = employee_user
		self.employee.save(update_fields=['user'])
		self.client.login(username='profile-user', password='old-password')
		self.assertEqual(self.client.post(reverse('employee_profile'), {
			'full_name': 'Ada Updated', 'email': 'ada@example.com', 'phone': '5550111',
		}).status_code, 302)
		self.assertEqual(self.client.post(reverse('employee_password_change'), {
			'old_password': 'old-password', 'new_password1': 'new-password-123',
			'new_password2': 'new-password-123',
		}).status_code, 302)
		self.client.get(reverse('logout'))
		self.assertTrue(self.client.login(username='profile-user', password='new-password-123'))
