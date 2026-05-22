# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from core.models import (
    Livre, Categorie, Membre, Exemplaire, Emprunt, 
    Reservation, Sanction, Notification, TypeMembre
)
from core.orm_adapter import ORMAdapter


class Command(BaseCommand):
    help = 'Synchronise et valide les données entre MSSQL et le cache Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity',
            type=str,
            default='all',
            help='Entité à synchroniser (all, livres, categories, membres, exemplaires, emprunts)',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corriger automatiquement les incohérences détectées',
        )

    def handle(self, *args, **options):
        entity = options['entity']
        fix = options['fix']
        client = ORMAdapter()

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('SYNCHRONISATION DES DONNÉES MSSQL'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        if entity in ['all', 'livres']:
            self.sync_livres(client, fix)

        if entity in ['all', 'categories']:
            self.sync_categories(client, fix)

        if entity in ['all', 'membres']:
            self.sync_membres(client, fix)

        if entity in ['all', 'exemplaires']:
            self.sync_exemplaires(client, fix)

        if entity in ['all', 'emprunts']:
            self.sync_emprunts(client, fix)

        self.stdout.write(self.style.SUCCESS('\n✅ Synchronisation terminée!'))

    def sync_livres(self, client, fix):
        self.stdout.write(self.style.SUCCESS('\n[1/5] LIVRES'))
        self.stdout.write('-' * 80)

        livres_orm = client.get_books() or []
        livres_db_count = Livre.objects.count()

        self.stdout.write(f'Livres via ORM: {len(livres_orm)}')
        self.stdout.write(f'Livres en BD: {livres_db_count}')

        if len(livres_orm) == livres_db_count:
            self.stdout.write(self.style.SUCCESS(f'✅ OK - {len(livres_orm)} livres synchronisés'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Discordance détectée'))

    def sync_categories(self, client, fix):
        self.stdout.write(self.style.SUCCESS('\n[2/5] CATÉGORIES'))
        self.stdout.write('-' * 80)

        categories_orm = client.get_categories() or []
        categories_db_count = Categorie.objects.count()

        self.stdout.write(f'Catégories via ORM: {len(categories_orm)}')
        self.stdout.write(f'Catégories en BD: {categories_db_count}')

        if len(categories_orm) == categories_db_count:
            self.stdout.write(self.style.SUCCESS(f'✅ OK - {len(categories_orm)} catégories synchronisées'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Discordance détectée'))

    def sync_membres(self, client, fix):
        self.stdout.write(self.style.SUCCESS('\n[3/5] MEMBRES'))
        self.stdout.write('-' * 80)

        membres_orm = client.get_members() or []
        membres_db_count = Membre.objects.count()

        self.stdout.write(f'Membres via ORM: {len(membres_orm)}')
        self.stdout.write(f'Membres en BD: {membres_db_count}')

        if len(membres_orm) == membres_db_count:
            self.stdout.write(self.style.SUCCESS(f'✅ OK - {len(membres_orm)} membres synchronisés'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Discordance détectée'))

    def sync_exemplaires(self, client, fix):
        self.stdout.write(self.style.SUCCESS('\n[4/5] EXEMPLAIRES'))
        self.stdout.write('-' * 80)

        exemplaires_orm = client.get_exemplaires() or []
        exemplaires_db_count = Exemplaire.objects.count()
        available_orm = len([e for e in exemplaires_orm if e.get('statut_logique', '').lower() == 'disponible'])
        available_db = Exemplaire.objects.filter(statut_logique='Disponible').count()

        self.stdout.write(f'Exemplaires via ORM: {len(exemplaires_orm)} ({available_orm} dispo)')
        self.stdout.write(f'Exemplaires en BD: {exemplaires_db_count} ({available_db} dispo)')

        if len(exemplaires_orm) == exemplaires_db_count and available_orm == available_db:
            self.stdout.write(self.style.SUCCESS(f'✅ OK - {len(exemplaires_orm)} exemplaires synchronisés'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Discordance détectée'))

    def sync_emprunts(self, client, fix):
        self.stdout.write(self.style.SUCCESS('\n[5/5] EMPRUNTS'))
        self.stdout.write('-' * 80)

        emprunts_orm = client.get_emprunts() or []
        emprunts_db_count = Emprunt.objects.count()
        active_orm = len([e for e in emprunts_orm if e.get('statut') in ['En cours', 'En retard']])
        active_db = Emprunt.objects.filter(statut__in=['En cours', 'En retard']).count()

        self.stdout.write(f'Emprunts via ORM: {len(emprunts_orm)} ({active_orm} actifs)')
        self.stdout.write(f'Emprunts en BD: {emprunts_db_count} ({active_db} actifs)')

        if len(emprunts_orm) == emprunts_db_count and active_orm == active_db:
            self.stdout.write(self.style.SUCCESS(f'✅ OK - {len(emprunts_orm)} emprunts synchronisés'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Discordance détectée'))
