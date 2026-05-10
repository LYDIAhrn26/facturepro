from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db     = SQLAlchemy()
bcrypt = Bcrypt()


# ══════════════════════════════════════════════════════════════════════════════
# TABLE UTILISATEUR
# ══════════════════════════════════════════════════════════════════════════════
class Utilisateur(db.Model):
    __tablename__ = 'utilisateur'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prenom      = db.Column(db.String(100), nullable=False)
    nom         = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(150), unique=True, nullable=False)
    mot_de_passe     = db.Column(db.String(255), nullable=False)
    is_active        = db.Column(db.Boolean, default=False)
    token_activation = db.Column(db.String(100), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec l'entreprise
    entreprise  = db.relationship('Entreprise', backref='utilisateur',
                                  uselist=False, lazy=True)

    def set_password(self, password):
        self.mot_de_passe = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.mot_de_passe, password)

    def __repr__(self):
        return f'<Utilisateur {self.prenom} {self.nom}>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE ENTREPRISE
# ══════════════════════════════════════════════════════════════════════════════
class Entreprise(db.Model):
    __tablename__ = 'entreprise'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    nom             = db.Column(db.String(200), nullable=False)
    forme_juridique = db.Column(db.String(50))
    siret           = db.Column(db.String(20), nullable=False)
    siren           = db.Column(db.String(15))
    capital         = db.Column(db.String(50))
    activite        = db.Column(db.String(255))
    adresse         = db.Column(db.String(255))
    email           = db.Column(db.String(150))
    telephone       = db.Column(db.String(20))
    iban            = db.Column(db.String(50))
    bic             = db.Column(db.String(20))
    logo            = db.Column(db.String(255))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Entreprise {self.nom}>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class Client(db.Model):
    __tablename__ = 'client'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    nom             = db.Column(db.String(100), nullable=False)
    prenom          = db.Column(db.String(100))
    email           = db.Column(db.String(150))
    telephone       = db.Column(db.String(20))
    adresse         = db.Column(db.String(255))
    type_client     = db.Column(db.String(20), default='particulier')  # particulier / professionnel
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    devis    = db.relationship('Devis',    backref='client', lazy=True)
    factures = db.relationship('Facture',  backref='client', lazy=True)

    def nom_complet(self):
        return f"{self.prenom or ''} {self.nom}".strip()

    def __repr__(self):
        return f'<Client {self.nom_complet()}>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE DEVIS
# ══════════════════════════════════════════════════════════════════════════════
class Devis(db.Model):
    __tablename__ = 'devis'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    client_id       = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    numero_devis    = db.Column(db.String(20), unique=True, nullable=False)  # DEV-0001

    # Infos client (stockées directement si client non enregistré)
    client_nom      = db.Column(db.String(200))
    client_email    = db.Column(db.String(150))
    client_telephone= db.Column(db.String(20))
    client_adresse  = db.Column(db.String(255))

    # Prestation
    type_service    = db.Column(db.String(50))
    description     = db.Column(db.Text)
    adresse_presta  = db.Column(db.String(255))
    date_devis      = db.Column(db.Date, nullable=False)
    remarques       = db.Column(db.Text)

    # Montants
    montant_ht      = db.Column(db.Numeric(10, 2), default=0)
    tva             = db.Column(db.Numeric(5, 2), default=20)
    montant_tva     = db.Column(db.Numeric(10, 2), default=0)
    montant_ttc     = db.Column(db.Numeric(10, 2), default=0)

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneDevis', backref='devis', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Devis {self.numero_devis}>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE FACTURE
# ══════════════════════════════════════════════════════════════════════════════
class Facture(db.Model):
    __tablename__ = 'facture'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    client_id       = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    numero_facture  = db.Column(db.String(20), unique=True, nullable=False)  # FAC-0001

    # Infos client
    client_nom      = db.Column(db.String(200))
    client_email    = db.Column(db.String(150))
    client_telephone= db.Column(db.String(20))
    client_adresse  = db.Column(db.String(255))

    # Dates
    date_emission   = db.Column(db.Date, nullable=False)
    date_echeance   = db.Column(db.Date)

    # Paiement
    conditions_paiement = db.Column(db.String(50), default='30 jours')
    statut_paiement     = db.Column(db.String(20), default='EN_ATTENTE')  # EN_ATTENTE / PAYEE
    date_paiement       = db.Column(db.Date, nullable=True)

    # Montants
    montant_ht      = db.Column(db.Numeric(10, 2), default=0)
    tva             = db.Column(db.Numeric(5, 2), default=20)
    montant_tva     = db.Column(db.Numeric(10, 2), default=0)
    montant_ttc     = db.Column(db.Numeric(10, 2), default=0)

    # Remarques / RIB
    remarques       = db.Column(db.Text)

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec les lignes
    lignes = db.relationship('LigneFacture', backref='facture',
                              lazy=True, cascade='all, delete-orphan')

    def est_payee(self):
        return self.statut_paiement == 'PAYEE'

    def __repr__(self):
        return f'<Facture {self.numero_facture}>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE LIGNE FACTURE
# ══════════════════════════════════════════════════════════════════════════════
class LigneFacture(db.Model):
    __tablename__ = 'ligne_facture'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    facture_id      = db.Column(db.Integer, db.ForeignKey('facture.id'), nullable=False)
    description     = db.Column(db.Text)
    type_service    = db.Column(db.String(50))
    quantite        = db.Column(db.Integer, default=1)
    prix_unitaire_ht= db.Column(db.Numeric(10, 2), default=0)
    total_ht        = db.Column(db.Numeric(10, 2), default=0)

    def __repr__(self):
        return f'<LigneFacture {self.description}>'




# ══════════════════════════════════════════════════════════════════════════════
# TABLE LIGNE DEVIS
# ══════════════════════════════════════════════════════════════════════════════
class LigneDevis(db.Model):
    __tablename__ = 'ligne_devis'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    devis_id        = db.Column(db.Integer, db.ForeignKey('devis.id'), nullable=False)
    description     = db.Column(db.Text)
    unite           = db.Column(db.String(50), default='Ens.')
    quantite        = db.Column(db.Numeric(10, 2), default=1)
    prix_unitaire_ht= db.Column(db.Numeric(10, 2), default=0)
    total_ht        = db.Column(db.Numeric(10, 2), default=0)

    def __repr__(self):
        return f'<LigneDevis {self.description}>'

# ══════════════════════════════════════════════════════════════════════════════
# TABLE NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
class Notification(db.Model):
    __tablename__ = 'notification'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    message         = db.Column(db.Text, nullable=False)
    type_notif      = db.Column(db.String(20), default='info')  # info / success / warning
    statut_lecture  = db.Column(db.Boolean, default=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.message[:30]}>'


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def generate_numero_devis(utilisateur_id):
    """Génère le prochain numéro de devis unique : DEV-0001, DEV-0002..."""
    num = 1
    while True:
        candidat = f"DEV-{str(num).zfill(4)}"
        existe = Devis.query.filter_by(numero_devis=candidat).first()
        if not existe:
            return candidat
        num += 1

def generate_numero_facture(utilisateur_id):
    """Génère le prochain numéro de facture unique : FAC-0001, FAC-0002..."""
    num = 1
    while True:
        candidat = f"FAC-{str(num).zfill(4)}"
        existe = Facture.query.filter_by(numero_facture=candidat).first()
        if not existe:
            return candidat
        num += 1