# -*- coding: utf-8 -*-
"""
Configuration admin Django pour gérer les utilisateurs et les données MSSQL
"""
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import (
    TypeMembre, Membre, Bibliothecaire, Categorie, Auteur, Livre,
    LivresAuteur, Exemplaire, Emprunt, Reservation, Sanction,
    Notification, Avis, Favori, Message
)


@admin.register(TypeMembre)
class TypeMembreAdmin(ModelAdmin):
    list_display = ('nom_type', 'duree_max_emprunt', 'nb_max_emprunt', 'created_at')
    search_fields = ('nom_type',)
    ordering = ('nom_type',)


@admin.register(Membre)
class MembreAdmin(ModelAdmin):
    list_display = ('numero_carte', 'nom', 'prenom', 'email', 'statut_compte', 'user_type', 'date_inscription')
    search_fields = ('numero_carte', 'nom', 'prenom', 'email', 'login')
    list_filter = ('statut_compte', 'user_type', 'id_type_membre', 'date_inscription')
    ordering = ('-date_inscription',)
    readonly_fields = ('created_at', 'updated_at', 'date_inscription')


@admin.register(Bibliothecaire)
class BibliothecaireAdmin(ModelAdmin):
    list_display = ('matricule', 'nom', 'prenom', 'email', 'role', 'actif', 'user_type')
    search_fields = ('matricule', 'nom', 'prenom', 'email', 'login')
    list_filter = ('role', 'actif', 'user_type', 'created_at')
    ordering = ('matricule',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Categorie)
class CategorieAdmin(ModelAdmin):
    list_display = ('nom_categorie', 'created_at')
    search_fields = ('nom_categorie',)
    ordering = ('nom_categorie',)


@admin.register(Auteur)
class AuteurAdmin(ModelAdmin):
    list_display = ('nom', 'prenom', 'created_at')
    search_fields = ('nom', 'prenom')
    ordering = ('nom', 'prenom')


@admin.register(Livre)
class LivreAdmin(ModelAdmin):
    list_display = ('titre', 'isbn', 'id_categorie', 'date_ajout_catalogue')
    search_fields = ('titre', 'isbn')
    list_filter = ('id_categorie', 'date_ajout_catalogue')
    ordering = ('-date_ajout_catalogue',)
    readonly_fields = ('created_at', 'updated_at', 'date_ajout_catalogue')


@admin.register(LivresAuteur)
class LivresAuteurAdmin(ModelAdmin):
    list_display = ('id_livre', 'id_auteur', 'created_at')
    search_fields = ('id_livre__titre', 'id_auteur__nom')
    list_filter = ('id_livre', 'id_auteur')
    ordering = ('id_livre', 'id_auteur')


@admin.register(Exemplaire)
class ExemplaireAdmin(ModelAdmin):
    list_display = ('code_barre', 'id_livre', 'etat', 'statut_logique', 'date_acquisition')
    search_fields = ('code_barre', 'id_livre__titre')
    list_filter = ('etat', 'statut_logique', 'date_acquisition')
    ordering = ('-date_acquisition',)
    readonly_fields = ('created_at', 'updated_at', 'date_acquisition')


@admin.register(Emprunt)
class EmpruntAdmin(ModelAdmin):
    list_display = ('id_membre', 'id_exemplaire', 'date_emprunt', 'date_retour_prevue', 'statut')
    search_fields = ('id_membre__nom', 'id_exemplaire__code_barre')
    list_filter = ('statut', 'date_emprunt', 'date_retour_prevue')
    ordering = ('-date_emprunt',)
    readonly_fields = ('created_at', 'updated_at', 'date_emprunt')


@admin.register(Reservation)
class ReservationAdmin(ModelAdmin):
    list_display = ('id_membre', 'id_livre', 'date_reservation', 'statut')
    search_fields = ('id_membre__nom', 'id_livre__titre')
    list_filter = ('statut', 'date_reservation')
    ordering = ('-date_reservation',)
    readonly_fields = ('created_at', 'updated_at', 'date_reservation')


@admin.register(Sanction)
class SanctionAdmin(ModelAdmin):
    list_display = ('id_membre', 'type_sanction', 'date_sanction', 'statut')
    search_fields = ('id_membre__nom',)
    list_filter = ('type_sanction', 'statut', 'date_sanction')
    ordering = ('-date_sanction',)
    readonly_fields = ('created_at', 'updated_at', 'date_sanction')


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('id_membre', 'message', 'date_notif', 'lu')
    search_fields = ('id_membre__nom', 'message')
    list_filter = ('lu', 'date_notif')
    ordering = ('-date_notif',)
    readonly_fields = ('created_at', 'date_notif')


@admin.register(Avis)
class AvisAdmin(ModelAdmin):
    list_display = ('id_livre', 'id_membre', 'note', 'date_avis')
    search_fields = ('id_livre__titre', 'id_membre__nom')
    list_filter = ('note', 'date_avis')
    ordering = ('-date_avis',)
    readonly_fields = ('created_at', 'updated_at', 'date_avis')


@admin.register(Favori)
class FavoriAdmin(ModelAdmin):
    list_display = ('id_membre', 'id_livre')
    search_fields = ('id_membre__nom', 'id_livre__titre')
    readonly_fields = ()


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ('id_membre', 'date_envoi', 'statut')
    search_fields = ('id_membre__nom', 'contenu')
    list_filter = ('statut', 'date_envoi')
    ordering = ('-date_envoi',)
    readonly_fields = ('created_at', 'updated_at', 'date_envoi')
