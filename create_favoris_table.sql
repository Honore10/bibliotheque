-- Script pour créer la table favoris dans SQL Server
-- Exécutez ce script dans SQL Server Management Studio

USE bibliotheque_db;
GO

-- Vérifier si la table existe déjà
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'favoris')
BEGIN
    CREATE TABLE favoris (
        id_favori INT IDENTITY(1,1) PRIMARY KEY,
        id_membre INT NOT NULL,
        id_livre INT NOT NULL,
        created_at DATETIME DEFAULT GETDATE(),
        CONSTRAINT fk_favoris_membre FOREIGN KEY (id_membre) REFERENCES membres(id_membre),
        CONSTRAINT fk_favoris_livre FOREIGN KEY (id_livre) REFERENCES livres(id_livre),
        CONSTRAINT uq_favoris_membre_livre UNIQUE (id_membre, id_livre)
    );
    
    -- Créer des indexes pour améliorer les performances
    CREATE INDEX idx_favoris_membre ON favoris(id_membre);
    CREATE INDEX idx_favoris_livre ON favoris(id_livre);
    
    PRINT 'Table favoris créée avec succès.';
END
ELSE
BEGIN
    PRINT 'La table favoris existe déjà.';
END
GO