# ============================================================
# COPE AESTHETIC CUSTOMS — FLASK BACKEND (app.py)
# ============================================================
# This is the main Flask application. It serves two things:
#   1. All HTML/CSS/JS files from the /static/ folder
#   2. All API endpoints under /api/ that the frontend calls
#
# The frontend (core.js) makes fetch() calls to these endpoints.
# Flask queries the PostgreSQL database and returns JSON.
#
# ENVIRONMENT VARIABLES (set in Railway):
#   DATABASE_URL  — PostgreSQL connection string (set automatically by Railway)
#   SECRET_KEY    — random string for JWT token signing
#
# HOW TO RUN LOCALLY:
#   pip install -r requirements.txt
#   export DATABASE_URL="postgresql://postgres:...@metro.proxy.rlwy.net:30189/railway"
#   export SECRET_KEY="any-random-string-for-local-dev"
#   python app.py
# ============================================================

import os
import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # Allow cross-origin requests (needed during development)

# Database connection — reads DATABASE_URL from environment variable
# Railway sets this automatically when you link a PostgreSQL service
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

db = SQLAlchemy(app)


# ============================================================
# DATABASE MODELS
# These match the tables defined in CustomFlow.sql exactly.
# ============================================================

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    name          = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(255), nullable=False, default='customer')  # owner | employee | customer
    phone         = db.Column(db.String(255))
    password_hash = db.Column(db.String(512))  # stored as bcrypt hash
    notify_email   = db.Column(db.Boolean, default=True)
    notify_sms     = db.Column(db.Boolean, default=False)
    is_active      = db.Column(db.Boolean, default=True)
    # customer_type: individual | group | influencer | nonprofit | organization
    # SQL: ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_type VARCHAR(50) DEFAULT 'individual';
    customer_type  = db.Column(db.String(50), default='individual')
    created_at     = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':            self.id,
            'email':         self.email,
            'name':          self.name,
            'role':          self.role,
            'phone':         self.phone,
            'notify_email':  self.notify_email,
            'notify_sms':    self.notify_sms,
            'is_active':     self.is_active if self.is_active is not None else True,
            'customer_type': self.customer_type or 'individual',
            'created_at':    self.created_at.isoformat() if self.created_at else None,
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pricing_tier      = db.Column(db.String(255))
    item_type         = db.Column(db.String(255))
    must_have_by      = db.Column(db.Date)
    is_rush           = db.Column(db.Boolean, default=False)
    rush_approved     = db.Column(db.Boolean, default=False)
    rush_fee          = db.Column(db.Numeric(8, 2), default=0)
    booking_fee_paid  = db.Column(db.Boolean, default=False)
    status            = db.Column(db.String(255), default='free_waitlist')
    customer_notes    = db.Column(db.Text)
    admin_notes       = db.Column(db.Text)
    inbound_tracking  = db.Column(db.String(255))
    outbound_tracking = db.Column(db.String(255))
    outbound_carrier  = db.Column(db.String(255))
    has_cleaning_fee  = db.Column(db.Boolean, default=False)
    created_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':                self.id,
            'user_id':           self.user_id,
            'pricing_tier':      self.pricing_tier,
            'item_type':         self.item_type,
            'must_have_by':      self.must_have_by.isoformat() if self.must_have_by else None,
            'is_rush':           self.is_rush,
            'rush_approved':     self.rush_approved,
            'rush_fee':          float(self.rush_fee) if self.rush_fee else 0,
            'booking_fee_paid':  self.booking_fee_paid,
            'status':            self.status,
            'customer_notes':    self.customer_notes,
            'admin_notes':       self.admin_notes,
            'inbound_tracking':  self.inbound_tracking,
            'outbound_tracking': self.outbound_tracking,
            'outbound_carrier':  self.outbound_carrier,
            'has_cleaning_fee':  self.has_cleaning_fee,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
            'updated_at':        self.updated_at.isoformat() if self.updated_at else None,
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    type            = db.Column(db.String(255), nullable=False)   # booking | custom | rush | cleaning | revision | addon
    method          = db.Column(db.String(255))                    # Zelle | Venmo | CashApp | PayPal | Other
    status          = db.Column(db.String(255), default='paid')    # paid | pending | refunded
    recorded_at     = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    external_txn_id = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id':              self.id,
            'order_id':        self.order_id,
            'amount':          float(self.amount),
            'type':            self.type,
            'method':          self.method,
            'status':          self.status,
            'recorded_at':     self.recorded_at.isoformat() if self.recorded_at else None,
            'external_txn_id': self.external_txn_id,
        }


class Mockup(db.Model):
    __tablename__ = 'mockups'
    id             = db.Column(db.Integer, primary_key=True)
    order_id       = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    image_url      = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    approved       = db.Column(db.Boolean, default=False)
    approval_at    = db.Column(db.DateTime)
    revision_limit = db.Column(db.Integer, default=3)

    def to_dict(self):
        return {
            'id':             self.id,
            'order_id':       self.order_id,
            'image_url':      self.image_url,
            'created_at':     self.created_at.isoformat() if self.created_at else None,
            'approved':       self.approved,
            'approval_at':    self.approval_at.isoformat() if self.approval_at else None,
            'revision_limit': self.revision_limit,
        }


class Revision(db.Model):
    __tablename__ = 'revisions'
    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    mockup_id       = db.Column(db.Integer, db.ForeignKey('mockups.id'))
    revision_number = db.Column(db.Integer, nullable=False)
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    charge_amount   = db.Column(db.Numeric(8, 2), default=0)
    # SQL: ALTER TABLE revisions ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT FALSE;
    completed       = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id':              self.id,
            'order_id':        self.order_id,
            'mockup_id':       self.mockup_id,
            'revision_number': self.revision_number,
            'notes':           self.notes,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
            'charge_amount':   float(self.charge_amount) if self.charge_amount else 0,
            'completed':       self.completed or False,
        }


class OrderImage(db.Model):
    __tablename__ = 'order_images'
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    url         = db.Column(db.Text, nullable=False)
    type        = db.Column(db.String(255), nullable=False)  # base_photo | reference | mockup
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'url':         self.url,
            'type':        self.type,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    from_status = db.Column(db.String(255))
    to_status   = db.Column(db.String(255), nullable=False)
    changed_by  = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    note        = db.Column(db.Text)

    def to_dict(self):
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'from_status': self.from_status,
            'to_status':   self.to_status,
            'changed_by':  self.changed_by,
            'changed_at':  self.changed_at.isoformat() if self.changed_at else None,
            'note':        self.note,
        }


class ConsultCall(db.Model):
    __tablename__ = 'consult_calls'
    id               = db.Column(db.Integer, primary_key=True)
    order_id         = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    scheduled_at     = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    notes            = db.Column(db.Text)
    completed_by     = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id':               self.id,
            'order_id':         self.order_id,
            'scheduled_at':     self.scheduled_at.isoformat() if self.scheduled_at else None,
            'duration_minutes': self.duration_minutes,
            'notes':            self.notes,
            'completed_by':     self.completed_by,
        }


class AddOn(db.Model):
    __tablename__ = 'add_ons'
    id       = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    name     = db.Column(db.String(255), nullable=False)
    price    = db.Column(db.Numeric(8, 2), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id':       self.id,
            'order_id': self.order_id,
            'name':     self.name,
            'price':    float(self.price),
            'quantity': self.quantity,
        }


class Invoice(db.Model):
    # SQL to add new columns if upgrading existing table:
    # ALTER TABLE invoices ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) DEFAULT 'invoice';
    # ALTER TABLE invoices ADD COLUMN IF NOT EXISTS doc_number VARCHAR(50);
    # ALTER TABLE invoices ADD COLUMN IF NOT EXISTS line_items TEXT;
    # ALTER TABLE invoices ADD COLUMN IF NOT EXISTS subtotal NUMERIC(10,2);
    # ALTER TABLE invoices ADD COLUMN IF NOT EXISTS notes TEXT;
    #
    # doc_type: 'estimate' | 'invoice' | 'receipt'
    # doc_number format: YYYYOrderID + E/I/R  e.g. 20261011E
    __tablename__ = 'invoices'
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    type        = db.Column(db.String(255))   # booking | custom | rush | cleaning | final | custom_addon
    label       = db.Column(db.String(255))
    amount      = db.Column(db.Numeric(10, 2))
    doc_type    = db.Column(db.String(20), default='invoice')  # estimate | invoice | receipt
    doc_number  = db.Column(db.String(50))   # e.g. 20261011E
    line_items  = db.Column(db.Text)          # JSON string of [{label, amount}]
    subtotal    = db.Column(db.Numeric(10, 2))
    notes       = db.Column(db.Text)
    status      = db.Column(db.String(255), default='draft')  # draft | sent
    file_url    = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sent_at     = db.Column(db.DateTime)

    def to_dict(self):
        import json as _json
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'type':        self.type,
            'label':       self.label,
            'amount':      float(self.amount) if self.amount else None,
            'doc_type':    self.doc_type,
            'doc_number':  self.doc_number,
            'line_items':  _json.loads(self.line_items) if self.line_items else [],
            'subtotal':    float(self.subtotal) if self.subtotal else None,
            'notes':       self.notes,
            'status':      self.status,
            'file_url':    self.file_url,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'sent_at':     self.sent_at.isoformat() if self.sent_at else None,
        }


class Setting(db.Model):
    __tablename__ = 'settings'
    key   = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text)


class Faq(db.Model):
    __tablename__ = 'faqs'
    id         = db.Column(db.Integer, primary_key=True)
    question   = db.Column(db.Text, nullable=False)
    answer     = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id':         self.id,
            'question':   self.question,
            'answer':     self.answer,
            'sort_order': self.sort_order,
        }


class PricingTier(db.Model):
    __tablename__ = 'pricing_tiers'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(255), nullable=False)
    price_from  = db.Column(db.Integer, default=0)
    price_label = db.Column(db.String(255))   # e.g. "$75+" or "Varies"
    description = db.Column(db.Text)
    sort_order  = db.Column(db.Integer, default=0)
    is_active   = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'price_from':  self.price_from,
            'price_label': self.price_label,
            'description': self.description,
            'sort_order':  self.sort_order,
            'is_active':   self.is_active if self.is_active is not None else True,
        }


# ============================================================
# AUTH HELPERS
# ============================================================

def generate_token(user_id, role):
    """Generate a JWT token for a logged-in user."""
    payload = {
        'user_id': user_id,
        'role':    role,
        'exp':     datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator — protects a route, requires a valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        request.user_id = payload['user_id']
        request.user_role = payload['role']
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator — protects a route, requires owner or employee role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        if payload['role'] not in ['owner', 'employee']:
            return jsonify({'error': 'Admin access required'}), 403
        request.user_id = payload['user_id']
        request.user_role = payload['role']
        return f(*args, **kwargs)
    return decorated


# ============================================================
# FRONTEND ROUTES
# Serve HTML pages from the /static/ folder
# ============================================================

@app.route('/')
def index():
    """Root URL — serve the landing page."""
    return send_from_directory('static', 'landing.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve any file from the static folder by name.
    e.g. /landing.html, /styles.css, /logo.png, /core.js
    This catches all non-API routes and tries to serve them as static files."""
    return send_from_directory('static', filename)


# ============================================================
# API: AUTH
# ============================================================

@app.route('/api/login', methods=['POST'])
def login():
    """
    POST /api/login
    Body: { email, password }
    Returns: { token, user }

    Called by: index.html (admin login) and customer-login.html
    The frontend stores the token in localStorage and sends it
    as Authorization: Bearer <token> on all subsequent API calls.
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email'].lower().strip()).first()
    if not user or not check_password_hash(user.password_hash or '', data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    if user.is_active is False:
        return jsonify({'error': 'This account has been deactivated. Please contact Buffy.'}), 403

    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': user.to_dict()})


@app.route('/api/register', methods=['POST'])
def register():
    """
    POST /api/register
    Body: { name, email, password, phone, notify_email, notify_sms }
    Returns: { token, user }

    Called by: customer-register.html after user reads and agrees to terms.
    Creates a new customer account.

    TODO: Trigger welcome email via SendGrid after creating the user.
    Email template is defined in core.js → WELCOME_EMAIL_TEMPLATE.
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Name, email, and password required'}), 400

    # Verify reCAPTCHA v3 token
    captcha_token = data.get('captcha_token', '')
    secret_key    = os.environ.get('RECAPTCHA_SECRET_KEY', '')
    if secret_key and captcha_token:
        import urllib.request, urllib.parse
        verify_url  = 'https://www.google.com/recaptcha/api/siteverify'
        verify_data = urllib.parse.urlencode({
            'secret':   secret_key,
            'response': captcha_token,
        }).encode()
        try:
            with urllib.request.urlopen(verify_url, verify_data, timeout=5) as resp:
                import json as _json
                result = _json.loads(resp.read().decode())
            # v3 returns a score 0.0-1.0; below 0.5 is likely a bot
            if not result.get('success') or result.get('score', 1.0) < 0.5:
                return jsonify({'error': 'Bot detected. Please try again.'}), 400
        except Exception:
            pass  # if Google is unreachable, allow through

    # Check if email already exists
    existing = User.query.filter_by(email=data['email'].lower().strip()).first()
    if existing:
        return jsonify({'error': 'An account with this email already exists'}), 409

    customer_type = data.get('customer_type', 'individual')
    SPECIAL_TYPES = {'group', 'influencer', 'nonprofit', 'organization'}

    user = User(
        email         = data['email'].lower().strip(),
        name          = data['name'].strip(),
        role          = 'customer',
        phone         = data.get('phone', ''),
        password_hash = generate_password_hash(data['password']),
        notify_email  = data.get('notify_email', True),
        notify_sms    = data.get('notify_sms', False),
        customer_type = customer_type,
    )
    db.session.add(user)
    db.session.commit()

    # Notify Buffy if a special customer type registered
    if customer_type in SPECIAL_TYPES:
        type_label = customer_type.replace('nonprofit', 'Non-Profit').capitalize()
        _notify_buffy_special_customer(user, type_label)

    # TODO: send_welcome_email(user.name, user.email)
    # See WELCOME_EMAIL_TEMPLATE in static/core.js for the email content

    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': user.to_dict()}), 201


def _notify_buffy_special_customer(user, type_label):
    """
    Internal helper — sends Buffy an email notification when a non-individual
    customer type registers (group, influencer, non-profit, organization).
    Requires SendGrid to be configured. Fails silently if not set up.
    """
    try:
        import os, smtplib
        buffy_email = 'CopeAestheticCustoms@gmail.com'
        subject     = f'🔔 New {type_label} Customer Registered — {user.name}'
        body = (
            f"Hi Buffy,\n\n"
            f"A new customer just signed up and selected a special account type:\n\n"
            f"  Name:  {user.name}\n"
            f"  Email: {user.email}\n"
            f"  Phone: {user.phone or 'Not provided'}\n"
            f"  Type:  {type_label}\n\n"
            f"You may want to reach out directly to discuss group rates, "
            f"collab details, or nonprofit pricing.\n\n"
            f"— CustomFlow"
        )
        # TODO: replace with SendGrid when API key is configured
        # sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
        # msg = Mail(from_email=buffy_email, to_emails=buffy_email,
        #            subject=subject, plain_text_content=body)
        # sg.client.mail.send.post(request_body=msg.get())
        #
        # For now: log to console so it's visible in Railway logs
        print(f"[NOTIFY BUFFY] {subject}\n{body}", flush=True)
    except Exception as e:
        print(f"[NOTIFY BUFFY] Failed to send notification: {e}", flush=True)


@app.route('/api/admin/preview-token', methods=['POST'])
@require_admin
def admin_preview_token():
    """
    POST /api/admin/preview-token
    Body: { user_id }
    Returns: { token } — a short-lived customer-scoped token so Buffy can
    preview any customer's portal without logging in as them.

    Called by: admin-order-detail.html "👁 Customer View" button.
    The frontend opens customer-order-detail.html?id=X&preview_token=TOKEN
    """
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    user = User.query.get_or_404(user_id)
    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': user.to_dict()})


# ============================================================
# API: ORDERS
# ============================================================

@app.route('/api/orders', methods=['GET'])
@require_auth
def get_orders():
    """
    GET /api/orders
    Returns orders based on who is asking:
      - Admin/owner/employee: returns ALL orders, each with customer_name injected
      - Customer: returns only THEIR orders

    Called by: admin-orders.html, admin-dashboard.html, customer-portal.html
    """
    if request.user_role in ['owner', 'employee']:
        orders = Order.query.order_by(Order.created_at.desc()).all()
        # Build a user lookup so we don't N+1 query
        user_ids = list({o.user_id for o in orders})
        users    = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
        result   = []
        for o in orders:
            d = o.to_dict()
            u = users.get(o.user_id)
            d['customer_name']  = u.name  if u else '—'
            d['customer_email'] = u.email if u else '—'
            result.append(d)
        return jsonify(result)
    else:
        orders = Order.query.filter_by(user_id=request.user_id).order_by(Order.created_at.desc()).all()
        return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    """
    GET /api/orders/<id>
    Returns full order detail including payments, mockups, revisions,
    status history, consult calls, add-ons, and images.

    Called by: admin-order-detail.html, customer-order-detail.html
    """
    order = Order.query.get_or_404(order_id)

    # Customers can only see their own orders
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403

    # Build full order response with all related data
    payments      = [p.to_dict() for p in Payment.query.filter_by(order_id=order_id).all()]
    mockups       = [m.to_dict() for m in Mockup.query.filter_by(order_id=order_id).all()]
    revisions     = [r.to_dict() for r in Revision.query.filter_by(order_id=order_id).order_by(Revision.revision_number).all()]
    order_images  = [i.to_dict() for i in OrderImage.query.filter_by(order_id=order_id).all()]
    status_history= [h.to_dict() for h in StatusHistory.query.filter_by(order_id=order_id).order_by(StatusHistory.changed_at).all()]
    consult_calls = [c.to_dict() for c in ConsultCall.query.filter_by(order_id=order_id).all()]
    add_ons       = [a.to_dict() for a in AddOn.query.filter_by(order_id=order_id).all()]
    invoices      = []
    try:
        invoices  = [i.to_dict() for i in Invoice.query.filter_by(order_id=order_id).all()]
    except Exception:
        pass  # invoices table may not exist yet

    # Get the customer info for this order
    customer = User.query.get(order.user_id)

    return jsonify({
        'order':          order.to_dict(),
        'customer':       customer.to_dict() if customer else None,
        'payments':       payments,
        'mockups':        mockups,
        'revisions':      revisions,
        'order_images':   order_images,
        'status_history': status_history,
        'consult_calls':  consult_calls,
        'add_ons':        add_ons,
        'invoices':       invoices,
    })


@app.route('/api/orders', methods=['POST'])
@require_auth
def create_order():
    """
    POST /api/orders
    Body: { item_type, pricing_tier, customer_notes, is_rush,
            must_have_by, wants_consult, has_cleaning_fee }
    Returns: { order }

    Called by: customer-order-form.html when customer submits a new order.
    New orders always start in 'free_waitlist' status per PRD Feature 2.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    order = Order(
        user_id         = request.user_id,
        item_type       = data.get('item_type'),
        pricing_tier    = data.get('pricing_tier'),
        customer_notes  = data.get('customer_notes', ''),
        is_rush         = data.get('is_rush', False),
        must_have_by    = data.get('must_have_by'),
        has_cleaning_fee= data.get('has_cleaning_fee', False),
        status          = 'free_waitlist',  # Always starts here per PRD
    )
    db.session.add(order)
    db.session.flush()  # Get the new order ID before committing

    # Log the initial status in status_history
    history = StatusHistory(
        order_id   = order.id,
        from_status= None,
        to_status  = 'free_waitlist',
        changed_by = request.user_id,
        note       = 'Order submitted by customer',
    )
    db.session.add(history)

    # If customer requested a consult call, create a placeholder
    if data.get('wants_consult'):
        consult = ConsultCall(
            order_id        = order.id,
            scheduled_at    = datetime.datetime.utcnow() + datetime.timedelta(days=7),
            duration_minutes= 30,
            notes           = 'Customer requested consult — please schedule',
        )
        db.session.add(consult)

    db.session.commit()
    return jsonify({'order': order.to_dict()}), 201


@app.route('/api/orders/<int:order_id>', methods=['PATCH'])
@require_auth
def update_order(order_id):
    """
    PATCH /api/orders/<id>
    Body: any subset of order fields to update
    Returns: { order }

    Called by: admin-order-detail.html for status changes, tracking,
               rush approval, notes, etc.
    Also called by customer-order-detail.html for inbound tracking.

    When status changes, a new StatusHistory row is created automatically.

    TODO: When status changes, send email to customer via SendGrid.
    See STATUS_EMAIL_TEMPLATES and buildStatusEmailHtml() in static/core.js.
    """
    order = Order.query.get_or_404(order_id)

    # Customers can only update their own orders and only certain fields
    if request.user_role == 'customer':
        if order.user_id != request.user_id:
            return jsonify({'error': 'Not authorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    old_status = order.status

    # Update allowed fields
    allowed_fields = [
        'status', 'pricing_tier', 'item_type', 'must_have_by',
        'is_rush', 'rush_approved', 'rush_fee', 'booking_fee_paid',
        'customer_notes', 'admin_notes', 'inbound_tracking',
        'outbound_tracking', 'outbound_carrier', 'has_cleaning_fee',
    ]
    for field in allowed_fields:
        if field in data:
            setattr(order, field, data[field])

    order.updated_at = datetime.datetime.utcnow()

    # If status changed, log it in status_history
    if 'status' in data and data['status'] != old_status:
        history = StatusHistory(
            order_id   = order_id,
            from_status= old_status,
            to_status  = data['status'],
            changed_by = request.user_id,
            note       = data.get('note', 'Status updated'),
        )
        db.session.add(history)

        # TODO: Send status change email to customer
        # customer = User.query.get(order.user_id)
        # template = STATUS_EMAIL_TEMPLATES[data['status']]  (defined in core.js)
        # send_status_email(customer.email, customer.name, order, template)

    db.session.commit()
    return jsonify({'order': order.to_dict()})


# ============================================================
# API: PAYMENTS
# ============================================================

@app.route('/api/payments', methods=['POST'])
@require_admin
def create_payment():
    """
    POST /api/payments
    Body: { order_id, amount, type, method, status, external_txn_id }
    Returns: { payment }

    Called by: admin-order-detail.html when Buffy logs a payment.
    After booking fee is logged, the frontend prompts to move order
    to paid_waitlist status.
    """
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('amount'):
        return jsonify({'error': 'order_id and amount required'}), 400

    payment = Payment(
        order_id       = data['order_id'],
        amount         = data['amount'],
        type           = data.get('type', 'custom'),
        method         = data.get('method', 'Other'),
        status         = data.get('status', 'paid'),
        external_txn_id= data.get('external_txn_id', ''),
    )
    db.session.add(payment)

    # If booking fee paid, update order flag
    if data.get('type') == 'booking' and data.get('status') == 'paid':
        order = Order.query.get(data['order_id'])
        if order:
            order.booking_fee_paid = True

    db.session.commit()
    return jsonify({'payment': payment.to_dict()}), 201


# ============================================================
# API: REVISIONS
# ============================================================

@app.route('/api/revisions', methods=['POST'])
@require_auth
def create_revision():
    """
    POST /api/revisions
    Body: { order_id, notes, mockup_id }
    Returns: { revision }

    Called by: admin-order-detail.html and customer-order-detail.html
    First 3 revisions are free (charge_amount = 0).
    Revision 4+ cost $20 each per PRD Feature 6.
    """
    data = request.get_json()
    if not data or not data.get('order_id'):
        return jsonify({'error': 'order_id required'}), 400

    # Count existing revisions for this order
    existing_count = Revision.query.filter_by(order_id=data['order_id']).count()
    revision_number = existing_count + 1
    charge_amount = 0 if revision_number <= 3 else 20.00  # $20 per extra revision

    revision = Revision(
        order_id       = data['order_id'],
        mockup_id      = data.get('mockup_id'),
        revision_number= revision_number,
        notes          = data.get('notes', ''),
        charge_amount  = charge_amount,
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify({'revision': revision.to_dict()}), 201


@app.route('/api/revisions/<int:revision_id>', methods=['PATCH'])
@require_admin
def update_revision(revision_id):
    """
    PATCH /api/revisions/<id>
    Body: { completed: true/false }
    Buffy marks a revision as completed (addressed).
    Called by: admin-order-detail.html revision list
    """
    revision = Revision.query.get_or_404(revision_id)
    data = request.get_json() or {}
    if 'completed' in data:
        revision.completed = data['completed']
    db.session.commit()
    return jsonify({'revision': revision.to_dict()})


@app.route('/api/revisions/<int:revision_id>', methods=['DELETE'])
@require_admin
def delete_revision(revision_id):
    """
    DELETE /api/revisions/<id>
    Buffy deletes a revision request.
    Called by: admin-order-detail.html revision list
    """
    revision = Revision.query.get_or_404(revision_id)
    db.session.delete(revision)
    db.session.commit()
    return jsonify({'deleted': revision_id})

@app.route('/api/orders/<int:order_id>/images', methods=['POST'])
@require_auth
def upload_order_image(order_id):
    """
    POST /api/orders/<id>/images
    Body: { url, type }
    type: 'moodboard' | 'concept_art' | 'mockup' | 'reference' | 'base_photo'
    Admins can upload any type. Customers can only upload 'reference' to their own orders.
    Called by: admin-order-detail.html, customer-order-detail.html, customer-order-form.html
    """
    data = request.get_json()
    if not data or not data.get('url') or not data.get('type'):
        return jsonify({'error': 'url and type required'}), 400

    order = Order.query.get_or_404(order_id)

    # Customers can only add reference photos to their own orders
    if request.user_role == 'customer':
        if order.user_id != request.user_id:
            return jsonify({'error': 'Not authorized'}), 403
        if data['type'] not in ('reference',):
            return jsonify({'error': 'Customers can only upload reference photos'}), 403

    image = OrderImage(
        order_id = order_id,
        url      = data['url'],
        type     = data['type'],
    )
    db.session.add(image)

    # If uploading a mockup, also create a mockup record
    if data['type'] == 'mockup':
        mockup = Mockup(
            order_id       = order_id,
            image_url      = data['url'],
            approved       = False,
            revision_limit = 3,
        )
        db.session.add(mockup)

    db.session.commit()
    return jsonify({'image': image.to_dict()}), 201


@app.route('/api/orders/<int:order_id>/images/<int:image_id>', methods=['DELETE'])
@require_admin
def delete_order_image(order_id, image_id):
    """DELETE /api/orders/<id>/images/<image_id> — remove an uploaded image."""
    image = OrderImage.query.filter_by(id=image_id, order_id=order_id).first_or_404()
    db.session.delete(image)
    db.session.commit()
    return jsonify({'deleted': image_id})


@app.route('/api/add_ons', methods=['POST'])
@require_admin
def create_addon():
    """
    POST /api/add_ons
    Body: { order_id, name, price, quantity }
    Returns: { add_on }

    Called by: admin-order-detail.html when Buffy adds an add-on service.
    """
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('name'):
        return jsonify({'error': 'order_id and name required'}), 400

    addon = AddOn(
        order_id = data['order_id'],
        name     = data['name'],
        price    = data.get('price', 0),
        quantity = data.get('quantity', 1),
    )
    db.session.add(addon)
    db.session.commit()
    return jsonify({'add_on': addon.to_dict()}), 201


# ============================================================
# API: CONSULT CALLS
# ============================================================

@app.route('/api/consult_calls', methods=['POST'])
@require_admin
def create_consult():
    """
    POST /api/consult_calls
    Body: { order_id, scheduled_at, duration_minutes, notes }
    Returns: { consult_call }

    Called by: admin-order-detail.html when Buffy schedules a consult.
    Priority order per PRD Feature 5: Rush > Date-specific > Standard.
    """
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('scheduled_at'):
        return jsonify({'error': 'order_id and scheduled_at required'}), 400

    consult = ConsultCall(
        order_id        = data['order_id'],
        scheduled_at    = datetime.datetime.fromisoformat(data['scheduled_at']),
        duration_minutes= data.get('duration_minutes', 30),
        notes           = data.get('notes', ''),
        completed_by    = request.user_id,
    )
    db.session.add(consult)
    db.session.commit()
    return jsonify({'consult_call': consult.to_dict()}), 201


# ============================================================
# API: INVOICES / ESTIMATES / RECEIPTS
# ============================================================

def _doc_number(order_id, created_at, doc_type):
    """Build document number: YYYYOrderID + E/I/R  e.g. 20261011E"""
    import json as _json
    year = (created_at or datetime.datetime.utcnow()).year
    suffix = {'estimate': 'E', 'invoice': 'I', 'receipt': 'R'}.get(doc_type, 'I')
    return f"{year}{order_id}{suffix}"


@app.route('/api/orders/<int:order_id>/invoices', methods=['GET'])
@require_auth
def get_invoices(order_id):
    """
    GET /api/orders/<id>/invoices
    Returns all documents (estimates, invoices, receipts) for an order.
    Customers only see sent docs. Admins see all.
    """
    try:
        if request.user_role in ['owner', 'employee']:
            docs = Invoice.query.filter_by(order_id=order_id).order_by(Invoice.uploaded_at.desc()).all()
        else:
            docs = Invoice.query.filter_by(order_id=order_id, status='sent').order_by(Invoice.uploaded_at.desc()).all()
        return jsonify([d.to_dict() for d in docs])
    except Exception:
        return jsonify([])


@app.route('/api/orders/<int:order_id>/invoices', methods=['POST'])
@require_admin
def create_invoice(order_id):
    """
    POST /api/orders/<id>/invoices
    Creates a new estimate, invoice, or receipt from fee line items.

    Body: {
      doc_type: 'estimate' | 'invoice' | 'receipt',
      line_items: [{ label: str, amount: float }],
      notes: str (optional)
    }

    Returns: { invoice } with doc_number assigned.
    Called by: admin-order-detail.html Generate buttons.
    """
    import json as _json
    data = request.get_json() or {}
    doc_type   = data.get('doc_type', 'invoice')
    line_items = data.get('line_items', [])
    notes      = data.get('notes', '')

    if not line_items:
        return jsonify({'error': 'No line items provided'}), 400

    subtotal = sum(float(li.get('amount', 0)) for li in line_items)
    now      = datetime.datetime.utcnow()

    inv = Invoice(
        order_id   = order_id,
        doc_type   = doc_type,
        doc_number = _doc_number(order_id, now, doc_type),
        line_items = _json.dumps(line_items),
        subtotal   = subtotal,
        amount     = subtotal,
        label      = doc_type.capitalize(),
        notes      = notes,
        status     = 'draft',
        uploaded_at= now,
    )
    db.session.add(inv)
    db.session.commit()
    return jsonify({'invoice': inv.to_dict()}), 201


@app.route('/api/invoices/<int:invoice_id>', methods=['PATCH'])
@require_admin
def update_invoice(invoice_id):
    """
    PATCH /api/invoices/<id>
    Update line items, notes, or file_url on an existing doc.
    """
    import json as _json
    data    = request.get_json() or {}
    invoice = Invoice.query.get_or_404(invoice_id)

    if 'line_items' in data:
        invoice.line_items = _json.dumps(data['line_items'])
        invoice.subtotal   = sum(float(li.get('amount', 0)) for li in data['line_items'])
        invoice.amount     = invoice.subtotal
    if 'notes'     in data: invoice.notes    = data['notes']
    if 'file_url'  in data: invoice.file_url = data['file_url']

    db.session.commit()
    return jsonify({'invoice': invoice.to_dict()})


@app.route('/api/invoices/<int:invoice_id>', methods=['DELETE'])
@require_admin
def delete_invoice(invoice_id):
    """DELETE /api/invoices/<id>  — removes the doc entirely."""
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    return jsonify({'deleted': invoice_id})


@app.route('/api/invoices/<int:invoice_id>/send', methods=['POST'])
@require_admin
def send_invoice(invoice_id):
    """
    POST /api/invoices/<id>/send
    Marks document as sent so it appears in the customer portal.

    Called by: admin-order-detail.html "Send to Customer" button.
    TODO: also email PDF via SendGrid.
    """
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status  = 'sent'
        invoice.sent_at = datetime.datetime.utcnow()
        db.session.commit()

        # TODO: Send email via SendGrid with PDF attachment
        # order    = Order.query.get(invoice.order_id)
        # customer = User.query.get(order.user_id)
        # send_via_sendgrid(...)

        return jsonify({'invoice': invoice.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# API: PRODUCTION QUEUE
# ============================================================

@app.route('/api/queue', methods=['GET'])
@require_admin
def get_queue():
    """
    GET /api/queue
    Returns production queue sorted by priority per PRD Feature 7:
      1. Approved rush orders (soonest must_have_by first)
      2. Date-specific orders (soonest must_have_by first)
      3. Standard FIFO (sorted by booking fee payment date)

    Called by: admin-queue.html, admin-dashboard.html
    """
    active_statuses  = ['production_queue', 'prep', 'painting']
    waiting_statuses = ['paid_waitlist']

    def queue_sort_key(order):
        """
        Returns a tuple used for sorting. Python sorts tuples left to right.
        Tier 1 (rush approved) = 1, Tier 2 (has deadline) = 2, Tier 3 (FIFO) = 3
        """
        if order.is_rush and order.rush_approved:
            tier = 1
            date = order.must_have_by or datetime.date.max
        elif order.must_have_by:
            tier = 2
            date = order.must_have_by
        else:
            tier = 3
            # FIFO — use booking fee payment date as tiebreaker
            booking = Payment.query.filter_by(
                order_id=order.id, type='booking', status='paid'
            ).first()
            date = booking.recorded_at.date() if booking else order.created_at.date()
        return (tier, date)

    active  = sorted(Order.query.filter(Order.status.in_(active_statuses)).all(),  key=queue_sort_key)
    waiting = sorted(Order.query.filter(Order.status.in_(waiting_statuses)).all(), key=queue_sort_key)

    # Inject customer names
    all_orders = active + waiting
    user_ids = list({o.user_id for o in all_orders})
    users    = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}

    def enrich(o):
        d = o.to_dict()
        u = users.get(o.user_id)
        d['customer_name']  = u.name  if u else '—'
        d['customer_email'] = u.email if u else '—'
        return d

    return jsonify({
        'active':  [enrich(o) for o in active],
        'waiting': [enrich(o) for o in waiting],
    })


# ============================================================
# API: DASHBOARD STATS
# ============================================================

@app.route('/api/dashboard', methods=['GET'])
@require_admin
def get_dashboard():
    """
    GET /api/dashboard
    Returns aggregated stats for the admin dashboard.

    Called by: admin-dashboard.html
    """
    total_orders  = Order.query.count()
    rush_pending  = Order.query.filter_by(is_rush=True, rush_approved=False).count()
    in_production = Order.query.filter(Order.status.in_(['production_queue', 'prep', 'painting'])).count()
    completed     = Order.query.filter(Order.status.in_(['completed', 'shipped', 'closed'])).count()

    # Orders by status for the donut chart
    from sqlalchemy import func
    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status).all()
    )

    # Orders by item type for the bar chart
    type_counts = dict(
        db.session.query(Order.item_type, func.count(Order.id))
        .group_by(Order.item_type).all()
    )

    # Recent orders
    recent = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    return jsonify({
        'stats': {
            'total_orders':  total_orders,
            'rush_pending':  rush_pending,
            'in_production': in_production,
            'completed':     completed,
        },
        'status_counts': status_counts,
        'type_counts':   type_counts,
        'recent_orders': [o.to_dict() for o in recent],
    })


# ============================================================
# API: REPORTS
# ============================================================

@app.route('/api/reports', methods=['GET'])
@require_admin
def get_reports():
    """
    GET /api/reports
    Returns revenue and order analytics for the reports page.

    Called by: admin-reports.html
    """
    from sqlalchemy import func

    # Total revenue from paid payments — include all statuses that represent money received
    total_revenue = db.session.query(func.sum(Payment.amount))\
        .filter(Payment.status.in_(['paid']))\
        .scalar() or 0

    # Revenue by payment type — filter out None keys
    revenue_by_type = {
        k: float(v) for k, v in
        db.session.query(Payment.type, func.sum(Payment.amount))
        .filter(Payment.status.in_(['paid'])).group_by(Payment.type).all()
        if k is not None
    }

    # Orders by pricing tier — normalize to lowercase to avoid duplicate bars
    from sqlalchemy import func as sqlfunc
    tier_raw = db.session.query(
        func.lower(Order.pricing_tier), func.count(Order.id)
    ).filter(Order.pricing_tier.isnot(None)).group_by(func.lower(Order.pricing_tier)).all()
    tier_counts = {k.capitalize(): v for k, v in tier_raw if k}

    # Top customers by total spend
    top_customers_raw = db.session.query(
        Order.user_id,
        func.sum(Payment.amount).label('total')
    ).join(Payment, Payment.order_id == Order.id)\
     .filter(Payment.status == 'paid')\
     .group_by(Order.user_id)\
     .order_by(func.sum(Payment.amount).desc())\
     .limit(10).all()

    top_customers = []
    for user_id, total in top_customers_raw:
        user = User.query.get(user_id)
        order_count = Order.query.filter_by(user_id=user_id).count()
        if user:
            top_customers.append({
                'user':        user.to_dict(),
                'total_paid':  float(total or 0),
                'order_count': order_count,
            })

    return jsonify({
        'total_revenue':   float(total_revenue),
        'revenue_by_type': {k: float(v) for k, v in revenue_by_type.items()},
        'tier_counts':     tier_counts,
        'top_customers':   top_customers,
    })


# ============================================================
# API: USERS
# ============================================================

@app.route('/api/users', methods=['GET'])
@require_admin
def get_users():
    """
    GET /api/users
    Returns all users — both customers and admins.
    Supports ?role=customer or ?role=admin filter.
    Called by: admin-settings.html → User Management section
    """
    role_filter = request.args.get('role')
    if role_filter == 'customer':
        users = User.query.filter_by(role='customer').order_by(User.created_at.desc()).all()
    elif role_filter == 'admin':
        users = User.query.filter(User.role.in_(['owner', 'employee'])).order_by(User.created_at.desc()).all()
    else:
        users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


@app.route('/api/users/<int:user_id>', methods=['GET'])
@require_admin
def get_user(user_id):
    """GET /api/users/<id> — get a single user's full profile."""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['PATCH'])
@require_admin
def update_user(user_id):
    """
    PATCH /api/users/<id>
    Body: { name, email, phone, role, is_active }
    Buffy can edit any user's details, role, or active status.
    Called by: admin-settings.html → User Management
    """
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    # Prevent Buffy from accidentally deactivating herself
    if str(user_id) == str(request.user_id) and 'is_active' in data and not data['is_active']:
        return jsonify({'error': 'You cannot deactivate your own account'}), 400

    if 'name'      in data: user.name      = data['name'].strip()
    if 'email'     in data:
        # Check email not taken by someone else
        existing = User.query.filter_by(email=data['email'].lower().strip()).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Email already in use'}), 409
        user.email = data['email'].lower().strip()
    if 'phone'     in data: user.phone     = data['phone']
    if 'role'      in data: user.role      = data['role']
    if 'is_active' in data: user.is_active = data['is_active']
    if 'customer_type' in data: user.customer_type = data['customer_type']

    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """
    DELETE /api/users/<id>
    Permanently deletes a user account.
    Cannot delete yourself.
    Called by: admin-settings.html → User Management
    """
    if str(user_id) == str(request.user_id):
        return jsonify({'error': 'You cannot delete your own account'}), 400
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'deleted': user_id})


@app.route('/api/users/me', methods=['GET'])
@require_auth
def get_me():
    """
    GET /api/users/me
    Returns the currently logged-in user's profile.

    Called by: customer-settings.html to pre-fill the profile form
    """
    user = User.query.get_or_404(request.user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/me', methods=['PATCH'])
@require_auth
def update_me():
    """
    PATCH /api/users/me
    Body: { name, phone, notify_email, notify_sms, customer_type }
    Returns: { user }

    Called by: customer-settings.html when customer saves profile changes
    """
    data = request.get_json()
    user = User.query.get_or_404(request.user_id)
    SPECIAL_TYPES = {'group', 'influencer', 'nonprofit', 'organization'}

    old_type = user.customer_type or 'individual'
    if 'name'          in data: user.name         = data['name']
    if 'phone'         in data: user.phone        = data['phone']
    if 'notify_email'  in data: user.notify_email = data['notify_email']
    if 'notify_sms'    in data: user.notify_sms   = data['notify_sms']
    if 'customer_type' in data:
        new_type = data['customer_type']
        user.customer_type = new_type
        # Notify Buffy if they switched TO a special type (and weren't already that type)
        if new_type in SPECIAL_TYPES and old_type != new_type:
            type_label = new_type.replace('nonprofit', 'Non-Profit').capitalize()
            _notify_buffy_special_customer(user, f"{type_label} (updated profile)")
    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    POST /api/change-password
    Body: { current_password, new_password }
    Returns: { message }

    Called by: customer-settings.html
    """
    data = request.get_json()
    user = User.query.get_or_404(request.user_id)
    if not check_password_hash(user.password_hash or '', data.get('current_password', '')):
        return jsonify({'error': 'Current password is incorrect'}), 400
    if len(data.get('new_password', '')) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    user.password_hash = generate_password_hash(data['new_password'])
    db.session.commit()
    return jsonify({'message': 'Password updated successfully'})


# ============================================================
# API: SETTINGS
# ============================================================

@app.route('/api/settings/booking', methods=['GET'])
def get_booking_settings():
    """
    GET /api/settings/booking
    Returns booking availability settings shown on landing page and terms page.
    No auth required — this is public info.

    Called by: landing.html, customer-terms.html via getBookingStatus() in core.js
    """
    try:
        status      = Setting.query.get('booking_status')
        until       = Setting.query.get('booked_until')
        message     = Setting.query.get('booking_message')
        prod_start  = Setting.query.get('prod_start')

        return jsonify({
            'status':      status.value      if status      else 'waitlist',
            'until':       until.value       if until       else '2026-05-18',
            'message':     message.value     if message     else 'Currently booked through May 18, 2026',
            'prod_start':  prod_start.value  if prod_start  else 'May 18, 2026',
        })
    except Exception:
        # settings table may not exist yet — return defaults
        return jsonify({
            'status':     'waitlist',
            'until':      '2026-05-18',
            'message':    'Currently booked through May 18, 2026',
            'prod_start': 'May 18, 2026',
        })


@app.route('/api/settings/booking', methods=['PATCH'])
@require_admin
def update_booking_settings():
    """
    PATCH /api/settings/booking
    Body: { status, until, message, prod_start }
    Returns: { message }

    Called by: admin-settings.html → Booking & Availability section
    """
    data = request.get_json()
    try:
        for key in ['booking_status', 'booked_until', 'booking_message', 'prod_start']:
            field = key.replace('booking_', '')
            val = data.get(field) or data.get(key)
            if val is not None:
                setting = Setting.query.get(key)
                if setting:
                    setting.value = val
                else:
                    db.session.add(Setting(key=key, value=val))
        db.session.commit()
        return jsonify({'message': 'Booking settings updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/faqs', methods=['GET'])
def get_faqs():
    """
    GET /api/faqs
    Returns all FAQs from the database sorted by sort_order.
    No auth required — shown on terms page and customer portal.
    """
    try:
        faqs = Faq.query.order_by(Faq.sort_order, Faq.id).all()
        return jsonify([{
            'id':         f.id,
            'q':          f.question,
            'a':          f.answer,
            'question':   f.question,
            'answer':     f.answer,
            'sort_order': f.sort_order,
        } for f in faqs])
    except Exception as e:
        return jsonify([])


@app.route('/api/faqs', methods=['POST'])
@require_admin
def create_faq():
    """
    POST /api/faqs
    Body: { question, answer, sort_order }
    Creates a new FAQ entry in the database.
    Called by: admin-settings.html FAQ management
    """
    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({'error': 'question required'}), 400
    faq = Faq(
        question   = data['question'].strip(),
        answer     = data.get('answer', '').strip(),
        sort_order = data.get('sort_order', 0),
    )
    db.session.add(faq)
    db.session.commit()
    return jsonify({
        'id':         faq.id,
        'q':          faq.question,
        'a':          faq.answer,
        'question':   faq.question,
        'answer':     faq.answer,
        'sort_order': faq.sort_order,
    }), 201


@app.route('/api/faqs/<int:faq_id>', methods=['PATCH'])
@require_admin
def update_faq(faq_id):
    """
    PATCH /api/faqs/<id>
    Updates an existing FAQ entry.
    """
    faq = Faq.query.get_or_404(faq_id)
    data = request.get_json()
    if 'question' in data: faq.question   = data['question'].strip()
    if 'answer'   in data: faq.answer     = data['answer'].strip()
    if 'sort_order' in data: faq.sort_order = data['sort_order']
    db.session.commit()
    return jsonify({'id': faq.id, 'q': faq.question, 'a': faq.answer, 'sort_order': faq.sort_order})


@app.route('/api/faqs/<int:faq_id>', methods=['DELETE'])
@require_admin
def delete_faq(faq_id):
    """
    DELETE /api/faqs/<id>
    Deletes a FAQ entry.
    """
    faq = Faq.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify({'deleted': faq_id})


# ============================================================
# API: PRICING TIERS
# ============================================================

@app.route('/api/pricing_tiers', methods=['GET'])
def get_pricing_tiers():
    """GET /api/pricing_tiers — returns all active pricing tiers sorted by sort_order."""
    try:
        tiers = PricingTier.query.filter_by(is_active=True).order_by(PricingTier.sort_order, PricingTier.id).all()
        return jsonify([t.to_dict() for t in tiers])
    except Exception:
        return jsonify([])


@app.route('/api/pricing_tiers/all', methods=['GET'])
@require_admin
def get_all_pricing_tiers():
    """GET /api/pricing_tiers/all — returns ALL tiers including inactive (admin only)."""
    try:
        tiers = PricingTier.query.order_by(PricingTier.sort_order, PricingTier.id).all()
        return jsonify([t.to_dict() for t in tiers])
    except Exception:
        return jsonify([])


@app.route('/api/pricing_tiers', methods=['POST'])
@require_admin
def create_pricing_tier():
    """POST /api/pricing_tiers — create a new pricing tier."""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name required'}), 400
    tier = PricingTier(
        name        = data['name'].strip(),
        price_from  = data.get('price_from', 0),
        price_label = data.get('price_label', ''),
        description = data.get('description', ''),
        sort_order  = data.get('sort_order', 0),
        is_active   = data.get('is_active', True),
    )
    db.session.add(tier)
    db.session.commit()
    return jsonify(tier.to_dict()), 201


@app.route('/api/pricing_tiers/<int:tier_id>', methods=['PATCH'])
@require_admin
def update_pricing_tier(tier_id):
    """PATCH /api/pricing_tiers/<id> — update a pricing tier."""
    tier = PricingTier.query.get_or_404(tier_id)
    data = request.get_json()
    if 'name'        in data: tier.name        = data['name'].strip()
    if 'price_from'  in data: tier.price_from  = data['price_from']
    if 'price_label' in data: tier.price_label = data['price_label']
    if 'description' in data: tier.description = data['description']
    if 'sort_order'  in data: tier.sort_order  = data['sort_order']
    if 'is_active'   in data: tier.is_active   = data['is_active']
    db.session.commit()
    return jsonify(tier.to_dict())


@app.route('/api/pricing_tiers/<int:tier_id>', methods=['DELETE'])
@require_admin
def delete_pricing_tier(tier_id):
    """DELETE /api/pricing_tiers/<id> — delete a pricing tier."""
    tier = PricingTier.query.get_or_404(tier_id)
    db.session.delete(tier)
    db.session.commit()
    return jsonify({'deleted': tier_id})


# ============================================================
# API: MOCKUP APPROVAL
# ============================================================

@app.route('/api/mockups', methods=['POST'])
@require_admin
def create_mockup():
    """
    POST /api/mockups
    Body: { order_id, image_url, type }
    type: 'moodboard' | 'concept_art' | 'mockup'
    Buffy uploads design assets for an order.
    """
    data = request.get_json()
    if not data or not data.get('order_id'):
        return jsonify({'error': 'order_id required'}), 400
    mockup = Mockup(
        order_id  = data['order_id'],
        image_url = data.get('image_url', ''),
    )
    db.session.add(mockup)
    # Also log in order_images with type
    image_type = data.get('type', 'mockup')
    img = OrderImage(
        order_id = data['order_id'],
        url      = data.get('image_url', ''),
        type     = image_type,
    )
    db.session.add(img)
    db.session.commit()
    return jsonify({'mockup': mockup.to_dict()}), 201


@app.route('/api/mockups/<int:mockup_id>/approve', methods=['POST'])
@require_auth
def approve_mockup(mockup_id):
    """
    POST /api/mockups/<id>/approve
    Body: { approved: true/false, notes: "change notes if rejecting" }
    Customer approves or requests changes on a mockup.
    If not approved, creates a revision request with the customer's notes.
    """
    mockup = Mockup.query.get_or_404(mockup_id)
    order  = Order.query.get_or_404(mockup.order_id)

    # Only the customer who owns the order can approve
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403

    data     = request.get_json()
    approved = data.get('approved', False)
    notes    = data.get('notes', '')

    mockup.approved = approved
    if approved:
        mockup.approval_at = datetime.datetime.utcnow()
    else:
        # Create a revision request with the customer's change notes
        existing_count = Revision.query.filter_by(order_id=mockup.order_id).count()
        revision_number = existing_count + 1
        charge_amount = 0 if revision_number <= 3 else 20.00
        revision = Revision(
            order_id        = mockup.order_id,
            mockup_id       = mockup_id,
            revision_number = revision_number,
            notes           = notes or 'Customer requested changes',
            charge_amount   = charge_amount,
        )
        db.session.add(revision)

    db.session.commit()
    return jsonify({
        'mockup':   mockup.to_dict(),
        'approved': approved,
        'message':  'Mockup approved!' if approved else 'Changes requested — Buffy has been notified.',
    })


# ============================================================
# APP ENTRY POINT
# ============================================================

if __name__ == '__main__':
    # Create all database tables that don't exist yet
    with app.app_context():
        db.create_all()
    # Run the development server
    # Railway uses the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
