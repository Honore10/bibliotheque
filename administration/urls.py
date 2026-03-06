from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Admin
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Gestion du Personnel (CU-59 à CU-62)
    path('personnel/', views.personnel_list, name='admin_personnel_list'),
    path('personnel/create/', views.personnel_create, name='admin_personnel_create'),
    path('personnel/<int:id_personnel>/', views.personnel_detail, name='admin_personnel_detail'),
    path('personnel/<int:id_personnel>/edit/', views.personnel_edit, name='admin_personnel_edit'),
    path('personnel/<int:id_personnel>/delete/', views.personnel_delete, name='admin_personnel_delete'),
    path('personnel/<int:id_personnel>/role/', views.personnel_change_role, name='admin_personnel_change_role'),
    
    # Gestion des Types de Membres (CU-63 à CU-66)
    path('types-membres/', views.types_membres_list, name='admin_types_membres_list'),
    path('types-membres/create/', views.type_membre_create, name='admin_type_membre_create'),
    path('types-membres/<int:id_type>/', views.type_membre_detail, name='admin_type_membre_detail'),
    path('types-membres/<int:id_type>/edit/', views.type_membre_edit, name='admin_type_membre_edit'),
    path('types-membres/<int:id_type>/delete/', views.type_membre_delete, name='admin_type_membre_delete'),
    
    # Statistiques avancées (CU-67, CU-68)
    path('statistiques/', views.admin_statistiques, name='admin_statistiques'),
    path('statistiques/export/', views.admin_export_stats, name='admin_export_stats'),
]
