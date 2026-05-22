from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("membre/dashboard/", views.membre_dashboard, name="membre_dashboard"),

    # Membres - sections du dashboard
    path("membre/emprunts/", views.membre_emprunts, name="membre_emprunts"),
    path("membre/historique/", views.membre_historique, name="membre_historique"),
    path("membre/reservations/", views.membre_reservations, name="membre_reservations"),
    path("membre/favoris/", views.membre_favoris, name="membre_favoris"),
    path("membre/notifications/", views.membre_notifications, name="membre_notifications"),
    path("membre/messages/", views.membre_messages, name="membre_messages"),
    path("membre/recommandations/", views.membre_recommandations, name="membre_recommandations"),
    path("membre/sanctions/", views.membre_sanctions, name="membre_sanctions"),
    path("membre/profil/", views.membre_profil, name="membre_profil"),

    # Actions: reserver, favoris, notifications marque lu, messages send, prolonger emprunt
    path("action/reserve/", views.action_reserve, name="action_reserve"),
    path("membre/reserver/<int:id_livre>/", views.membre_reserver_livre, name="membre_reserver_livre"),
    path("action/reservation/cancel/<int:id_reservation>/", views.action_cancel_reservation, name="action_cancel_reservation"),
    path("action/favori/add/", views.action_add_favori, name="action_add_favori"),
    path("action/favori/delete/<int:id_livre>/", views.action_delete_favori, name="action_delete_favori"),
    path("action/notification/lu/<int:id_notification>/", views.action_notification_lu, name="action_notification_lu"),
    path("action/message/send/", views.action_send_message, name="action_send_message"),
    path("action/emprunt/prolonger/<int:id_emprunt>/", views.action_emprunt_prolonger, name="action_emprunt_prolonger"),
    path("action/avis/post/", views.action_post_avis, name="action_post_avis"),
]