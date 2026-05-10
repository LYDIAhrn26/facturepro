from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
from models import db, bcrypt, Utilisateur, Entreprise, Client, Devis, Facture, LigneFacture, LigneDevis, Notification
from models import generate_numero_devis, generate_numero_facture
from datetime import datetime, date
import os
import secrets
try:
    import pdfkit
    import shutil
    wkhtmltopdf_path = shutil.which('wkhtmltopdf') or r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False
    PDFKIT_CONFIG = None

app = Flask(__name__)
app.secret_key = 'gl_global_secret_key_2026'
import os
app.config['SESSION_COOKIE_SECURE'] = False

# ─── Config Yahoo SMTP ────────────────────────────────────────────────────────
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = 'harounelydia2000@gmail.com'
app.config['MAIL_PASSWORD']       = 'befhtevajlkkmtev'
app.config['MAIL_DEFAULT_SENDER'] = ('FacturePro', 'harounelydia2000@gmail.com')

mail = Mail(app)

# ─── Config MySQL WAMP ────────────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:@localhost:3306/gl_global')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt.init_app(app)

with app.app_context():
    db.create_all()

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_entreprise():
    if 'user_id' not in session:
        return {}
    user = Utilisateur.query.get(session['user_id'])
    if not user or not user.entreprise:
        return {}
    e = user.entreprise
    return {
        'nom':       e.nom,
        'forme':     e.forme_juridique or '',
        'siret':     e.siret or '',
        'siren':     e.siren or '',
        'capital':   e.capital or '',
        'activite':  e.activite or '',
        'adresse':   e.adresse or '',
        'email':     e.email or '',
        'telephone': e.telephone or '',
        'dirigeant': f"{user.prenom} {user.nom}".strip(),
        'iban':      e.iban or '',
        'bic':       e.bic or '',
        'logo':      e.logo or None,
    }

def get_user():
    if 'user_id' not in session:
        return {}
    user = Utilisateur.query.get(session['user_id'])
    if not user:
        return {}
    initiales = ''
    if user.prenom: initiales += user.prenom[0].upper()
    if user.nom:    initiales += user.nom[0].upper()
    return {
        'id':        user.id,
        'nom':       f"{user.prenom} {user.nom}".strip(),
        'email':     user.email,
        'initiales': initiales,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PAGE D'ACCUEIL PUBLIQUE
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/')
def home():
    return render_template('index.html')


# ══════════════════════════════════════════════════════════════════════════════
# INSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = {}

    if request.method == 'POST':
        nom_entreprise   = request.form.get('nom_entreprise', '').strip()
        forme_juridique  = request.form.get('forme_juridique', '').strip()
        siret            = request.form.get('siret', '').strip()
        siren            = request.form.get('siren', '').strip()
        capital          = request.form.get('capital', '').strip()
        activite         = request.form.get('activite', '').strip()
        adresse          = request.form.get('adresse', '').strip()
        code_postal      = request.form.get('code_postal', '').strip()
        ville            = request.form.get('ville', '').strip()
        email            = request.form.get('email', '').strip()
        telephone        = request.form.get('telephone', '').strip()
        nom_gerant       = request.form.get('nom_gerant', '').strip()
        prenom_gerant    = request.form.get('prenom_gerant', '').strip()
        iban             = request.form.get('iban', '').strip()
        bic              = request.form.get('bic', '').strip()
        password         = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()

        if not nom_entreprise: errors['nom_entreprise'] = "Le nom de l'entreprise est obligatoire."
        if not siret:          errors['siret'] = "Le SIRET est obligatoire."
        if not email:          errors['email'] = "L'email est obligatoire."
        if not nom_gerant:     errors['nom_gerant'] = "Le nom du gérant est obligatoire."
        if not password or len(password) < 6:
            errors['password'] = "Le mot de passe doit contenir au moins 6 caractères."
        if password != password_confirm:
            errors['password_confirm'] = "Les mots de passe ne correspondent pas."
        if not errors and Utilisateur.query.filter_by(email=email).first():
            errors['email'] = "Cet email est déjà utilisé."

        logo_path = None
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo and logo.filename and allowed_file(logo.filename):
                ext = logo.filename.rsplit('.', 1)[1].lower()
                logo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'logo_entreprise.' + ext))
                logo_path = 'uploads/logo_entreprise.' + ext

        if not errors:
            adresse_complete = adresse
            if code_postal or ville:
                adresse_complete = f"{adresse}, {code_postal} {ville}".strip(', ')

            # Générer un token unique
            token = secrets.token_urlsafe(32)

            # Créer le compte (inactif)
            user = Utilisateur(
                prenom=prenom_gerant, nom=nom_gerant,
                email=email, is_active=False, token_activation=token
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            entreprise = Entreprise(
                utilisateur_id=user.id, nom=nom_entreprise,
                forme_juridique=forme_juridique, siret=siret, siren=siren,
                capital=capital + ' €' if capital else '', activite=activite,
                adresse=adresse_complete, email=email, telephone=telephone,
                iban=iban, bic=bic, logo=logo_path,
            )
            db.session.add(entreprise)
            db.session.commit()

            # Envoyer l'email d'activation
            lien = url_for('activer_compte', token=token, _external=True)
            try:
                msg = Message(
                    subject='✅ Activez votre compte FacturePro',
                    recipients=[email]
                )
                msg.html = f'''
                <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
                  <div style="background:linear-gradient(135deg,#1e1b4b,#4f46e5);padding:28px 32px;text-align:center;">
                    <h1 style="color:#fff;font-size:24px;margin:0;">FacturePro</h1>
                    <p style="color:rgba(255,255,255,.75);margin:6px 0 0;font-size:13px;">Gestion de devis et factures</p>
                  </div>
                  <div style="padding:32px;">
                    <h2 style="color:#1e1b4b;font-size:20px;margin-bottom:12px;">Bonjour {prenom_gerant} {nom_gerant} 👋</h2>
                    <p style="color:#475569;font-size:14px;line-height:1.7;margin-bottom:24px;">
                      Merci de vous être inscrit sur <strong>FacturePro</strong> avec votre entreprise <strong>{nom_entreprise}</strong>.<br>
                      Pour activer votre compte et accéder à votre espace, cliquez sur le bouton ci-dessous :
                    </p>
                    <div style="text-align:center;margin:28px 0;">
                      <a href="{lien}" style="background-color:#6366f1;color:#ffffff !important;padding:16px 36px;border-radius:8px;text-decoration:none;font-size:16px;font-weight:700;display:inline-block;border:3px solid #4f46e5;font-family:Arial,sans-serif;">
                        ✅ Activer mon compte
                      </a>
                    </div>
                    <p style="color:#94a3b8;font-size:12px;text-align:center;">
                      Ce lien est valable 24h. Si vous n'avez pas créé de compte, ignorez cet email.
                    </p>
                  </div>
                  <div style="background:#f8fafc;padding:16px 32px;text-align:center;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;">
                    FacturePro — La facturation simplifiée pour tous les professionnels
                  </div>
                </div>
                '''
                print(f"📧 Envoi email vers : {email}")
                print(f"🔗 Lien activation : {lien}")
                mail.send(msg)
                print("✅ Email envoyé avec succès !")
                flash(f"Un email d'activation a été envoyé à {email}. Vérifiez votre boîte mail !", 'info')
            except Exception as e:
                print(f"❌ ERREUR EMAIL : {str(e)}")
                flash(f"Erreur envoi email : {str(e)}", 'error')

            return redirect(url_for('attente_activation', email=email, token=token))

    return render_template('register.html', errors=errors, form=request.form)


@app.route('/attente-activation')
def attente_activation():
    email = request.args.get('email', '')
    token = request.args.get('token', '')
    lien  = url_for('activer_compte', token=token, _external=True) if token else ''
    return render_template('attente_activation.html', email=email, lien=lien)


@app.route('/activer/<token>')
def activer_compte(token):
    user = Utilisateur.query.filter_by(token_activation=token).first()
    if not user:
        flash("Lien d'activation invalide ou expiré.", 'error')
        return redirect(url_for('login'))
    if user.is_active:
        flash("Compte déjà activé. Connectez-vous !", 'info')
        return redirect(url_for('login'))

    user.is_active        = True
    user.token_activation = None
    db.session.commit()

    flash(f"✅ Votre compte est activé ! Vous pouvez maintenant vous connecter.", 'success')
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════════════════════════
# CONNEXION / DECONNEXION
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        user = Utilisateur.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                error = "⚠️ Compte non activé. Vérifiez votre email et cliquez sur le lien d'activation."
            else:
                session['user_id'] = user.id
                return redirect(url_for('dashboard'))
        else:
            error = 'Email ou mot de passe incorrect.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════════════════════════
# PROFIL ENTREPRISE
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    user = Utilisateur.query.get(session['user_id'])
    e    = user.entreprise

    if request.method == 'POST':
        onglet = request.form.get('onglet', 'entreprise')

        # ── Onglet Entreprise ──────────────────────────────────────────────
        if onglet == 'entreprise' and e:
            e.nom             = request.form.get('nom_entreprise', e.nom).strip()
            e.forme_juridique = request.form.get('forme_juridique', e.forme_juridique)
            e.siret           = request.form.get('siret', e.siret).strip()
            e.siren           = request.form.get('siren', e.siren).strip()
            capital           = request.form.get('capital', '').strip()
            e.capital         = capital + ' €' if capital and '€' not in capital else capital
            e.activite        = request.form.get('activite', e.activite).strip()

            # Logo
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo and logo.filename and allowed_file(logo.filename):
                    ext = logo.filename.rsplit('.', 1)[1].lower()
                    logo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'logo_entreprise.' + ext))
                    e.logo = 'uploads/logo_entreprise.' + ext

            db.session.commit()
            flash('Informations entreprise mises à jour !', 'success')

        # ── Onglet Coordonnées ─────────────────────────────────────────────
        elif onglet == 'coordonnees':
            if e:
                e.adresse   = request.form.get('adresse', '').strip()
                e.email     = request.form.get('email', '').strip()
                e.telephone = request.form.get('telephone', '').strip()
            prenom = request.form.get('prenom_gerant', '').strip()
            nom    = request.form.get('nom_gerant', '').strip()
            if prenom: user.prenom = prenom
            if nom:    user.nom    = nom
            db.session.commit()
            flash('Coordonnées mises à jour !', 'success')

        # ── Onglet Bancaire ────────────────────────────────────────────────
        elif onglet == 'bancaire' and e:
            e.iban = request.form.get('iban', '').strip()
            e.bic  = request.form.get('bic', '').strip()
            db.session.commit()
            flash('Coordonnées bancaires mises à jour !', 'success')

        # ── Onglet Sécurité ────────────────────────────────────────────────
        elif onglet == 'securite':
            cur_pwd  = request.form.get('current_password', '').strip()
            new_pwd  = request.form.get('new_password', '').strip()
            conf_pwd = request.form.get('confirm_password', '').strip()
            if not cur_pwd or not new_pwd:
                flash('Veuillez remplir tous les champs.', 'error')
                return redirect(url_for('profil'))
            if not user.check_password(cur_pwd):
                flash('Mot de passe actuel incorrect.', 'error')
                return redirect(url_for('profil'))
            if new_pwd != conf_pwd:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'error')
                return redirect(url_for('profil'))
            if len(new_pwd) < 6:
                flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
                return redirect(url_for('profil'))
            user.set_password(new_pwd)
            db.session.commit()
            flash('Mot de passe mis à jour avec succès !', 'success')

        return redirect(url_for('profil'))

    return render_template('profil.html', entreprise=get_entreprise(), user=get_user())


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    from sqlalchemy import func
    from datetime import datetime, date
    import json

    nb_devis    = Devis.query.filter_by(utilisateur_id=user_id).count()
    nb_factures = Facture.query.filter_by(utilisateur_id=user_id).count()
    nb_clients  = Client.query.filter_by(utilisateur_id=user_id).count()
    nb_payees   = Facture.query.filter_by(utilisateur_id=user_id, statut_paiement='PAYEE').count()

    ca = db.session.query(func.sum(Facture.montant_ttc)).filter_by(
        utilisateur_id=user_id, statut_paiement='PAYEE'
    ).scalar() or 0

    # ── Données graphiques par mois (6 derniers mois) ──────────────────────
    today = date.today()
    mois_labels = []
    devis_par_mois    = []
    factures_par_mois = []
    ca_par_mois       = []

    for i in range(5, -1, -1):
        # Calculer le mois
        mois_num = today.month - i
        annee    = today.year
        while mois_num <= 0:
            mois_num += 12
            annee    -= 1

        import calendar
        dernier_jour = calendar.monthrange(annee, mois_num)[1]
        debut = date(annee, mois_num, 1)
        fin   = date(annee, mois_num, dernier_jour)

        # Label mois
        noms = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc']
        mois_labels.append(noms[mois_num - 1] + ' ' + str(annee)[2:])

        # Compter devis de ce mois
        nb_d = Devis.query.filter(
            Devis.utilisateur_id == user_id,
            Devis.date_devis >= debut,
            Devis.date_devis <= fin
        ).count()
        devis_par_mois.append(nb_d)

        # Compter factures de ce mois
        nb_f = Facture.query.filter(
            Facture.utilisateur_id == user_id,
            Facture.date_emission >= debut,
            Facture.date_emission <= fin
        ).count()
        factures_par_mois.append(nb_f)

        # CA de ce mois
        ca_m = db.session.query(func.sum(Facture.montant_ttc)).filter(
            Facture.utilisateur_id == user_id,
            Facture.statut_paiement == 'PAYEE',
            Facture.date_emission >= debut,
            Facture.date_emission <= fin
        ).scalar() or 0
        ca_par_mois.append(float(ca_m))

    derniers_devis     = Devis.query.filter_by(utilisateur_id=user_id).order_by(Devis.created_at.desc()).limit(4).all()
    dernieres_factures = Facture.query.filter_by(utilisateur_id=user_id).order_by(Facture.created_at.desc()).limit(4).all()
    notifications      = Notification.query.filter_by(utilisateur_id=user_id, statut_lecture=False).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
        entreprise=get_entreprise(), user=get_user(),
        nb_devis=nb_devis, nb_factures=nb_factures,
        nb_clients=nb_clients, nb_payees=nb_payees,
        nb_attente=nb_factures - nb_payees,
        ca=float(ca),
        derniers_devis=derniers_devis,
        dernieres_factures=dernieres_factures,
        notifications=notifications,
        mois_labels=json.dumps(mois_labels),
        devis_par_mois=json.dumps(devis_par_mois),
        factures_par_mois=json.dumps(factures_par_mois),
        ca_par_mois=json.dumps(ca_par_mois),
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEVIS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/devis')
@login_required
def liste_devis():
    devis = Devis.query.filter_by(utilisateur_id=session['user_id']).order_by(Devis.created_at.desc()).all()
    return render_template('devis/liste.html', entreprise=get_entreprise(), user=get_user(), devis=devis)

@app.route('/devis/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_devis():
    user_id = session['user_id']

    if request.method == 'POST':
        # ── Récupération des lignes ─────────────────────────────────────
        descs = request.form.getlist('ligne_desc[]')
        types = request.form.getlist('ligne_type[]')
        qtys  = request.form.getlist('ligne_qty[]')
        prix  = request.form.getlist('ligne_pu[]')
        tva   = float(request.form.get('tva', 20) or 20)

        # ── Calcul du montant HT depuis les lignes ─────────────────────
        montant_ht = 0
        lignes_valides = []
        for i in range(len(descs)):
            desc = descs[i].strip() if i < len(descs) else ''
            if not desc:
                continue
            qty = float(qtys[i]) if i < len(qtys) and qtys[i] else 1
            pu  = float(prix[i]) if i < len(prix) and prix[i] else 0
            unite = types[i] if i < len(types) else 'Ens.'
            total_ligne = round(qty * pu, 2)
            montant_ht += total_ligne
            lignes_valides.append({
                'desc':  desc,
                'unite': unite,
                'qty':   qty,
                'pu':    pu,
                'total': total_ligne,
            })

        montant_ht  = round(montant_ht, 2)
        montant_tva = round(montant_ht * tva / 100, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)

        # ── Date ───────────────────────────────────────────────────────
        try:
            date_devis = datetime.strptime(request.form.get('date_devis', ''), '%Y-%m-%d').date()
        except:
            date_devis = date.today()

        # ── Nom client ─────────────────────────────────────────────────
        client_nom = (
            request.form.get('client_nom', '') + ' ' +
            request.form.get('client_prenom', '')
        ).strip()

        # ── Création du devis ──────────────────────────────────────────
        devis = Devis(
            utilisateur_id   = user_id,
            numero_devis     = generate_numero_devis(user_id),
            client_nom       = client_nom,
            client_email     = request.form.get('client_email', '').strip(),
            client_telephone = request.form.get('client_tel', '').strip(),
            client_adresse   = request.form.get('client_adresse', '').strip(),
            type_service     = request.form.get('type_service', '').strip(),
            description      = request.form.get('reference', request.form.get('description', '')).strip(),
            adresse_presta   = request.form.get('adresse_presta', '').strip(),
            date_devis       = date_devis,
            remarques        = request.form.get('remarques', '').strip(),
            montant_ht       = montant_ht,
            tva              = tva,
            montant_tva      = montant_tva,
            montant_ttc      = montant_ttc,
        )
        db.session.add(devis)
        db.session.flush()  # pour avoir devis.id

        # ── Sauvegarder le client si nouveau ──────────────────────────────
        if client_nom:
            client_exist = Client.query.filter_by(
                utilisateur_id=user_id, nom=client_nom.split()[0] if client_nom else ''
            ).first()
            if not client_exist:
                nouveau_client = Client(
                    utilisateur_id=user_id,
                    nom=request.form.get('client_nom','').strip(),
                    prenom=request.form.get('client_prenom','').strip(),
                    email=request.form.get('client_email','').strip(),
                    telephone=request.form.get('client_tel','').strip(),
                    adresse=request.form.get('client_adresse','').strip(),
                    type_client='professionnel',
                )
                db.session.add(nouveau_client)

        # ── Sauvegarde des lignes dans LigneDevis ──────────────────────
        for l in lignes_valides:
            ligne = LigneDevis(
                devis_id         = devis.id,
                description      = l['desc'],
                unite            = l['unite'],
                quantite         = l['qty'],
                prix_unitaire_ht = l['pu'],
                total_ht         = l['total'],
            )
            db.session.add(ligne)

        # ── Notification ───────────────────────────────────────────────
        notif = Notification(
            utilisateur_id = user_id,
            message        = f"Nouveau devis {devis.numero_devis} créé — {client_nom} — {montant_ttc:.2f} €",
            type_notif     = 'info'
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Devis {devis.numero_devis} enregistré avec succès !", 'success')
        return redirect(url_for('liste_devis'))

    prochain_numero = generate_numero_devis(user_id)
    clients = Client.query.filter_by(utilisateur_id=user_id).all()
    return render_template('devis/nouveau.html',
        entreprise=get_entreprise(), user=get_user(),
        prochain_numero=prochain_numero, clients=clients)


@app.route('/devis/voir/<int:id>')
@login_required
def voir_devis(id):
    devis = Devis.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    return render_template('devis/voir.html',
        devis=devis,
        entreprise=get_entreprise(),
        user=get_user())

@app.route('/devis/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_devis(id):
    user_id = session['user_id']
    devis   = Devis.query.filter_by(id=id, utilisateur_id=user_id).first_or_404()

    if request.method == 'POST':
        descs = request.form.getlist('ligne_desc[]')
        types = request.form.getlist('ligne_type[]')
        qtys  = request.form.getlist('ligne_qty[]')
        prix  = request.form.getlist('ligne_pu[]')
        tva   = float(request.form.get('tva', 20) or 20)

        montant_ht = 0
        lignes_valides = []
        for i in range(len(descs)):
            desc = descs[i].strip() if i < len(descs) else ''
            if not desc:
                continue
            qty = float(qtys[i]) if i < len(qtys) and qtys[i] else 1
            pu  = float(prix[i]) if i < len(prix) and prix[i] else 0
            unite = types[i] if i < len(types) else 'Ens.'
            total_ligne = round(qty * pu, 2)
            montant_ht += total_ligne
            lignes_valides.append({
                'desc': desc, 'unite': unite,
                'qty': qty, 'pu': pu, 'total': total_ligne
            })

        montant_ht  = round(montant_ht, 2)
        montant_tva = round(montant_ht * tva / 100, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)

        try:
            date_devis = datetime.strptime(request.form.get('date_devis',''), '%Y-%m-%d').date()
        except:
            date_devis = devis.date_devis

        client_nom = (
            request.form.get('client_nom','') + ' ' +
            request.form.get('client_prenom','')
        ).strip()

        # Mise à jour du devis
        devis.client_nom       = client_nom
        devis.client_email     = request.form.get('client_email','').strip()
        devis.client_telephone = request.form.get('client_tel','').strip()
        devis.client_adresse   = request.form.get('client_adresse','').strip()
        devis.type_service     = request.form.get('type_service','').strip()
        devis.description      = request.form.get('reference', request.form.get('description','')).strip()
        devis.adresse_presta   = request.form.get('adresse_presta','').strip()
        devis.date_devis       = date_devis
        devis.remarques        = request.form.get('remarques','').strip()
        devis.montant_ht       = montant_ht
        devis.tva              = tva
        devis.montant_tva      = montant_tva
        devis.montant_ttc      = montant_ttc

        # Supprimer les anciennes lignes et recréer
        from models import LigneDevis
        LigneDevis.query.filter_by(devis_id=devis.id).delete()
        for l in lignes_valides:
            ligne = LigneDevis(
                devis_id=devis.id, description=l['desc'],
                unite=l['unite'], quantite=l['qty'],
                prix_unitaire_ht=l['pu'], total_ht=l['total']
            )
            db.session.add(ligne)

        db.session.commit()
        flash(f"Devis {devis.numero_devis} modifié avec succès !", 'success')
        return redirect(url_for('voir_devis', id=devis.id))

    return render_template('devis/modifier.html',
        devis=devis,
        entreprise=get_entreprise(),
        user=get_user())


@app.route('/devis/pdf/<int:id>')
@login_required
def pdf_devis(id):
    devis = Devis.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    entreprise = get_entreprise()
    html = render_template('devis/pdf_devis.html', devis=devis, entreprise=entreprise)
    try:
        # Générer le vrai PDF avec WeasyPrint
        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)
        from flask import Response
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={devis.numero_devis}.pdf'
            }
        )
    except Exception as e:
        # Fallback HTML si WeasyPrint échoue
        from flask import Response
        return Response(html, mimetype='text/html')

@app.route('/devis/envoyer/<int:id>')
@login_required
def envoyer_devis(id):
    devis = Devis.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    entreprise = get_entreprise()

    if not devis.client_email:
        flash("Impossible d'envoyer : l'email du client n'est pas renseigné.", 'error')
        return redirect(url_for('voir_devis', id=id))

    try:
        # Générer le PDF
        html = render_template('devis/pdf_devis.html', devis=devis, entreprise=entreprise)
        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)

        # Envoyer l'email avec PDF joint
        msg = Message(
            subject=f"Devis {devis.numero_devis} — {entreprise.get('nom','')}",
            recipients=[devis.client_email]
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
          <div style="background:linear-gradient(135deg,#1e1b4b,#4f46e5);padding:24px 28px;border-radius:10px 10px 0 0;">
            <h2 style="color:#fff;margin:0;font-size:20px;">Devis {devis.numero_devis}</h2>
            <p style="color:rgba(255,255,255,.7);margin:4px 0 0;font-size:13px;">{entreprise.get('nom','')}</p>
          </div>
          <div style="padding:28px;background:#fff;border:1px solid #e2e8f0;border-top:none;">
            <p style="color:#475569;font-size:14px;line-height:1.7;">Bonjour,</p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Veuillez trouver ci-joint votre devis <strong>{devis.numero_devis}</strong>
              d'un montant de <strong>{float(devis.montant_ttc):.2f} € TTC</strong>.
            </p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Pour l'accepter, veuillez imprimer le document, inscrire la mention
              <strong>"Bon pour accord"</strong>, le dater et le signer, puis nous le retourner.
            </p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Cordialement,<br>
              <strong>{entreprise.get('dirigeant','')}</strong><br>
              {entreprise.get('nom','')}
            </p>
          </div>
          <div style="background:#f8fafc;padding:12px 28px;text-align:center;font-size:11px;color:#94a3b8;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;">
            {entreprise.get('nom','')} — {entreprise.get('adresse','')}
          </div>
        </div>
        """
        msg.attach(
            f"{devis.numero_devis}.pdf",
            'application/pdf',
            pdf_bytes
        )
        mail.send(msg)
        flash(f"Devis {devis.numero_devis} envoyé à {devis.client_email} avec succès !", 'success')

    except Exception as e:
        flash(f"Erreur lors de l'envoi : {str(e)}", 'error')

    return redirect(url_for('voir_devis', id=id))

@app.route('/devis/supprimer/<int:id>')
@login_required
def supprimer_devis(id):
    devis = Devis.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    num    = devis.numero_devis
    client = devis.client_nom or '—'
    db.session.delete(devis)
    notif = Notification(
        utilisateur_id=session['user_id'],
        message=f"Devis {num} supprimé — Client : {client}",
        type_notif='warning'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Devis {num} supprimé.", 'success')
    return redirect(url_for('liste_devis'))

@app.route('/devis/convertir/<int:id>')
@login_required
def convertir_devis(id):
    devis = Devis.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    # Stocker les infos du devis en session pour pré-remplir la facture
    session['convert_from_devis'] = {
        'client_nom':       devis.client_nom,
        'client_email':     devis.client_email,
        'client_telephone': devis.client_telephone,
        'client_adresse':   devis.client_adresse,
        'montant_ht':       float(devis.montant_ht),
        'tva':              float(devis.tva),
        'montant_ttc':      float(devis.montant_ttc),
        'description':      devis.description,
        'type_service':     devis.type_service,
        'devis_ref':        devis.numero_devis,
    }
    flash(f"Données du devis {devis.numero_devis} reprises. Complétez la facture.", 'info')
    return redirect(url_for('nouvelle_facture'))


# ══════════════════════════════════════════════════════════════════════════════
# FACTURES
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/factures')
@login_required
def liste_factures():
    factures = Facture.query.filter_by(utilisateur_id=session['user_id']).order_by(Facture.created_at.desc()).all()
    return render_template('factures/liste.html', entreprise=get_entreprise(), user=get_user(), factures=factures)

@app.route('/factures/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_facture():
    user_id = session['user_id']

    if request.method == 'POST':
        descs = request.form.getlist('ligne_desc[]')
        types = request.form.getlist('ligne_type[]')
        qtys  = request.form.getlist('ligne_qty[]')
        prix  = request.form.getlist('ligne_pu[]')

        tva = float(request.form.get('tva', 20) or 20)
        montant_ht = 0
        for i in range(len(descs)):
            if descs[i].strip():
                qty = float(qtys[i]) if i < len(qtys) and qtys[i] else 1
                pu  = float(prix[i]) if i < len(prix) and prix[i] else 0
                montant_ht += qty * pu

        montant_tva = round(montant_ht * tva / 100, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)

        def parse_date(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return date.today()

        statut = request.form.get('statut_paiement', 'EN_ATTENTE')

        facture = Facture(
            utilisateur_id      = user_id,
            numero_facture      = generate_numero_facture(user_id),
            client_nom          = request.form.get('client_nom','').strip(),
            client_email        = request.form.get('client_email','').strip(),
            client_telephone    = request.form.get('client_tel','').strip(),
            client_adresse      = request.form.get('client_adresse','').strip(),
            date_emission       = parse_date(request.form.get('date_emission','')),
            date_echeance       = parse_date(request.form.get('date_echeance','')),
            conditions_paiement = request.form.get('cond_paiement','30 jours'),
            statut_paiement     = statut,
            date_paiement       = date.today() if statut == 'PAYEE' else None,
            montant_ht          = montant_ht,
            tva                 = tva,
            montant_tva         = montant_tva,
            montant_ttc         = montant_ttc,
            remarques           = request.form.get('remarques','').strip(),
        )
        db.session.add(facture)
        db.session.flush()

        for i in range(len(descs)):
            if descs[i].strip():
                qty = float(qtys[i]) if i < len(qtys) and qtys[i] else 1
                pu  = float(prix[i]) if i < len(prix) and prix[i] else 0
                ligne = LigneFacture(
                    facture_id=facture.id, description=descs[i].strip(),
                    type_service=types[i] if i < len(types) else '',
                    quantite=int(qty), prix_unitaire_ht=pu, total_ht=round(qty*pu,2),
                )
                db.session.add(ligne)

        notif = Notification(
            utilisateur_id=user_id,
            message=f"Nouvelle facture {facture.numero_facture} créée — {facture.client_nom} — {montant_ttc:.2f} €",
            type_notif='info'
        )
        db.session.add(notif)
        db.session.commit()

        # Vider session convert
        session.pop('convert_from_devis', None)

        flash(f"Facture {facture.numero_facture} enregistrée avec succès !", 'success')
        return redirect(url_for('liste_factures'))

    prochain_numero = generate_numero_facture(user_id)
    clients         = Client.query.filter_by(utilisateur_id=user_id).all()
    convert_data    = session.get('convert_from_devis', {})

    return render_template('factures/nouvelle.html',
        entreprise=get_entreprise(), user=get_user(),
        prochain_numero=prochain_numero, clients=clients,
        convert_data=convert_data)


@app.route('/factures/voir/<int:id>')
@login_required
def voir_facture(id):
    facture = Facture.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    return render_template('factures/voir.html',
        facture=facture, entreprise=get_entreprise(), user=get_user())

@app.route('/factures/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_facture(id):
    user_id = session['user_id']
    facture = Facture.query.filter_by(id=id, utilisateur_id=user_id).first_or_404()

    if request.method == 'POST':
        descs = request.form.getlist('ligne_desc[]')
        types = request.form.getlist('ligne_type[]')
        qtys  = request.form.getlist('ligne_qty[]')
        prix  = request.form.getlist('ligne_pu[]')
        tva   = float(request.form.get('tva', 20) or 20)

        montant_ht = 0
        lignes_valides = []
        for i in range(len(descs)):
            desc = descs[i].strip() if i < len(descs) else ''
            if not desc: continue
            qty = float(qtys[i]) if i < len(qtys) and qtys[i] else 1
            pu  = float(prix[i]) if i < len(prix) and prix[i] else 0
            unite = types[i] if i < len(types) else 'Ens.'
            total_ligne = round(qty * pu, 2)
            montant_ht += total_ligne
            lignes_valides.append({'desc': desc, 'unite': unite, 'qty': qty, 'pu': pu, 'total': total_ligne})

        montant_ht  = round(montant_ht, 2)
        montant_tva = round(montant_ht * tva / 100, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)

        def parse_date(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return date.today()

        facture.client_nom          = request.form.get('client_nom', '').strip()
        facture.client_email        = request.form.get('client_email', '').strip()
        facture.client_telephone    = request.form.get('client_tel', '').strip()
        facture.client_adresse      = request.form.get('client_adresse', '').strip()
        facture.date_emission       = parse_date(request.form.get('date_emission', ''))
        facture.date_echeance       = parse_date(request.form.get('date_echeance', ''))
        facture.conditions_paiement = request.form.get('cond_paiement', '30 jours')
        facture.statut_paiement     = request.form.get('statut_paiement', 'EN_ATTENTE')
        facture.remarques           = request.form.get('remarques', '').strip()
        facture.montant_ht          = montant_ht
        facture.tva                 = tva
        facture.montant_tva         = montant_tva
        facture.montant_ttc         = montant_ttc

        if facture.statut_paiement == 'PAYEE' and not facture.date_paiement:
            facture.date_paiement = date.today()

        # Supprimer anciennes lignes et recréer
        LigneFacture.query.filter_by(facture_id=facture.id).delete()
        for l in lignes_valides:
            ligne = LigneFacture(
                facture_id=facture.id, description=l['desc'],
                type_service=l['unite'], quantite=int(l['qty']),
                prix_unitaire_ht=l['pu'], total_ht=l['total']
            )
            db.session.add(ligne)

        db.session.commit()
        flash(f"Facture {facture.numero_facture} modifiée avec succès !", 'success')
        return redirect(url_for('voir_facture', id=facture.id))

    return render_template('factures/modifier.html',
        facture=facture, entreprise=get_entreprise(), user=get_user())

@app.route('/factures/pdf/<int:id>')
@login_required
def pdf_facture(id):
    facture = Facture.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    entreprise = get_entreprise()
    html = render_template('factures/pdf_facture.html', facture=facture, entreprise=entreprise)
    try:
        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)
        from flask import Response
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={facture.numero_facture}.pdf'
            }
        )
    except Exception as e:
        from flask import Response
        return Response(html, mimetype='text/html')

@app.route('/factures/envoyer/<int:id>')
@login_required
def envoyer_facture(id):
    facture = Facture.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    entreprise = get_entreprise()

    if not facture.client_email:
        flash("Impossible d'envoyer : l'email du client n'est pas renseigné.", 'error')
        return redirect(url_for('voir_facture', id=id))

    try:
        html = render_template('factures/pdf_facture.html', facture=facture, entreprise=entreprise)
        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)

        msg = Message(
            subject=f"Facture {facture.numero_facture} — {entreprise.get('nom','')}",
            recipients=[facture.client_email]
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
          <div style="background:linear-gradient(135deg,#1e1b4b,#4f46e5);padding:24px 28px;border-radius:10px 10px 0 0;">
            <h2 style="color:#fff;margin:0;font-size:20px;">Facture {facture.numero_facture}</h2>
            <p style="color:rgba(255,255,255,.7);margin:4px 0 0;font-size:13px;">{entreprise.get('nom','')}</p>
          </div>
          <div style="padding:28px;background:#fff;border:1px solid #e2e8f0;border-top:none;">
            <p style="color:#475569;font-size:14px;line-height:1.7;">Bonjour,</p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Veuillez trouver ci-joint votre facture <strong>{facture.numero_facture}</strong>
              d'un montant de <strong>{float(facture.montant_ttc):.2f} € TTC</strong>.
            </p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Conditions de paiement : <strong>{facture.conditions_paiement}</strong>
            </p>
            <p style="color:#475569;font-size:14px;line-height:1.7;">
              Cordialement,<br>
              <strong>{entreprise.get('dirigeant','')}</strong><br>
              {entreprise.get('nom','')}
            </p>
          </div>
          <div style="background:#f8fafc;padding:12px 28px;text-align:center;font-size:11px;color:#94a3b8;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;">
            {entreprise.get('nom','')} — {entreprise.get('adresse','')}
          </div>
        </div>
        """
        msg.attach(
            f"{facture.numero_facture}.pdf",
            'application/pdf',
            pdf_bytes
        )
        mail.send(msg)
        flash(f"Facture {facture.numero_facture} envoyée à {facture.client_email} avec succès !", 'success')

    except Exception as e:
        flash(f"Erreur lors de l'envoi : {str(e)}", 'error')

    return redirect(url_for('voir_facture', id=id))

@app.route('/factures/payer/<int:id>')
@login_required
def marquer_payee(id):
    facture = Facture.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    facture.statut_paiement = 'PAYEE'
    facture.date_paiement   = date.today()
    notif = Notification(
        utilisateur_id=session['user_id'],
        message=f"Facture {facture.numero_facture} marquée payée — {facture.client_nom} — {float(facture.montant_ttc):.2f} €",
        type_notif='success'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Facture {facture.numero_facture} marquée comme payée !", 'success')
    return redirect(url_for('liste_factures'))

@app.route('/factures/supprimer/<int:id>')
@login_required
def supprimer_facture(id):
    facture = Facture.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    num    = facture.numero_facture
    client = facture.client_nom or '—'
    montant = float(facture.montant_ttc)
    db.session.delete(facture)
    notif = Notification(
        utilisateur_id=session['user_id'],
        message=f"Facture {num} supprimée — Client : {client} — {montant:.2f} €",
        type_notif='warning'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Facture {num} supprimée.", 'success')
    return redirect(url_for('liste_factures'))


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/clients')
@login_required
def liste_clients():
    clients = Client.query.filter_by(utilisateur_id=session['user_id']).order_by(Client.created_at.desc()).all()
    return render_template('clients/liste.html', entreprise=get_entreprise(), user=get_user(), clients=clients)

@app.route('/clients/ajouter', methods=['POST'])
@login_required
def ajouter_client():
    client = Client(
        utilisateur_id=session['user_id'],
        nom=request.form.get('nom','').strip(),
        prenom=request.form.get('prenom','').strip(),
        email=request.form.get('email','').strip(),
        telephone=request.form.get('telephone','').strip(),
        adresse=request.form.get('adresse','').strip(),
        type_client=request.form.get('type_client','particulier'),
    )
    db.session.add(client)
    db.session.commit()
    flash(f"Client {client.nom_complet()} ajouté !", 'success')
    return redirect(url_for('liste_clients'))

@app.route('/clients/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_client(id):
    client = Client.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    client.nom         = request.form.get('nom','').strip()
    client.prenom      = request.form.get('prenom','').strip()
    client.email       = request.form.get('email','').strip()
    client.telephone   = request.form.get('telephone','').strip()
    client.adresse     = request.form.get('adresse','').strip()
    client.type_client = request.form.get('type_client','particulier')
    db.session.commit()
    flash(f"Client {client.nom_complet()} mis à jour !", 'success')
    return redirect(url_for('liste_clients'))

@app.route('/clients/supprimer/<int:id>')
@login_required
def supprimer_client(id):
    client = Client.query.filter_by(id=id, utilisateur_id=session['user_id']).first_or_404()
    nom = client.nom_complet()
    db.session.delete(client)
    db.session.commit()
    flash(f"Client {nom} supprimé.", 'success')
    return redirect(url_for('liste_clients'))



# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/notifications')
@login_required
def liste_notifications():
    user_id = session['user_id']
    notifications = Notification.query.filter_by(
        utilisateur_id=user_id
    ).order_by(Notification.created_at.desc()).all()

    # Marquer toutes comme lues
    Notification.query.filter_by(
        utilisateur_id=user_id, statut_lecture=False
    ).update({'statut_lecture': True})
    db.session.commit()

    return render_template('notifications.html',
        notifications=notifications,
        entreprise=get_entreprise(),
        user=get_user())

@app.route('/notifications/tout-lu')
@login_required
def marquer_tout_lu():
    Notification.query.filter_by(
        utilisateur_id=session['user_id'], statut_lecture=False
    ).update({'statut_lecture': True})
    db.session.commit()
    flash('Toutes les notifications ont été marquées comme lues.', 'success')
    return redirect(url_for('liste_notifications'))

# ══════════════════════════════════════════════════════════════════════════════
# LANCEMENT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
