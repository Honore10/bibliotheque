from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.staff_dashboard, name="staff_dashboard"),

    # Livres management
    path("livres/", views.books_list, name="staff_books_list"),
    path("livres/new/", views.book_create, name="staff_book_create"),
    path("livres/<int:id_livre>/", views.book_detail, name="staff_book_detail"),
    path("livres/<int:id_livre>/edit/", views.book_edit, name="staff_book_edit"),
    path("livres/<int:id_livre>/delete/", views.book_delete, name="staff_book_delete"),
    path("livres/<int:id_livre>/upload_cover/", views.book_upload_cover, name="staff_book_upload_cover"),

    # Exemplaires management
    path("exemplaires/", views.exemplaires_list, name="staff_exemplaires_list"),
    path("exemplaires/new/", views.exemplaire_create, name="staff_exemplaire_create"),
    path("exemplaires/<int:id_exemplaire>/", views.exemplaire_detail, name="staff_exemplaire_detail"),
    path("exemplaires/<int:id_exemplaire>/edit/", views.exemplaire_edit, name="staff_exemplaire_edit"),
    path("exemplaires/<int:id_exemplaire>/delete/", views.exemplaire_delete, name="staff_exemplaire_delete"),
    path("exemplaires/<int:id_exemplaire>/etat/", views.exemplaire_update_etat, name="staff_exemplaire_update_etat"),

    # Catégories management (CU-29 à CU-32)
    path("categories/", views.categories_list, name="staff_categories_list"),
    path("categories/new/", views.category_create, name="staff_category_create"),
    path("categories/<int:id_categorie>/edit/", views.category_edit, name="staff_category_edit"),
    path("categories/<int:id_categorie>/delete/", views.category_delete, name="staff_category_delete"),

    # Auteurs management (CU-33 à CU-36)
    path("auteurs/", views.auteurs_list, name="staff_auteurs_list"),
    path("auteurs/new/", views.auteur_create, name="staff_auteur_create"),
    path("auteurs/<int:id_auteur>/edit/", views.auteur_edit, name="staff_auteur_edit"),
    path("auteurs/<int:id_auteur>/delete/", views.auteur_delete, name="staff_auteur_delete"),

    # Membres management (CRUD)
    path("membres/", views.members_list, name="staff_members_list"),
    path("membres/new/", views.member_create, name="staff_member_create"),
    path("membres/<int:id_membre>/", views.member_detail, name="staff_member_detail"),
    path("membres/<int:id_membre>/edit/", views.member_edit, name="staff_member_edit"),
    path("membres/<int:id_membre>/delete/", views.member_delete, name="staff_member_delete"),
    path("membres/<int:id_membre>/statut/", views.member_change_statut, name="staff_member_change_statut"),

    # Emprunts management
    path("emprunts/", views.emprunts_list, name="staff_emprunts_list"),
    path("emprunts/new/", views.emprunt_create, name="staff_emprunt_create"),
    path("emprunts/<int:id_emprunt>/", views.emprunt_detail, name="staff_emprunt_detail"),
    path("emprunts/<int:id_emprunt>/retour/", views.emprunt_retour, name="staff_emprunt_retour"),
    path("emprunts/<int:id_emprunt>/prolonger/", views.emprunt_prolonger, name="staff_emprunt_prolonger"),

    # Réservations management (CU-48 à CU-51)
    path("reservations/", views.reservations_list, name="staff_reservations_list"),
    path("reservations/new/", views.reservation_create, name="staff_reservation_create"),
    path("reservations/<int:id_reservation>/valider/", views.reservation_valider, name="staff_reservation_valider"),
    path("reservations/<int:id_reservation>/annuler/", views.reservation_annuler, name="staff_reservation_annuler"),

    # Sanctions management (CU-52 à CU-55)
    path("sanctions/", views.sanctions_list, name="staff_sanctions_list"),
    path("sanctions/new/", views.sanction_create, name="staff_sanction_create"),
    path("sanctions/<int:id_sanction>/", views.sanction_detail, name="staff_sanction_detail"),
    path("sanctions/<int:id_sanction>/statut/", views.sanction_update_statut, name="staff_sanction_update_statut"),

    # Messages management (CU-56 à CU-57)
    path("messages/", views.staff_messages_list, name="staff_messages_list"),
    path("messages/membre/<int:id_membre>/", views.staff_messages_membre, name="staff_messages_membre"),
    path("messages/<int:id_message>/reply/", views.staff_message_reply, name="staff_message_reply"),
]