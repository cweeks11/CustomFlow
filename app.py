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
    notify_email  = db.Column(db.Boolean, default=True)
    notify_sms    = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'email':        self.email,
            'name':         self.name,
            'role':         self.role,
            'phone':        self.phone,
            'notify_email': self.notify_email,
            'notify_sms':   self.notify_sms,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
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

    def to_dict(self):
        return {
            'id':              self.id,
            'order_id':        self.order_id,
            'mockup_id':       self.mockup_id,
            'revision_number': self.revision_number,
            'notes':           self.notes,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
            'charge_amount':   float(self.charge_amount) if self.charge_amount else 0,
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
    # NOTE: This table may not exist in CustomFlow.sql yet.
    # Run this SQL on Railway to create it:
    # CREATE TABLE invoices (
    #   id SERIAL PRIMARY KEY,
    #   order_id INT REFERENCES orders(id),
    #   type VARCHAR(255),
    #   label VARCHAR(255),
    #   amount NUMERIC(10,2),
    #   status VARCHAR(255) DEFAULT 'uploaded',
    #   file_url TEXT,
    #   uploaded_at TIMESTAMP DEFAULT NOW(),
    #   sent_at TIMESTAMP
    # );
    __tablename__ = 'invoices'
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    type        = db.Column(db.String(255))   # booking | custom | rush | cleaning | final
    label       = db.Column(db.String(255))
    amount      = db.Column(db.Numeric(10, 2))
    status      = db.Column(db.String(255), default='uploaded')  # uploaded | sent
    file_url    = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sent_at     = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'type':        self.type,
            'label':       self.label,
            'amount':      float(self.amount) if self.amount else None,
            'status':      self.status,
            'file_url':    self.file_url,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'sent_at':     self.sent_at.isoformat() if self.sent_at else None,
        }


class Setting(db.Model):
    # Stores key/value pairs for app settings like booking status.
    # NOTE: Create this table on Railway:
    # CREATE TABLE settings (
    #   key VARCHAR(255) PRIMARY KEY,
    #   value TEXT
    # );
    __tablename__ = 'settings'
    key   = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text)


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

    # Check if email already exists
    existing = User.query.filter_by(email=data['email'].lower().strip()).first()
    if existing:
        return jsonify({'error': 'An account with this email already exists'}), 409

    user = User(
        email        = data['email'].lower().strip(),
        name         = data['name'].strip(),
        role         = 'customer',
        phone        = data.get('phone', ''),
        password_hash= generate_password_hash(data['password']),
        notify_email = data.get('notify_email', True),
        notify_sms   = data.get('notify_sms', False),
    )
    db.session.add(user)
    db.session.commit()

    # TODO: send_welcome_email(user.name, user.email)
    # See WELCOME_EMAIL_TEMPLATE in static/core.js for the email content

    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': user.to_dict()}), 201


# ============================================================
# API: ORDERS
# ============================================================

@app.route('/api/orders', methods=['GET'])
@require_auth
def get_orders():
    """
    GET /api/orders
    Returns orders based on who is asking:
      - Admin/owner/employee: returns ALL orders
      - Customer: returns only THEIR orders

    Called by: admin-orders.html, customer-portal.html
    """
    if request.user_role in ['owner', 'employee']:
        orders = Order.query.order_by(Order.created_at.desc()).all()
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


# ============================================================
# API: ADD-ONS
# ============================================================

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
# API: INVOICES
# ============================================================

@app.route('/api/orders/<int:order_id>/invoices', methods=['GET'])
@require_auth
def get_invoices(order_id):
    """
    GET /api/orders/<id>/invoices
    Returns all invoices for an order.
    Customers only see invoices with status='sent'.

    Called by: customer-order-detail.html, admin-order-detail.html
    """
    try:
        if request.user_role in ['owner', 'employee']:
            invoices = Invoice.query.filter_by(order_id=order_id).all()
        else:
            invoices = Invoice.query.filter_by(order_id=order_id, status='sent').all()
        return jsonify([i.to_dict() for i in invoices])
    except Exception:
        return jsonify([])  # invoices table may not exist yet


@app.route('/api/invoices/<int:invoice_id>/send', methods=['POST'])
@require_admin
def send_invoice(invoice_id):
    """
    POST /api/invoices/<id>/send
    Marks invoice as sent and triggers email to customer.

    Called by: admin-order-detail.html when Buffy clicks "Send to Customer"

    TODO: Attach PDF and send via SendGrid.
    See buildInvoiceEmailHtml() in static/core.js for the email template.
    """
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status  = 'sent'
        invoice.sent_at = datetime.datetime.utcnow()
        db.session.commit()

        # TODO: Send invoice email via SendGrid
        # order = Order.query.get(invoice.order_id)
        # customer = User.query.get(order.user_id)
        # html = buildInvoiceEmailHtml(customer.name, order.item_type,
        #                              order.id, invoice.label, invoice.amount)
        # send_via_sendgrid(to=customer.email, subject='New Invoice', html=html)

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

    return jsonify({
        'active':  [o.to_dict() for o in active],
        'waiting': [o.to_dict() for o in waiting],
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

    # Total revenue from paid payments
    total_revenue = db.session.query(func.sum(Payment.amount))\
        .filter_by(status='paid').scalar() or 0

    # Revenue by payment type
    revenue_by_type = dict(
        db.session.query(Payment.type, func.sum(Payment.amount))
        .filter_by(status='paid').group_by(Payment.type).all()
    )

    # Orders by pricing tier
    tier_counts = dict(
        db.session.query(Order.pricing_tier, func.count(Order.id))
        .group_by(Order.pricing_tier).all()
    )

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
        if user:
            top_customers.append({
                'user': user.to_dict(),
                'total_paid': float(total or 0),
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
    Returns all non-customer users (admins and employees).

    Called by: admin-settings.html → User Management section
    """
    users = User.query.filter(User.role.in_(['owner', 'employee'])).all()
    return jsonify([u.to_dict() for u in users])


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
    Body: { name, phone, notify_email, notify_sms }
    Returns: { user }

    Called by: customer-settings.html when customer saves profile changes
    """
    data = request.get_json()
    user = User.query.get_or_404(request.user_id)
    if 'name'         in data: user.name         = data['name']
    if 'phone'        in data: user.phone        = data['phone']
    if 'notify_email' in data: user.notify_email = data['notify_email']
    if 'notify_sms'   in data: user.notify_sms   = data['notify_sms']
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
    Returns FAQ list. No auth required — shown on terms page and customer portal.

    Called by: customer-terms.html, customer-portal.html
    TODO: Store FAQs in a database table. For now returns hardcoded defaults.
    """
    faqs = [
        {'q': 'What is the return policy?',           'a': 'All custom orders are final sale. Every piece is one-of-one and made specifically for you.'},
        {'q': 'How long does an order take?',         'a': 'Typically 2–4 weeks from when Buffy receives your item, depending on complexity.'},
        {'q': 'What is the booking fee?',             'a': 'The booking fee is $50 and is non-refundable. It moves your order from the Free Waitlist to the Paid Waitlist.'},
        {'q': 'How many revisions do I get?',         'a': 'Up to 3 revisions are included at no charge. Additional revisions beyond 3 are available for a fee.'},
        {'q': 'What is a rush order?',                'a': 'Rush fee is 50% of your custom fee and requires Buffy\'s approval based on schedule availability.'},
        {'q': 'What if my item is pre-loved (used)?', 'a': 'A cleaning fee applies to pre-loved items before painting can begin.'},
        {'q': 'How do I send my item to Buffy?',      'a': 'After approval and deposit, Buffy will provide her shipping address.'},
        {'q': 'Can I request a consult call?',        'a': 'Yes! Rush orders receive priority scheduling.'},
    ]
    return jsonify(faqs)


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
