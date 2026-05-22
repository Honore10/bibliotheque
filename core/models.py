# -*- coding: utf-8 -*-
"""
Modèles Django pour la base MSSQL
Remplace les appels API par des requêtes locales ORM
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import EmailValidator, MinValueValidator
from datetime import datetime, timedelta
from types import SimpleNamespace


class TypeMembreManager(models.Manager):
    def get_by_natural_key(self, nom_type):
        return self.get(nom_type=nom_type)


class TypeMembre(models.Model):
    id_type_membre = models.AutoField(primary_key=True)
    nom_type = models.CharField(max_length=100, unique=True)
    duree_max_emprunt = models.IntegerField(validators=[MinValueValidator(1)])
    nb_max_emprunt = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TypeMembreManager()

    class Meta:
        managed = False  # Django crée les tables
        db_table = 'types_membre'
        verbose_name = 'Type de Membre'
        verbose_name_plural = 'Types de Membres'

    def __str__(self):
        return self.nom_type


class MembreManager(BaseUserManager):
    def create_user(self, login, email, mot_de_passe_hash, **extra_fields):
        if not login:
            raise ValueError('Login est requis')
        if not email:
            raise ValueError('Email est requis')
        
        user = self.model(login=login, email=email, mot_de_passe_hash=mot_de_passe_hash, **extra_fields)
        return user


class Membre(models.Model):
    STATUT_CHOICES = [
        ('Actif', 'Actif'),
        ('Suspendu', 'Suspendu'),
        ('Bloqué', 'Bloqué'),
    ]
    USER_TYPE_CHOICES = [
        ('member', 'Membre'),
        ('unified', 'Utilisateur Unifié'),
    ]

    id_membre = models.AutoField(primary_key=True)
    numero_carte = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    date_naissance = models.DateField()
    statut_compte = models.CharField(max_length=50, choices=STATUT_CHOICES, default='Actif')
    login = models.CharField(max_length=100, unique=True)
    mot_de_passe_hash = models.CharField(max_length=255)
    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, default='member')
    id_type_membre = models.ForeignKey(TypeMembre, on_delete=models.PROTECT, db_column='id_type_membre')
    date_inscription = models.DateField(auto_now_add=True)
    derniere_connexion = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MembreManager()
    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['email', 'nom', 'prenom']

    class Meta:
        managed = False
        db_table = 'membres'
        verbose_name = 'Membre'
        verbose_name_plural = 'Membres'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['login']),
            models.Index(fields=['numero_carte']),
            models.Index(fields=['statut_compte']),
        ]

    def __str__(self):
        return f'{self.prenom} {self.nom}'

    def get_full_name(self):
        return f'{self.prenom} {self.nom}'


class BibliothecaireManager(BaseUserManager):
    def create_user(self, login, email, mot_de_passe_hash, **extra_fields):
        if not login:
            raise ValueError('Login est requis')
        user = self.model(login=login, email=email, mot_de_passe_hash=mot_de_passe_hash, **extra_fields)
        return user


class Bibliothecaire(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('agent', 'Agent Bibliothécaire'),
    ]
    USER_TYPE_CHOICES = [
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]

    id_bibliotecaire = models.AutoField(primary_key=True)
    matricule = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    login = models.CharField(max_length=100, unique=True)
    mot_de_passe_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='agent')
    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, default='staff')
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BibliothecaireManager()
    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['email']

    class Meta:
        managed = False
        db_table = 'bibliothecaires'
        verbose_name = 'Bibliothécaire'
        verbose_name_plural = 'Bibliothécaires'
        indexes = [
            models.Index(fields=['login']),
            models.Index(fields=['role']),
            models.Index(fields=['actif']),
        ]

    def __str__(self):
        return f'{self.prenom} {self.nom} ({self.role})'

    def is_admin(self):
        return self.role == 'admin'


class Categorie(models.Model):
    id_categorie = models.AutoField(primary_key=True)
    nom_categorie = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'categories'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return self.nom_categorie


class Auteur(models.Model):
    id_auteur = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'auteurs'
        verbose_name = 'Auteur'
        verbose_name_plural = 'Auteurs'
        unique_together = ('nom', 'prenom')

    def __str__(self):
        return f'{self.prenom} {self.nom}'

    @property
    def nom_auteur(self):
        """Compatibilité template: nom complet de l'auteur attendu par certains templates."""
        return f"{self.prenom} {self.nom}"


class Livre(models.Model):
    id_livre = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=255)
    descriptions = models.TextField(blank=True, null=True)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    editeur = models.CharField(max_length=150, blank=True, null=True)
    langue = models.CharField(max_length=50, default='Français')
    annee_publication = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1)])
    id_categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, db_column='id_categorie')
    image_url = models.URLField(max_length=2048, blank=True, null=True)
    date_ajout_catalogue = models.DateField(auto_now_add=True)
    auteurs = models.ManyToManyField(Auteur, through='LivresAuteur', related_name='livres')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'livres'
        verbose_name = 'Livre'
        verbose_name_plural = 'Livres'
        indexes = [
            models.Index(fields=['titre']),
            models.Index(fields=['isbn']),
            models.Index(fields=['id_categorie']),
        ]

    def __str__(self):
        return self.titre

    @property
    def nb_disponible(self):
        return self.exemplaires.filter(statut_logique='Disponible').count()

    @property
    def nb_total_exemplaires(self):
        return self.exemplaires.count()

    @property
    def auteur(self):
        """Compatibilité template: retourne le premier auteur (objet) ou None.
        Les templates peuvent appeler `livre.auteur.nom_auteur` ou afficher `{{ livre.auteur }}`.
        """
        try:
            authors = list(self.auteurs.all())
        except Exception:
            return None
        return authors[0] if authors else None

    @property
    def categorie(self):
        """Alias vers `id_categorie` pour compatibilité template."""
        return self.id_categorie

    @property
    def categorie_nom(self):
        try:
            return self.id_categorie.nom_categorie
        except Exception:
            return ''

    @property
    def image_couverture(self):
        """Compatibilité template: retourne un objet avec `.url` si `image_url` est présent."""
        if self.image_url:
            return SimpleNamespace(url=self.image_url)
        return None


class LivresAuteur(models.Model):
    id_livre = models.ForeignKey(Livre, on_delete=models.CASCADE, db_column='id_livre')
    id_auteur = models.ForeignKey(Auteur, on_delete=models.CASCADE, db_column='id_auteur')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'livres_auteurs'
        unique_together = ('id_livre', 'id_auteur')
        verbose_name = 'Livre-Auteur'
        verbose_name_plural = 'Livres-Auteurs'


class Exemplaire(models.Model):
    ETAT_CHOICES = [
        ('Bon', 'Bon'),
        ('Abîmé', 'Abîmé'),
        ('Perdu', 'Perdu'),
    ]
    STATUT_LOGIQUE_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Emprunté', 'Emprunté'),
        ('Réservé', 'Réservé'),
        ('Indisponible', 'Indisponible'),
    ]

    id_exemplaire = models.AutoField(primary_key=True)
    code_barre = models.CharField(max_length=100, unique=True)
    etat = models.CharField(max_length=50, choices=ETAT_CHOICES, default='Bon')
    statut_logique = models.CharField(max_length=50, choices=STATUT_LOGIQUE_CHOICES, default='Disponible')
    date_acquisition = models.DateField(auto_now_add=True)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    id_livre = models.ForeignKey(Livre, on_delete=models.CASCADE, db_column='id_livre', related_name='exemplaires')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'exemplaires'
        verbose_name = 'Exemplaire'
        verbose_name_plural = 'Exemplaires'
        indexes = [
            models.Index(fields=['code_barre']),
            models.Index(fields=['statut_logique']),
            models.Index(fields=['id_livre']),
        ]

    def __str__(self):
        return f'{self.id_livre.titre} - {self.code_barre}'

    @property
    def code_exemplaire(self):
        """Compatibilité template: alias lisible pour code_barre"""
        return self.code_barre

    @property
    def livre(self):
        """Alias pour accéder facilement à l'objet Livre lié."""
        try:
            return self.id_livre
        except Exception:
            return None


class Emprunt(models.Model):
    STATUT_CHOICES = [
        ('En cours', 'En cours'),
        ('Retourné', 'Retourné'),
        ('En retard', 'En retard'),
    ]

    id_emprunt = models.AutoField(primary_key=True)
    date_emprunt = models.DateField(auto_now_add=True)
    date_retour_prevue = models.DateField()
    date_retour_effective = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='En cours')
    renouvellement_count = models.IntegerField(default=0)
    commentaire = models.TextField(blank=True, null=True)
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='emprunts')
    id_exemplaire = models.ForeignKey(Exemplaire, on_delete=models.CASCADE, db_column='id_exemplaire', related_name='emprunts')
    id_bibliotecaire = models.ForeignKey(Bibliothecaire, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_bibliotecaire')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'emprunts'
        verbose_name = 'Emprunt'
        verbose_name_plural = 'Emprunts'
        indexes = [
            models.Index(fields=['id_membre', 'statut']),
            models.Index(fields=['statut']),
            models.Index(fields=['date_retour_prevue']),
        ]

    def __str__(self):
        return f'Emprunt #{self.id_emprunt} - {self.id_membre}'

    @property
    def jours_restants(self):
        if self.date_retour_effective:
            return 0
        return (self.date_retour_prevue - datetime.now().date()).days

    @property
    def en_retard(self):
        return self.statut == 'En cours' and self.jours_restants < 0

    @property
    def livre(self):
        """Alias pour accéder directement au Livre emprunté (via l'exemplaire)."""
        try:
            if self.id_exemplaire:
                return self.id_exemplaire.id_livre
        except Exception:
            return None

    @property
    def exemplaire(self):
        try:
            return self.id_exemplaire
        except Exception:
            return None


class Reservation(models.Model):
    STATUT_CHOICES = [
        ('En attente', 'En attente'),
        ('Disponible', 'Disponible'),
        ('Complétée', 'Complétée'),
        ('Annulée', 'Annulée'),
    ]

    id_reservation = models.AutoField(primary_key=True)
    date_reservation = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='En attente')
    priorite = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='reservations')
    id_livre = models.ForeignKey(Livre, on_delete=models.CASCADE, db_column='id_livre', related_name='reservations')
    id_bibliotecaire = models.ForeignKey(Bibliothecaire, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_bibliotecaire')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'reservations'
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        indexes = [
            models.Index(fields=['id_livre', 'statut']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f'Réservation #{self.id_reservation} - {self.id_membre}'

    @property
    def livre(self):
        """Alias compatibilité templates: retourne l'objet Livre lié."""
        try:
            return self.id_livre
        except Exception:
            return None



class Sanction(models.Model):
    TYPE_CHOICES = [
        ('Retard', 'Retard'),
        ('Détérioration', 'Détérioration'),
        ('Perte', 'Perte'),
        ('Autre', 'Autre'),
    ]
    STATUT_CHOICES = [
        ('Active', 'Active'),
        ('Payée', 'Payée'),
        ('Annulée', 'Annulée'),
    ]

    id_sanction = models.AutoField(primary_key=True)
    type_sanction = models.CharField(max_length=100, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    date_sanction = models.DateField(auto_now_add=True)
    date_fin_suspension = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='Active')
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='sanctions')
    id_emprunt = models.ForeignKey(Emprunt, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_emprunt')
    id_bibliotecaire = models.ForeignKey(Bibliothecaire, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_bibliotecaire')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'sanctions'
        verbose_name = 'Sanction'
        verbose_name_plural = 'Sanctions'

    def __str__(self):
        return f'{self.type_sanction} - {self.id_membre}'


class Notification(models.Model):
    id_notification = models.AutoField(primary_key=True)
    message = models.TextField()
    date_notif = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['id_membre', 'lu']),
            models.Index(fields=['-date_notif']),
        ]

    def __str__(self):
        return f'Notification #{self.id_notification}'


class Avis(models.Model):
    id_avis = models.AutoField(primary_key=True)
    id_livre = models.ForeignKey(Livre, on_delete=models.CASCADE, db_column='id_livre', related_name='avis')
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='avis')
    note = models.IntegerField(validators=[MinValueValidator(1)])
    commentaire = models.TextField(blank=True, null=True)
    date_avis = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'avis'
        verbose_name = 'Avis'
        verbose_name_plural = 'Avis'
        unique_together = ('id_livre', 'id_membre')

    def __str__(self):
        return f'Avis {self.note}/5 - {self.id_livre}'


class Favori(models.Model):
    id_favori = models.AutoField(primary_key=True)
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='favoris')
    id_livre = models.ForeignKey(Livre, on_delete=models.CASCADE, db_column='id_livre', related_name='favoris_membres')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'favoris'
        unique_together = ('id_membre', 'id_livre')
        verbose_name = 'Favori'
        verbose_name_plural = 'Favoris'
        indexes = [
            models.Index(fields=['id_membre']),
            models.Index(fields=['id_livre']),
        ]

    def __str__(self):
        return f'Favori - {self.id_membre} : {self.id_livre}'


class Message(models.Model):
    STATUT_CHOICES = [
        ('En attente', 'En attente'),
        ('Répondu', 'Répondu'),
    ]

    id_message = models.AutoField(primary_key=True)
    id_membre = models.ForeignKey(Membre, on_delete=models.CASCADE, db_column='id_membre', related_name='messages_envoyes')
    id_bibliotecaire = models.ForeignKey(Bibliothecaire, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_bibliotecaire', related_name='messages_recus')
    contenu = models.TextField()
    reponse = models.TextField(blank=True, null=True)
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_reponse = models.DateTimeField(blank=True, null=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='En attente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f'Message #{self.id_message} - {self.id_membre}'
