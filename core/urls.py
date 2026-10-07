from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    path(
        'login/',
        views.admin_login,
        name='admin_login'
    ),

    path(
        'employee/login/',
        views.employee_login,
        name='employee_login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

    path(
        'admin-profile/',
        views.admin_profile,
        name='admin_profile'
    ),


    # =====================================================
    # EMPLOYEE PORTAL
    # =====================================================

    path(
        'employee/',
        views.employee_dashboard,
        name='employee_dashboard_legacy'
    ),

    path(
        'employee/dashboard/',
        views.employee_dashboard,
        name='employee_dashboard'
    ),

    path(
        'employee/attendance/',
        views.employee_attendance,
        name='employee_attendance'
    ),

    path(
        'employee/attendance/check-in/',
        views.employee_check_in,
        name='employee_check_in'
    ),

    path(
        'employee/attendance/check-out/',
        views.employee_check_out,
        name='employee_check_out'
    ),

    path(
        'employee/tasks/',
        views.employee_tasks,
        name='employee_tasks'
    ),

    path(
        'employee/tasks/<int:task_id>/complete/',
        views.employee_complete_task,
        name='employee_complete_task'
    ),

    path(
        'employee/tasks/<int:task_id>/update/',
        views.employee_update_task,
        name='employee_update_task'
    ),

    path(
        'employee/tasks/<int:task_id>/submit/',
        views.employee_submit_task,
        name='employee_submit_task'
    ),

    path(
        'employee/leave/',
        views.employee_leave,
        name='employee_leave'
    ),

    path(
        'employee/performance/',
        views.employee_performance,
        name='employee_performance'
    ),

    path(
        'employee/payroll/',
        views.employee_payroll,
        name='employee_payroll'
    ),

    path(
        'employee/profile/',
        views.employee_profile,
        name='employee_profile'
    ),

    path(
        'employee/password/',
        views.employee_password_change,
        name='employee_password_change'
    ),


    # =====================================================
    # EMPLOYEE APPLICATIONS
    # =====================================================

    path(
        'employee/applications/',
        views.employee_applications,
        name='employee_applications'
    ),


    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    path(
        'notifications/',
        views.notification_list,
        name='notification_list'
    ),

    path(
        'notifications/<int:notification_id>/read/',
        views.notification_read,
        name='notification_read'
    ),


    # =====================================================
    # ADMIN APPLICATION MANAGEMENT
    # =====================================================

    path(
        'applications/',
        views.application_list,
        name='application_list'
    ),

    path(
        'applications/<int:application_id>/',
        views.application_detail,
        name='application_detail'
    ),

    path(
        'applications/<int:application_id>/delete/',
        views.application_delete,
        name='application_delete'
    ),


    # =====================================================
    # WELCOME / DASHBOARD
    # =====================================================

    path(
        '',
        views.welcome,
        name='welcome'
    ),

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard_page'
    ),


    # =====================================================
    # EMPLOYEES
    # =====================================================

    path(
        'employees/',
        views.employee_list,
        name='employee_list'
    ),

    path(
        'employees/add/',
        views.employee_add,
        name='employee_add'
    ),

    path(
        'employees/<str:employee_id>/',
        views.employee_detail,
        name='employee_detail'
    ),

    path(
        'employees/<str:employee_id>/edit/',
        views.employee_edit,
        name='employee_edit'
    ),

    path(
        'employees/<str:employee_id>/delete/',
        views.employee_delete,
        name='employee_delete'
    ),


    # =====================================================
    # ATTENDANCE
    # =====================================================

    path(
        'attendance/',
        views.attendance_list,
        name='attendance_list'
    ),

    path(
        'attendance/add/',
        views.attendance_add,
        name='attendance_add'
    ),

    path(
        'attendance/<int:attendance_id>/edit/',
        views.attendance_edit,
        name='attendance_edit'
    ),

    path(
        'attendance/<int:attendance_id>/delete/',
        views.attendance_delete,
        name='attendance_delete'
    ),


    # =====================================================
    # LEAVE
    # =====================================================

    path(
        'leaves/',
        views.leave_list,
        name='leave_list'
    ),

    path(
        'leaves/add/',
        views.leave_add,
        name='leave_add'
    ),

    path(
        'leaves/<int:leave_id>/edit/',
        views.leave_edit,
        name='leave_edit'
    ),

    path(
        'leaves/<int:leave_id>/delete/',
        views.leave_delete,
        name='leave_delete'
    ),


    # =====================================================
    # TASKS
    # =====================================================

    path(
        'tasks/',
        views.task_list,
        name='task_list'
    ),

    path(
        'tasks/add/',
        views.task_add,
        name='task_add'
    ),

    path(
        'tasks/<int:task_id>/',
        views.task_detail,
        name='task_detail'
    ),

    path(
        'tasks/<int:task_id>/edit/',
        views.task_edit,
        name='task_edit'
    ),

    path(
        'tasks/<int:task_id>/delete/',
        views.task_delete,
        name='task_delete'
    ),


    # =====================================================
    # PERFORMANCE
    # =====================================================

    path(
        'performance/',
        views.performance_list,
        name='performance_list'
    ),

    path(
        'performance/add/',
        views.performance_add,
        name='performance_add'
    ),

    path(
        'performance/<int:performance_id>/',
        views.performance_detail,
        name='performance_detail'
    ),

    path(
        'performance/employee/<str:employee_id>/',
        views.employee_performance_detail,
        name='employee_performance_detail'
    ),

    path(
        'performance/<int:performance_id>/edit/',
        views.performance_edit,
        name='performance_edit'
    ),

    path(
        'performance/<int:performance_id>/delete/',
        views.performance_delete,
        name='performance_delete'
    ),


    # =====================================================
    # PAYROLL
    # =====================================================

    path(
        'payrolls/',
        views.payroll_list,
        name='payroll_list'
    ),

    path(
        'payrolls/add/',
        views.payroll_add,
        name='payroll_add'
    ),

    path(
        'payrolls/<int:payroll_id>/',
        views.payroll_detail,
        name='payroll_detail'
    ),

    path(
        'payrolls/<int:payroll_id>/edit/',
        views.payroll_edit,
        name='payroll_edit'
    ),

    path(
        'payrolls/<int:payroll_id>/delete/',
        views.payroll_delete,
        name='payroll_delete'
    ),

]
