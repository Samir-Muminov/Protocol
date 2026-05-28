# protocol_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',    views.ProtocolLoginView.as_view(),  name='login'),
    path('logout/',   views.ProtocolLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(),       name='register'),

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Reports
    path('report/add/',             views.AddReportView.as_view(),    name='add_report'),
    path('report/add/<str:date>/',  views.AddReportView.as_view(),    name='add_report_date'),
    path('report/delete/<str:date>/', views.DeleteReportView.as_view(), name='delete_report'),

    # Export
    path('export/csv/', views.ExportCSVView.as_view(), name='export_csv'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # AJAX
    path('ajax/day/<str:date>/', views.DayCardAjaxView.as_view(),  name='day_card_ajax'),
    path('ajax/calendar/',       views.CalendarAjaxView.as_view(), name='calendar_ajax'),

    # Global report
    path('global/', views.GlobalReportView.as_view(), name='global_report'),
    path('__manage/seed/', views.ManagementCommandView.as_view(), name='management_seed'),
]