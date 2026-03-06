from django import forms

class BookForm(forms.Form):
    titre = forms.CharField(label="Titre", max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    auteur = forms.CharField(label="Auteur", required=True, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    descriptions = forms.CharField(label="Descriptions", required=False, widget=forms.Textarea(attrs={"class":"border rounded w-full px-3 py-2", "rows":4}))
    isbn = forms.CharField(label="ISBN", required=True, max_length=50, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    editeur = forms.CharField(label="Editeur", required=False, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    langue = forms.CharField(label="Langue", required=False, max_length=50, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    annee_publication = forms.IntegerField(label="Annee publication", required=False, widget=forms.NumberInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    genre = forms.CharField(label="Genre", required=False, max_length=100, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    id_categorie = forms.ChoiceField(label="Categorie", required=True, choices=[], widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    image_url = forms.URLField(label="Image URL", required=False, widget=forms.URLInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    cover = forms.FileField(label="Couverture (fichier)", required=False)
    
    def __init__(self, *args, categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        if categories:
            self.fields['id_categorie'].choices = [('', '-- Selectionnez une categorie --')] + [
                (c.get('id_categorie') or c.get('id'), c.get('nom') or c.get('libelle') or f"Categorie #{c.get('id_categorie') or c.get('id')}")
                for c in categories
            ]

# Choix pour l'etat des exemplaires - Valeurs API: 'Disponible', 'Emprunte', 'Reserve', 'Abime'
ETAT_CHOICES = [
    ("Disponible", "Disponible"),
    ("Emprunte", "Emprunte"),
    ("Reserve", "Reserve"),
    ("Abime", "Abime"),
]

# Statut logique des exemplaires
STATUT_LOGIQUE_CHOICES = [
    ("Disponible", "Disponible"),
    ("Emprunte", "Emprunte"),
    ("Reserve", "Reserve"),
    ("Abime", "Abime"),
]

class ExemplaireForm(forms.Form):
    id_livre = forms.ChoiceField(label="Livre", required=True, choices=[], widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    code_barre = forms.CharField(label="Code barre", required=True, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2", "placeholder":"Code barre unique"}))
    code_exemplaire = forms.CharField(label="Code exemplaire", required=False, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2", "placeholder":"Code exemplaire (optionnel)"}))
    etat = forms.ChoiceField(label="Etat", required=True, choices=ETAT_CHOICES, widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    statut_logique = forms.ChoiceField(label="Statut logique", required=True, choices=STATUT_LOGIQUE_CHOICES, widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    date_acquisition = forms.DateField(label="Date d'acquisition", required=False, widget=forms.DateInput(attrs={"class":"border rounded w-full px-3 py-2", "type":"date"}))
    localisation = forms.CharField(label="Localisation", required=False, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    
    def __init__(self, *args, livres=None, **kwargs):
        super().__init__(*args, **kwargs)
        if livres:
            self.fields['id_livre'].choices = [('', '-- Selectionnez un livre --')] + [
                (b.get('id_livre') or b.get('id'), f"{b.get('titre', 'Sans titre')} - {b.get('auteur', 'Auteur inconnu')}")
                for b in livres
            ]

# Choix pour types de membres
TYPE_MEMBRE_CHOICES = [
    (1, "Etudiant"),
    (2, "Enseignant"),
    (3, "Personnel"),
    (4, "Externe"),
]

class MemberForm(forms.Form):
    """Formulaire de creation/modification de membre"""
    nom = forms.CharField(label="Nom", required=True, max_length=100, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    prenom = forms.CharField(label="Prenom", required=True, max_length=100, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    email = forms.EmailField(label="Email", required=True, widget=forms.EmailInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    password = forms.CharField(label="Mot de passe", required=True, widget=forms.PasswordInput(attrs={"class":"border rounded w-full px-3 py-2", "placeholder":"Mot de passe du membre"}))
    id_type_membre = forms.ChoiceField(label="Type de membre", required=True, choices=TYPE_MEMBRE_CHOICES, widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    numero_carte = forms.CharField(label="Numero de carte", required=True, max_length=50, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2", "placeholder":"Numero de carte unique"}))
    telephone = forms.CharField(label="Telephone", required=False, max_length=20, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    adresse = forms.CharField(label="Adresse", required=False, max_length=255, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))
    date_naissance = forms.DateField(label="Date de naissance", required=False, widget=forms.DateInput(attrs={"type":"date", "class":"border rounded w-full px-3 py-2"}))
    statut_compte = forms.ChoiceField(
        label="Statut du compte", 
        required=True,
        initial="Actif",
        choices=[("Actif", "Actif"), ("Inactif", "Inactif"), ("Suspendu", "Suspendu")],
        widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"})
    )
    login = forms.CharField(label="Login", required=False, max_length=50, widget=forms.TextInput(attrs={"class":"border rounded w-full px-3 py-2"}))

class EmpruntForm(forms.Form):
    """Formulaire de creation d'emprunt"""
    id_membre = forms.ChoiceField(
        label="Membre", 
        required=True, 
        choices=[],
        widget=forms.Select(attrs={"class":"w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"}),
    )
    id_exemplaire = forms.ChoiceField(
        label="Exemplaire", 
        required=True, 
        choices=[],
        widget=forms.Select(attrs={"class":"w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"}),
    )
    id_bibliotecaire = forms.IntegerField(
        label="Bibliothecaire", 
        required=True,
        widget=forms.HiddenInput(),
    )
    commentaire = forms.CharField(
        label="Commentaire", 
        required=False, 
        widget=forms.Textarea(attrs={"class":"w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500", "rows":3, "placeholder":"Notes optionnelles sur cet emprunt..."})
    )
    
    def __init__(self, *args, membres=None, exemplaires=None, livres=None, current_staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Liste des membres avec infos detaillees
        if membres:
            self.fields['id_membre'].choices = [('', '-- Selectionnez un membre --')] + [
                (m.get('id_membre') or m.get('id'), 
                 f"{m.get('nom', '')} {m.get('prenom', '')} - {m.get('numero_carte', '')} ({m.get('email', '')})")
                for m in sorted(membres, key=lambda x: x.get('nom', ''))
            ]
        
        # Creer un dict des livres pour afficher le titre
        livres_dict = {}
        if livres:
            livres_dict = {l.get('id_livre'): l.get('titre', 'Livre inconnu') for l in livres}
        
        # Liste des exemplaires disponibles avec titre du livre
        if exemplaires:
            exemplaires_disponibles = [
                ex for ex in exemplaires 
                if ex.get('statut_logique', '').lower() == 'disponible'
            ]
            self.fields['id_exemplaire'].choices = [('', '-- Selectionnez un exemplaire disponible --')] + [
                (ex.get('id_exemplaire') or ex.get('id'), 
                 f"{ex.get('code_barre', '')} - {livres_dict.get(ex.get('id_livre'), 'Livre #' + str(ex.get('id_livre', '?')))} ({ex.get('localisation', 'N/A')})")
                for ex in exemplaires_disponibles
            ]
        
        # Pre-remplir le bibliothecaire connecte
        self.current_staff_name = "Non identifie"
        if current_staff:
            self.fields['id_bibliotecaire'].initial = current_staff.get('id_bibliotecaire') or current_staff.get('id')
            self.current_staff_name = f"{current_staff.get('prenom', '')} {current_staff.get('nom', '')}"

class ReservationForm(forms.Form):
    """Formulaire de reservation (staff)"""
    id_livre = forms.ChoiceField(label="Livre", required=True, choices=[], widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    id_membre = forms.ChoiceField(label="Membre", required=True, choices=[], widget=forms.Select(attrs={"class":"border rounded w-full px-3 py-2"}))
    
    def __init__(self, *args, livres=None, membres=None, **kwargs):
        super().__init__(*args, **kwargs)
        if livres:
            self.fields['id_livre'].choices = [('', '-- Selectionnez un livre --')] + [
                (b.get('id_livre') or b.get('id'), f"{b.get('titre', 'Sans titre')} - {b.get('auteur', 'Auteur inconnu')}")
                for b in livres
            ]
        if membres:
            self.fields['id_membre'].choices = [('', '-- Selectionnez un membre --')] + [
                (m.get('id_membre') or m.get('id'), f"{m.get('nom', '')} {m.get('prenom', '')} ({m.get('email', '')})")
                for m in membres
            ]
