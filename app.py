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
#   python .py
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

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

db = SQLAlchemy(app)


# ============================================================
# DATABASE MODELS
# ============================================================

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    name          = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(255), nullable=False, default='customer')
    phone         = db.Column(db.String(255))
    password_hash = db.Column(db.String(512))
    notify_email   = db.Column(db.Boolean, default=True)
    is_active      = db.Column(db.Boolean, default=True)
    customer_type  = db.Column(db.String(50), default='individual')
    influencer_status = db.Column(db.String(20))
    created_at     = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':                self.id,
            'email':             self.email,
            'name':              self.name,
            'role':              self.role,
            'phone':             self.phone,
            'notify_email':      self.notify_email,
            'is_active':         self.is_active if self.is_active is not None else True,
            'customer_type':     self.customer_type or 'individual',
            'influencer_status': self.influencer_status,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id                = db.Column(db.Integer, primary_key=True)
    order_number      = db.Column(db.String(20), unique=True)
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
    is_archived       = db.Column(db.Boolean, default=False)
    archived_at       = db.Column(db.DateTime)
    created_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        try:
            order_num = self.order_number or f'{self.id:08d}'
        except Exception:
            order_num = f'{self.id:08d}'
        return {
            'id':                self.id,
            'order_number':      order_num,
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
            'is_archived':       getattr(self, 'is_archived', False) or False,
            'archived_at':       self.archived_at.isoformat() if getattr(self, 'archived_at', None) else None,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
            'updated_at':        self.updated_at.isoformat() if self.updated_at else None,
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    type            = db.Column(db.String(255), nullable=False)
    method          = db.Column(db.String(255))
    status          = db.Column(db.String(255), default='paid')
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
    type        = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'url':         self.url,
            'type':        self.type,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def to_dict_meta(self):
        return {
            'id':          self.id,
            'order_id':    self.order_id,
            'url':         None,
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
    __tablename__ = 'invoices'
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    type        = db.Column(db.String(255))
    label       = db.Column(db.String(255))
    amount      = db.Column(db.Numeric(10, 2))
    doc_type    = db.Column(db.String(20), default='invoice')
    doc_number  = db.Column(db.String(50))
    line_items  = db.Column(db.Text)
    subtotal    = db.Column(db.Numeric(10, 2))
    notes       = db.Column(db.Text)
    status      = db.Column(db.String(255), default='draft')
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


class CustomItem(db.Model):
    __tablename__ = 'custom_items'
    id         = db.Column(db.Integer, primary_key=True)
    icon       = db.Column(db.String(20), nullable=False, default='✨')
    label      = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active  = db.Column(db.Boolean, default=True)
    tiers      = db.relationship('ItemPricingTier', backref='item', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':         self.id,
            'icon':       self.icon,
            'label':      self.label,
            'sort_order': self.sort_order,
            'is_active':  self.is_active if self.is_active is not None else True,
            'tiers':      [t.to_dict() for t in sorted(self.tiers, key=lambda x: x.sort_order)],
        }


class ItemPricingTier(db.Model):
    __tablename__ = 'item_pricing_tiers'
    id          = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey('custom_items.id'), nullable=False)
    name        = db.Column(db.Text, nullable=False)
    price_label = db.Column(db.Text)
    description = db.Column(db.Text)
    sort_order  = db.Column(db.Integer, default=0)
    is_active   = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'item_id':     self.item_id,
            'name':        self.name,
            'price_label': self.price_label,
            'description': self.description,
            'sort_order':  self.sort_order,
            'is_active':   self.is_active if self.is_active is not None else True,
        }
        
class HowItWorksStep(db.Model):
    __tablename__ = 'how_it_works_steps'
    id          = db.Column(db.Integer, primary_key=True)
    step_number = db.Column(db.Integer, nullable=False)
    title       = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    sort_order  = db.Column(db.Integer, default=0)
    is_active   = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'step_number': self.step_number,
            'title':       self.title,
            'description': self.description,
            'sort_order':  self.sort_order,
            'is_active':   self.is_active if self.is_active is not None else True,
        }

# ============================================================
# EMAIL HELPERS
# ============================================================

LOGO_URL      = 'https://raw.githubusercontent.com/copeaestheticcustoms/CustomFlow/main/static/logo_gold_transparent.png'
SITE_URL      = 'https://copeaesthetic.studio'
CUSTOMS_URL   = 'https://customs.copeaesthetic.studio'
PORTAL_URL    = 'https://app.copeaesthetic.studio'

def _email_wrap(headline, subheadline, body_html, accent_color='#F217A5'):
    """Wrap content in the branded Cope Aesthetic email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Cope Aesthetic Customs</title>
</head>
<body style="margin:0;padding:0;background:#0D0D0D;font-family:Georgia,'Times New Roman',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D0D;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- LOGO HEADER -->
        <tr>
          <td align="center" style="padding:40px 0 24px;">
            <img src="{LOGO_URL}" alt="Cope Aesthetic Customs" width="320"
                 style="display:block;max-width:320px;width:100%;"/>
          </td>
        </tr>

        <!-- GOLD DIVIDER -->
        <tr>
          <td style="padding:0 0 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="height:1px;background:linear-gradient(to right,transparent,#D8BC84,transparent);font-size:0;line-height:0;">&nbsp;</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- HEADLINE BLOCK -->
        <tr>
          <td align="center" style="padding:0 32px 32px;">
            <div style="color:{accent_color};font-size:11px;letter-spacing:6px;text-transform:uppercase;font-family:Arial,sans-serif;font-weight:700;margin-bottom:16px;">
              Cope Aesthetic Customs
            </div>
            <div style="color:#D8BC84;font-size:36px;line-height:1.2;font-family:Georgia,'Times New Roman',serif;font-weight:normal;margin-bottom:12px;">
              {headline}
            </div>
            <div style="color:#858488;font-size:14px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;">
              {subheadline}
            </div>
          </td>
        </tr>

        <!-- GOLD DIVIDER -->
        <tr>
          <td style="padding:0 32px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="height:1px;background:linear-gradient(to right,transparent,#D8BC84,transparent);font-size:0;line-height:0;">&nbsp;</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- BODY CONTENT -->
        <tr>
          <td style="padding:0 40px 40px;">
            {body_html}
          </td>
        </tr>

        <!-- SIGNATURE -->
        <tr>
          <td style="padding:0 40px 40px;">
            <div style="border-left:3px solid #F217A5;padding-left:16px;">
              <div style="color:#D8BC84;font-size:18px;font-family:Georgia,'Times New Roman',serif;font-style:italic;margin-bottom:4px;">
                ~buffy
              </div>
              <div style="color:#858488;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;">
                Cope Aesthetic Customs
              </div>
            </div>
          </td>
        </tr>

        <!-- GOLD DIVIDER -->
        <tr>
          <td style="padding:0 32px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="height:1px;background:linear-gradient(to right,transparent,#D8BC84,transparent);font-size:0;line-height:0;">&nbsp;</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- FOOTER BUTTONS -->
        <tr>
          <td align="center" style="padding:0 32px 40px;">
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:0 6px;">
                  <a href="{SITE_URL}" style="display:inline-block;background:transparent;border:1px solid #D8BC84;color:#D8BC84;text-decoration:none;font-size:10px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;padding:10px 18px;">
                    Cope Aesthetic Studio
                  </a>
                </td>
                <td style="padding:0 6px;">
                  <a href="{CUSTOMS_URL}" style="display:inline-block;background:#F217A5;border:1px solid #F217A5;color:#fff;text-decoration:none;font-size:10px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;padding:10px 18px;font-weight:700;">
                    Cope Aesthetic Customs
                  </a>
                </td>
                <td style="padding:0 6px;">
                  <a href="{PORTAL_URL}" style="display:inline-block;background:transparent;border:1px solid #44118C;color:#858488;text-decoration:none;font-size:10px;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;padding:10px 18px;">
                    Custom Order Portal
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- BOTTOM TAGLINE -->
        <tr>
          <td align="center" style="padding:0 32px 48px;">
            <div style="color:#44118C;font-size:10px;letter-spacing:3px;text-transform:uppercase;font-family:Arial,sans-serif;">
              Unleash Your Wild Truth
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _info_row(label, value, highlight=False):
    """A single info row for order/customer detail tables."""
    val_style = 'color:#F217A5;font-weight:700;' if highlight else 'color:#ffffff;font-weight:600;'
    return f"""
    <tr>
      <td style="padding:10px 0;color:#858488;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-family:Arial,sans-serif;width:130px;border-bottom:1px solid #1a1a1a;">{label}</td>
      <td style="padding:10px 0;font-size:15px;font-family:Georgia,serif;border-bottom:1px solid #1a1a1a;{val_style}">{value}</td>
    </tr>"""


def _primary_button(text, url):
    return f"""
    <table cellpadding="0" cellspacing="0" style="margin:28px 0;">
      <tr>
        <td style="background:#F217A5;">
          <a href="{url}" style="display:inline-block;background:#F217A5;color:#ffffff;text-decoration:none;font-size:12px;letter-spacing:3px;text-transform:uppercase;font-family:Arial,sans-serif;font-weight:700;padding:16px 36px;">
            {text} &rarr;
          </a>
        </td>
      </tr>
    </table>"""


def send_email(to_email, subject, html_body, text_body=None):
    import resend as _resend
    api_key = os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        print(f'[EMAIL] RESEND_API_KEY not set — skipping email to {to_email}: {subject}')
        return False
    try:
        _resend.api_key = api_key
        payload = {
            'from': 'Cope Aesthetic Customs <customflow@email.copeaesthetic.studio>',
            'to':   to_email,
            'subject': subject,
            'html': html_body,
        }
        if text_body:
            payload['text'] = text_body
        _resend.Emails.send(payload)
        print(f'[EMAIL] Sent to {to_email}: {subject}')
        return True
    except Exception as e:
        print(f'[EMAIL] Failed to send to {to_email}: {e}')
        return False


def _notify_buffy_special_customer(user, type_label):
    subject     = f'[Cope Aesthetic] New {type_label} Customer — {user.name}'
    body = f"""
    <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.8;margin:0 0 28px;">
      A new account has been created that needs your attention.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      {_info_row('Name', user.name)}
      {_info_row('Email', user.email)}
      {_info_row('Phone', user.phone or 'Not provided')}
      {_info_row('Account Type', type_label, highlight=True)}
    </table>
    <p style="color:#858488;font-size:13px;font-family:Arial,sans-serif;letter-spacing:1px;">
      Log in to the admin portal to review and approve this account.
    </p>
    {_primary_button('Review Account', PORTAL_URL)}
    """
    admin_users = User.query.filter(User.role.in_(['owner', 'employee'])).all()
    for admin in admin_users:
        send_email(admin.email, subject, _email_wrap(
            'New Special Account',
            type_label,
            body,
            accent_color='#D8BC84'
        ))


# ============================================================
# AUTH HELPERS
# ============================================================

def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role':    role,
        'exp':     datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
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
# ============================================================

@app.route('/')
def index():
    return send_from_directory('static', 'landing.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# ============================================================
# API: AUTH
# ============================================================

@app.route('/api/login', methods=['POST'])
def login():
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
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Name, email, and password required'}), 400

    captcha_token = data.get('captcha_token', '')
    secret_key    = os.environ.get('RECAPTCHA_SECRET_KEY', '')
    if secret_key:
        if not captcha_token:
            return jsonify({'error': 'Please complete the reCAPTCHA check.'}), 400
        import urllib.request, urllib.parse
        verify_url  = 'https://www.google.com/recaptcha/api/siteverify'
        verify_data = urllib.parse.urlencode({'secret': secret_key, 'response': captcha_token}).encode()
        try:
            with urllib.request.urlopen(verify_url, verify_data, timeout=5) as resp:
                import json as _json
                result = _json.loads(resp.read().decode())
            if not result.get('success'):
                return jsonify({'error': 'reCAPTCHA verification failed. Please try again.'}), 400
        except Exception:
            pass

    existing = User.query.filter_by(email=data['email'].lower().strip()).first()
    if existing:
        return jsonify({'error': 'An account with this email already exists'}), 409

    customer_type = data.get('customer_type', 'individual')
    SPECIAL_TYPES = {'group', 'influencer', 'nonprofit', 'organization'}

    user = User(
        email             = data['email'].lower().strip(),
        name              = data['name'].strip(),
        role              = 'customer',
        phone             = data.get('phone', ''),
        password_hash     = generate_password_hash(data['password']),
        notify_email      = data.get('notify_email', True),
        customer_type     = customer_type,
        influencer_status = 'pending' if customer_type == 'influencer' else None,
    )
    db.session.add(user)
    db.session.commit()

    # Welcome email to new customer
    _welcome_body = f"""
    <p style="color:#D8BC84;font-size:22px;font-family:Georgia,serif;font-style:italic;margin:0 0 20px;">
      Welcome, {user.name}.
    </p>
    <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 24px;">
      Your account is live. Every custom painted piece is a ritual of self&#8209;expression —
      and yours starts right here.
    </p>
    <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 32px;">
      Browse pricing, join the waitlist, and track every step of your order from your personal dashboard.
      When you're ready, Buffy is ready.
    </p>
    {_primary_button('Go to My Dashboard', PORTAL_URL)}
    <p style="color:#44118C;font-size:12px;font-family:Arial,sans-serif;letter-spacing:1px;margin:24px 0 0;">
      Questions? Just reply to this email — Buffy checks it personally.
    </p>
    """
    send_email(
        user.email,
        'Welcome to Cope Aesthetic Customs \u2756',
        _email_wrap('Welcome to the Family', 'Your account is ready', _welcome_body)
    )

    # Notify Buffy if special account type
    if customer_type in SPECIAL_TYPES:
        type_label = customer_type.replace('nonprofit', 'Non-Profit').capitalize()
        _notify_buffy_special_customer(user, type_label)

    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': user.to_dict()}), 201





@app.route('/api/admin/test-email', methods=['POST'])
def test_email():
    api_key = os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'RESEND_API_KEY not set in Railway variables'}), 400
    data    = request.get_json() or {}
    test_to = data.get('to') or os.environ.get('RESEND_TEST_TO', '')
    if not test_to:
        return jsonify({'error': 'Provide a "to" email in the request body or set RESEND_TEST_TO in Railway'}), 400
    result = send_email(
        test_to,
        '\u2756 Cope Aesthetic Customs \u2014 Email Test',
        _email_wrap(
            'Email is Working',
            'Test Confirmed',
            f"""<p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 24px;">
              Resend is configured correctly and this branded email template is live.
              You're all set, Buffy.
            </p>
            <p style="color:#D8BC84;font-size:13px;font-family:Arial,sans-serif;letter-spacing:1px;">
              Sent to: {test_to}
            </p>""",
            accent_color='#D8BC84'
        )
    )
    if result:
        return jsonify({'message': f'Test email sent to {test_to}!'})
    return jsonify({'error': 'Send failed — check Railway logs for details'}), 500


@app.route('/api/admin/preview-token', methods=['POST'])
@require_admin
def admin_preview_token():
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
    show_archived = request.args.get('archived', 'false').lower() == 'true'
    if request.user_role in ['owner', 'employee']:
        try:
            orders = Order.query.filter_by(is_archived=show_archived).order_by(Order.created_at.desc()).all()
        except Exception:
            orders = Order.query.order_by(Order.created_at.desc()).all()
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
        try:
            orders = Order.query.filter_by(user_id=request.user_id, is_archived=False).order_by(Order.created_at.desc()).all()
        except Exception:
            orders = Order.query.filter_by(user_id=request.user_id).order_by(Order.created_at.desc()).all()
        return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403

    try: payments = [p.to_dict() for p in Payment.query.filter_by(order_id=order_id).all()]
    except Exception: payments = []
    try: mockups = [m.to_dict() for m in Mockup.query.filter_by(order_id=order_id).all()]
    except Exception: mockups = []
    try: revisions = [r.to_dict() for r in Revision.query.filter_by(order_id=order_id).order_by(Revision.revision_number).all()]
    except Exception: revisions = []
    try: order_images = [i.to_dict_meta() for i in OrderImage.query.filter_by(order_id=order_id).all()]
    except Exception: order_images = []
    try: status_history = [h.to_dict() for h in StatusHistory.query.filter_by(order_id=order_id).order_by(StatusHistory.changed_at).all()]
    except Exception: status_history = []
    try: consult_calls = [c.to_dict() for c in ConsultCall.query.filter_by(order_id=order_id).all()]
    except Exception: consult_calls = []
    try: add_ons = [a.to_dict() for a in AddOn.query.filter_by(order_id=order_id).all()]
    except Exception: add_ons = []
    try: invoices = [i.to_dict() for i in Invoice.query.filter_by(order_id=order_id).all()]
    except Exception: invoices = []
    try:
        customer = User.query.get(order.user_id)
        customer_dict = customer.to_dict() if customer else None
    except Exception: customer_dict = None

    return jsonify({
        'order': order.to_dict(), 'customer': customer_dict,
        'payments': payments, 'mockups': mockups, 'revisions': revisions,
        'order_images': order_images, 'status_history': status_history,
        'consult_calls': consult_calls, 'add_ons': add_ons, 'invoices': invoices,
    })


@app.route('/api/orders/<int:order_id>/archive', methods=['POST'])
@require_admin
def archive_order(order_id):
    order = Order.query.get_or_404(order_id)
    data  = request.get_json() or {}
    if not data.get('keep_photos', True):
        OrderImage.query.filter_by(order_id=order_id).delete()
    order.is_archived = True
    order.archived_at = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({'order': order.to_dict()})


@app.route('/api/orders', methods=['POST'])
@require_auth
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    submitting_user = User.query.get(request.user_id)
    if submitting_user and submitting_user.customer_type == 'influencer' and submitting_user.influencer_status != 'approved':
        status_msg = 'pending Buffy\'s approval' if submitting_user.influencer_status == 'pending' else 'not approved'
        return jsonify({'error': f'Your influencer account is {status_msg}. You cannot place orders until your account is approved.'}), 403

    order = Order(
        user_id          = request.user_id,
        item_type        = data.get('item_type'),
        pricing_tier     = data.get('pricing_tier'),
        customer_notes   = data.get('customer_notes', ''),
        is_rush          = data.get('is_rush', False),
        must_have_by     = data.get('must_have_by'),
        has_cleaning_fee = data.get('has_cleaning_fee', False),
        status           = 'free_waitlist',
    )
    db.session.add(order)
    db.session.flush()
    order.order_number = generate_order_number()

    history = StatusHistory(
        order_id=order.id, from_status=None, to_status='free_waitlist',
        changed_by=request.user_id, note='Order submitted by customer',
    )
    db.session.add(history)

    if data.get('wants_consult'):
        consult = ConsultCall(
            order_id=order.id,
            scheduled_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
            duration_minutes=30,
            notes='Customer requested consult — please schedule',
        )
        db.session.add(consult)

    db.session.commit()

    # Order confirmation email to customer
    creator = User.query.get(order.user_id)
    if creator and creator.notify_email:
        order_num = order.order_number or str(order.id)
        _confirm_body = f"""
        <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 28px;">
          {creator.name}, your order is in. Buffy will be in touch as things move forward —
          in the meantime, you can track every step from your dashboard.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
          {_info_row('Order', f'#{order_num}')}
          {_info_row('Item', order.item_type or '&mdash;')}
          {_info_row('Tier', (order.pricing_tier or '&mdash;').capitalize())}
          {_info_row('Status', 'On the Waitlist', highlight=True)}
        </table>
        {_primary_button('Track My Order', PORTAL_URL)}
        """
        send_email(
            creator.email,
            f'Order #{order_num} Confirmed \u2756 Cope Aesthetic Customs',
            _email_wrap('Order Received', f'Order #{order_num}', _confirm_body)
        )

        # Notify all admins that a new order was submitted
    if creator:
        order_num = order.order_number or str(order.id)
        _admin_order_body = f"""
        <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.8;margin:0 0 28px;">
          A new custom order has just been submitted and is waiting on the free waitlist.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
          {_info_row('Order', f'#{order_num}')}
          {_info_row('Customer', creator.name)}
          {_info_row('Email', creator.email)}
          {_info_row('Item', order.item_type or '&mdash;')}
          {_info_row('Tier', (order.pricing_tier or '&mdash;').capitalize())}
          {_info_row('Rush', 'Yes' if order.is_rush else 'No', highlight=order.is_rush)}
        </table>
        {_primary_button('View Order', PORTAL_URL)}
        """
        admin_users = User.query.filter(User.role.in_(['owner', 'employee'])).all()
        for admin in admin_users:
            send_email(
                admin.email,
                f'[New Order] #{order_num} — {creator.name}',
                _email_wrap('New Order Submitted', f'#{order_num}', _admin_order_body, accent_color='#D8BC84')
            )

    return jsonify({'order': order.to_dict()}), 201


@app.route('/api/orders/<int:order_id>', methods=['PATCH'])
@require_auth
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    old_status = order.status
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

    if 'status' in data and data['status'] != old_status:
        history = StatusHistory(
            order_id=order_id, from_status=old_status, to_status=data['status'],
            changed_by=request.user_id, note=data.get('note', 'Status updated'),
        )
        db.session.add(history)

    db.session.commit()

    # Email customer on status change
    if 'status' in data and data['status'] != old_status:
        customer = User.query.get(order.user_id)
        if customer and customer.notify_email:
            STATUS_LABELS = {
                'free_waitlist':    'On the Free Waitlist',
                'paid_waitlist':    'Booking Fee Paid — You\'re Confirmed! 🎉',
                'production_queue': 'In the Production Queue',
                'prep':             'In Prep',
                'painting':         'Being Painted 🎨',
                'drying':           'Drying',
                'finishing':        'In Finishing',
                'quality_check':    'Quality Check',
                'shipped':          'Shipped! 📦',
                'delivered':        'Delivered ✅',
                'complete':         'Complete',
                'on_hold':          'On Hold',
                'cancelled':        'Cancelled',
            }
            label     = STATUS_LABELS.get(data['status'], data['status'].replace('_', ' ').title())
            order_num = order.order_number or str(order.id)
            _status_body = f"""
            <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 28px;">
              {customer.name}, something just changed on your order. Here's where things stand right now.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              {_info_row('Order', f'#{order_num}')}
              {_info_row('New Status', label, highlight=True)}
            </table>
            {_primary_button('View My Order', PORTAL_URL)}
            """
            send_email(
                customer.email,
                f'Order #{order_num} Update \u2756 {label}',
                _email_wrap('Order Update', f'Order #{order_num}', _status_body)
            )

    return jsonify({'order': order.to_dict()})


# ============================================================
# API: PAYMENTS
# ============================================================

@app.route('/api/payments', methods=['POST'])
@require_admin
def create_payment():
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('amount'):
        return jsonify({'error': 'order_id and amount required'}), 400
    payment = Payment(
        order_id=data['order_id'], amount=data['amount'],
        type=data.get('type', 'custom'), method=data.get('method', 'Other'),
        status=data.get('status', 'paid'), external_txn_id=data.get('external_txn_id', ''),
    )
    db.session.add(payment)
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
    data = request.get_json()
    if not data or not data.get('order_id'):
        return jsonify({'error': 'order_id required'}), 400
    existing_count  = Revision.query.filter_by(order_id=data['order_id']).count()
    revision_number = existing_count + 1
    charge_amount   = 0 if revision_number <= 3 else 20.00
    revision = Revision(
        order_id=data['order_id'], mockup_id=data.get('mockup_id'),
        revision_number=revision_number, notes=data.get('notes', ''),
        charge_amount=charge_amount,
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify({'revision': revision.to_dict()}), 201


@app.route('/api/revisions/<int:revision_id>', methods=['PATCH'])
@require_admin
def update_revision(revision_id):
    revision = Revision.query.get_or_404(revision_id)
    data = request.get_json() or {}
    if 'completed' in data:
        revision.completed = data['completed']
    db.session.commit()
    return jsonify({'revision': revision.to_dict()})


@app.route('/api/revisions/<int:revision_id>', methods=['DELETE'])
@require_admin
def delete_revision(revision_id):
    revision = Revision.query.get_or_404(revision_id)
    db.session.delete(revision)
    db.session.commit()
    return jsonify({'deleted': revision_id})


@app.route('/api/orders/<int:order_id>/images', methods=['GET'])
@require_auth
def get_order_images(order_id):
    order = Order.query.get_or_404(order_id)
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403
    images = OrderImage.query.filter_by(order_id=order_id).all()
    return jsonify([i.to_dict() for i in images])


@app.route('/api/orders/<int:order_id>/images', methods=['POST'])
@require_auth
def upload_order_image(order_id):
    data = request.get_json()
    if not data or not data.get('url') or not data.get('type'):
        return jsonify({'error': 'url and type required'}), 400
    order = Order.query.get_or_404(order_id)
    if request.user_role == 'customer':
        if order.user_id != request.user_id:
            return jsonify({'error': 'Not authorized'}), 403
        if data['type'] not in ('reference',):
            return jsonify({'error': 'Customers can only upload reference photos'}), 403
    image = OrderImage(order_id=order_id, url=data['url'], type=data['type'])
    db.session.add(image)
    if data['type'] == 'mockup':
        mockup = Mockup(order_id=order_id, image_url=data['url'], approved=False, revision_limit=3)
        db.session.add(mockup)
    db.session.commit()

    # If this is a mockup upload, email the customer
    if data['type'] == 'mockup':
        customer = User.query.get(order.user_id)
        if customer and customer.notify_email is not False:
            order_num = order.order_number or str(order.id)
            _mockup_body = f"""
            <p style="color:#D8BC84;font-size:22px;font-family:Georgia,serif;font-style:italic;margin:0 0 20px;">
              Your design is ready.
            </p>
            <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 28px;">
              {customer.name}, Buffy has uploaded your custom mockup for order #{order_num}.
              Head to your portal to review it — approve it to move into production,
              or request changes if something needs adjusting.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              {_info_row('Order', f'#{order_num}')}
              {_info_row('Action Needed', 'Review &amp; Approve Your Mockup', highlight=True)}
            </table>
            {_primary_button('Review My Mockup', PORTAL_URL)}
            <p style="color:#44118C;font-size:12px;font-family:Arial,sans-serif;letter-spacing:1px;margin:24px 0 0;">
              You have up to 3 free revisions included with your order.
            </p>
            """
            send_email(
                customer.email,
                f'Your Mockup is Ready ❖ Order #{order_num}',
                _email_wrap('Your Mockup is Ready', 'Action Required', _mockup_body)
            )

    return jsonify({'image': image.to_dict()}), 201


@app.route('/api/orders/<int:order_id>/images/<int:image_id>', methods=['DELETE'])
@require_admin
def delete_order_image(order_id, image_id):
    image = OrderImage.query.filter_by(id=image_id, order_id=order_id).first_or_404()
    db.session.delete(image)
    db.session.commit()
    return jsonify({'deleted': image_id})


@app.route('/api/add_ons', methods=['POST'])
@require_admin
def create_addon():
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('name'):
        return jsonify({'error': 'order_id and name required'}), 400
    addon = AddOn(
        order_id=data['order_id'], name=data['name'],
        price=data.get('price', 0), quantity=data.get('quantity', 1),
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
    data = request.get_json()
    if not data or not data.get('order_id') or not data.get('scheduled_at'):
        return jsonify({'error': 'order_id and scheduled_at required'}), 400
    consult = ConsultCall(
        order_id=data['order_id'],
        scheduled_at=datetime.datetime.fromisoformat(data['scheduled_at']),
        duration_minutes=data.get('duration_minutes', 30),
        notes=data.get('notes', ''),
        completed_by=request.user_id,
    )
    db.session.add(consult)
    db.session.commit()
    return jsonify({'consult_call': consult.to_dict()}), 201


# ============================================================
# API: INVOICES / ESTIMATES / RECEIPTS
# ============================================================

def generate_order_number():
    try:
        year     = datetime.datetime.utcnow().year
        year_str = str(year)
        existing = db.session.query(Order.order_number)\
            .filter(Order.order_number.like(f'__{year_str}__')).all()
        existing_nums = [r[0] for r in existing if r[0]]
        if not existing_nums:
            return f'00{year_str}00'
        max_total = 0
        for num in existing_nums:
            try:
                total = int(num[0:2]) * 100 + int(num[6:8])
                if total > max_total:
                    max_total = total
            except (ValueError, IndexError):
                continue
        next_total = max_total + 1
        return f'{next_total // 100:02d}{year_str}{next_total % 100:02d}'
    except Exception:
        return None


def _doc_number(order_number, doc_type):
    suffix = {'estimate': 'E', 'invoice': 'I', 'receipt': 'R'}.get(doc_type, 'I')
    return f"{order_number}{suffix}"


@app.route('/api/orders/<int:order_id>/invoices', methods=['GET'])
@require_auth
def get_invoices(order_id):
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
    import json as _json
    data       = request.get_json() or {}
    doc_type   = data.get('doc_type', 'invoice')
    line_items = data.get('line_items', [])
    if not line_items:
        return jsonify({'error': 'No line items provided'}), 400
    subtotal  = sum(float(li.get('amount', 0)) for li in line_items)
    order     = Order.query.get_or_404(order_id)
    order_num = order.order_number or f'{order_id:08d}'
    inv = Invoice(
        order_id=order_id, doc_type=doc_type,
        doc_number=_doc_number(order_num, doc_type),
        line_items=_json.dumps(line_items), subtotal=subtotal, amount=subtotal,
        label=doc_type.capitalize(), notes=data.get('notes', ''),
        status='draft', uploaded_at=datetime.datetime.utcnow(),
    )
    db.session.add(inv)
    db.session.commit()
    return jsonify({'invoice': inv.to_dict()}), 201


@app.route('/api/invoices/<int:invoice_id>', methods=['PATCH'])
@require_admin
def update_invoice(invoice_id):
    import json as _json
    data    = request.get_json() or {}
    invoice = Invoice.query.get_or_404(invoice_id)
    if 'line_items' in data:
        invoice.line_items = _json.dumps(data['line_items'])
        invoice.subtotal   = sum(float(li.get('amount', 0)) for li in data['line_items'])
        invoice.amount     = invoice.subtotal
    if 'notes'    in data: invoice.notes    = data['notes']
    if 'file_url' in data: invoice.file_url = data['file_url']
    db.session.commit()
    return jsonify({'invoice': invoice.to_dict()})


@app.route('/api/invoices/<int:invoice_id>', methods=['DELETE'])
@require_admin
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    return jsonify({'deleted': invoice_id})


@app.route('/api/invoices/<int:invoice_id>/send', methods=['POST'])
@require_admin
def send_invoice(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status  = 'sent'
        invoice.sent_at = datetime.datetime.utcnow()
        db.session.commit()

        order    = Order.query.get(invoice.order_id)
        customer = User.query.get(order.user_id) if order else None
        if customer and customer.notify_email:
            order_num  = order.order_number or str(order.id)
            doc_label  = (invoice.doc_type or 'invoice').capitalize()
            amount     = invoice.amount or invoice.subtotal
            amount_str = f'${float(amount):,.2f}' if amount else '&mdash;'
            _invoice_body = f"""
            <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 28px;">
              {customer.name}, your {doc_label.lower()} is ready. Review it in your portal and reach out
              to Buffy if you have any questions before moving forward.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              {_info_row('Order', f'#{order_num}')}
              {_info_row('Document', doc_label)}
              {_info_row('Amount Due', amount_str, highlight=True)}
            </table>
            {_primary_button(f'View My {doc_label}', PORTAL_URL)}
            """
            send_email(
                customer.email,
                f'Your {doc_label} is Ready \u2756 Order #{order_num}',
                _email_wrap(f'Your {doc_label} is Ready', f'Order #{order_num}', _invoice_body)
            )

        return jsonify({'invoice': invoice.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# API: PRODUCTION QUEUE
# ============================================================

@app.route('/api/queue', methods=['GET'])
@require_admin
def get_queue():
    active_statuses  = ['production_queue', 'prep', 'painting']
    waiting_statuses = ['paid_waitlist']

    def queue_sort_key(order):
        if order.is_rush and order.rush_approved:
            return (1, order.must_have_by or datetime.date.max)
        elif order.must_have_by:
            return (2, order.must_have_by)
        else:
            booking = Payment.query.filter_by(order_id=order.id, type='booking', status='paid').first()
            date = booking.recorded_at.date() if booking else order.created_at.date()
            return (3, date)

    active  = sorted(Order.query.filter(Order.status.in_(active_statuses)).all(),  key=queue_sort_key)
    waiting = sorted(Order.query.filter(Order.status.in_(waiting_statuses)).all(), key=queue_sort_key)
    all_orders = active + waiting
    user_ids   = list({o.user_id for o in all_orders})
    users      = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}

    def enrich(o):
        d = o.to_dict()
        u = users.get(o.user_id)
        d['customer_name']  = u.name  if u else '—'
        d['customer_email'] = u.email if u else '—'
        return d

    return jsonify({'active': [enrich(o) for o in active], 'waiting': [enrich(o) for o in waiting]})


# ============================================================
# API: DASHBOARD STATS
# ============================================================

@app.route('/api/dashboard', methods=['GET'])
@require_admin
def get_dashboard():
    from sqlalchemy import func
    total_orders  = Order.query.count()
    rush_pending  = Order.query.filter_by(is_rush=True, rush_approved=False).count()
    in_production = Order.query.filter(Order.status.in_(['production_queue', 'prep', 'painting'])).count()
    completed     = Order.query.filter(Order.status.in_(['completed', 'shipped', 'closed'])).count()
    status_counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    type_counts   = dict(db.session.query(Order.item_type, func.count(Order.id)).group_by(Order.item_type).all())
    recent = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    recent_list = []
    for o in recent:
        d = o.to_dict()
        u = User.query.get(o.user_id)
        d['customer_name'] = u.name if u else '—'
        recent_list.append(d)
    return jsonify({
        'stats': {'total_orders': total_orders, 'rush_pending': rush_pending,
                  'in_production': in_production, 'completed': completed},
        'status_counts': status_counts, 'type_counts': type_counts, 'recent_orders': recent_list,
    })


# ============================================================
# API: REPORTS
# ============================================================

@app.route('/api/reports', methods=['GET'])
@require_admin
def get_reports():
    from sqlalchemy import func
    total_revenue   = db.session.query(func.sum(Payment.amount)).filter(Payment.status.in_(['paid'])).scalar() or 0
    revenue_by_type = {k: float(v) for k, v in
        db.session.query(Payment.type, func.sum(Payment.amount))
        .filter(Payment.status.in_(['paid'])).group_by(Payment.type).all() if k is not None}
    tier_raw    = db.session.query(func.lower(Order.pricing_tier), func.count(Order.id))\
        .filter(Order.pricing_tier.isnot(None)).group_by(func.lower(Order.pricing_tier)).all()
    tier_counts = {k.capitalize(): v for k, v in tier_raw if k}
    top_customers_raw = db.session.query(Order.user_id, func.sum(Payment.amount).label('total'))\
        .join(Payment, Payment.order_id == Order.id).filter(Payment.status == 'paid')\
        .group_by(Order.user_id).order_by(func.sum(Payment.amount).desc()).limit(10).all()
    top_customers = []
    for user_id, total in top_customers_raw:
        user = User.query.get(user_id)
        if user:
            top_customers.append({
                'user': user.to_dict(),
                'total_paid': float(total or 0),
                'order_count': Order.query.filter_by(user_id=user_id).count(),
            })
    return jsonify({
        'total_revenue': float(total_revenue),
        'revenue_by_type': revenue_by_type,
        'tier_counts': tier_counts,
        'top_customers': top_customers,
    })


# ============================================================
# API: USERS
# ============================================================

@app.route('/api/users', methods=['GET'])
@require_admin
def get_users():
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
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['PATCH'])
@require_admin
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    if str(user_id) == str(request.user_id) and 'is_active' in data and not data['is_active']:
        return jsonify({'error': 'You cannot deactivate your own account'}), 400
    if 'name'  in data: user.name  = data['name'].strip()
    if 'email' in data:
        existing = User.query.filter_by(email=data['email'].lower().strip()).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Email already in use'}), 409
        user.email = data['email'].lower().strip()
    if 'phone'         in data: user.phone         = data['phone']
    if 'role'          in data: user.role          = data['role']
    if 'is_active'     in data: user.is_active     = data['is_active']
    if 'customer_type' in data: user.customer_type = data['customer_type']
    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """
    DELETE /api/users/<id>
    Permanently deletes a user and all their related records.
    Handles FK constraints by deleting child records first.
    Cannot delete yourself.
    """
    if str(user_id) == str(request.user_id):
        return jsonify({'error': 'You cannot delete your own account'}), 400
    user = User.query.get_or_404(user_id)
    try:
        # Get all order IDs for this user
        order_ids = [o.id for o in Order.query.filter_by(user_id=user_id).all()]
        if order_ids:
            # Delete order child records in dependency order
            OrderImage.query.filter(OrderImage.order_id.in_(order_ids)).delete(synchronize_session=False)
            StatusHistory.query.filter(StatusHistory.order_id.in_(order_ids)).delete(synchronize_session=False)
            ConsultCall.query.filter(ConsultCall.order_id.in_(order_ids)).delete(synchronize_session=False)
            AddOn.query.filter(AddOn.order_id.in_(order_ids)).delete(synchronize_session=False)
            Invoice.query.filter(Invoice.order_id.in_(order_ids)).delete(synchronize_session=False)
            Payment.query.filter(Payment.order_id.in_(order_ids)).delete(synchronize_session=False)
            # Revisions reference mockups — delete revisions before mockups
            Revision.query.filter(Revision.order_id.in_(order_ids)).delete(synchronize_session=False)
            Mockup.query.filter(Mockup.order_id.in_(order_ids)).delete(synchronize_session=False)
            # Delete the orders themselves
            Order.query.filter(Order.user_id == user_id).delete(synchronize_session=False)
        # Delete status_history rows where this user was the changer
        StatusHistory.query.filter(StatusHistory.changed_by == user_id).delete(synchronize_session=False)
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        return jsonify({'deleted': user_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500


@app.route('/api/users/me', methods=['GET'])
@require_auth
def get_me():
    user = User.query.get_or_404(request.user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/me', methods=['PATCH'])
@require_auth
def update_me():
    data = request.get_json()
    user = User.query.get_or_404(request.user_id)
    old_type = user.customer_type or 'individual'
    if 'name'         in data: user.name         = data['name']
    if 'phone'        in data: user.phone        = data['phone']
    if 'notify_email' in data: user.notify_email = data['notify_email']
    if 'customer_type' in data:
        new_type = data['customer_type']
        user.customer_type = new_type
        if new_type == 'influencer' and old_type != 'influencer':
            user.influencer_status = 'pending'
            _notify_buffy_special_customer(user, 'Influencer (pending approval)')
        elif new_type != 'influencer':
            user.influencer_status = None
        elif new_type in {'group', 'nonprofit', 'organization'} and old_type != new_type:
            type_label = new_type.replace('nonprofit', 'Non-Profit').capitalize()
            _notify_buffy_special_customer(user, f"{type_label} (updated profile)")
    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>/influencer-approval', methods=['POST'])
@require_admin
def influencer_approval(user_id):
    data     = request.get_json() or {}
    approved = data.get('approved', False)
    user     = User.query.get_or_404(user_id)
    if approved:
        user.influencer_status = 'approved'
    else:
        user.influencer_status = 'denied'
        user.customer_type = 'individual'
    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/influencer-pending', methods=['GET'])
@require_admin
def get_influencer_pending():
    try:
        pending = User.query.filter_by(influencer_status='pending').all()
        return jsonify([u.to_dict() for u in pending])
    except Exception:
        return jsonify([])


@app.route('/api/users/<int:user_id>/set-password', methods=['POST'])
@require_admin
def admin_set_password(user_id):
    """
    POST /api/users/<id>/set-password
    Body: { new_password }
    Allows Buffy to reset any user's password from admin settings.
    """
    data   = request.get_json() or {}
    new_pw = data.get('new_password', '')
    if len(new_pw) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    user = User.query.get_or_404(user_id)
    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    return jsonify({'message': 'Password updated'})


@app.route('/api/change-password', methods=['POST'])
@require_auth
def change_password():
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
    try:
        status     = Setting.query.get('booking_status')
        until      = Setting.query.get('booked_until')
        message    = Setting.query.get('booking_message')
        prod_start = Setting.query.get('prod_start')
        return jsonify({
            'status':     status.value     if status     else 'waitlist',
            'until':      until.value      if until      else '2026-05-18',
            'message':    message.value    if message    else 'Currently booked through May 18, 2026',
            'prod_start': prod_start.value if prod_start else 'May 18, 2026',
        })
    except Exception:
        return jsonify({'status': 'waitlist', 'until': '2026-05-18',
                        'message': 'Currently booked through May 18, 2026', 'prod_start': 'May 18, 2026'})


@app.route('/api/settings/booking', methods=['PATCH'])
@require_admin
def update_booking_settings():
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
    try:
        faqs = Faq.query.order_by(Faq.sort_order, Faq.id).all()
        return jsonify([{'id': f.id, 'q': f.question, 'a': f.answer,
                         'question': f.question, 'answer': f.answer, 'sort_order': f.sort_order}
                        for f in faqs])
    except Exception:
        return jsonify([])


@app.route('/api/faqs', methods=['POST'])
@require_admin
def create_faq():
    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({'error': 'question required'}), 400
    faq = Faq(question=data['question'].strip(), answer=data.get('answer', '').strip(),
              sort_order=data.get('sort_order', 0))
    db.session.add(faq)
    db.session.commit()
    return jsonify({'id': faq.id, 'q': faq.question, 'a': faq.answer,
                    'question': faq.question, 'answer': faq.answer, 'sort_order': faq.sort_order}), 201


@app.route('/api/faqs/<int:faq_id>', methods=['PATCH'])
@require_admin
def update_faq(faq_id):
    faq  = Faq.query.get_or_404(faq_id)
    data = request.get_json()
    if 'question'   in data: faq.question   = data['question'].strip()
    if 'answer'     in data: faq.answer     = data['answer'].strip()
    if 'sort_order' in data: faq.sort_order = data['sort_order']
    db.session.commit()
    return jsonify({'id': faq.id, 'q': faq.question, 'a': faq.answer, 'sort_order': faq.sort_order})


@app.route('/api/faqs/<int:faq_id>', methods=['DELETE'])
@require_admin
def delete_faq(faq_id):
    faq = Faq.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify({'deleted': faq_id})

# ============================================================
# API: MOCKUP APPROVAL
# ============================================================

@app.route('/api/mockups', methods=['POST'])
@require_admin
def create_mockup():
    data = request.get_json()
    if not data or not data.get('order_id'):
        return jsonify({'error': 'order_id required'}), 400
    mockup = Mockup(order_id=data['order_id'], image_url=data.get('image_url', ''))
    db.session.add(mockup)
    img = OrderImage(order_id=data['order_id'], url=data.get('image_url', ''), type=data.get('type', 'mockup'))
    db.session.add(img)
    db.session.commit()

    # Notify customer that their mockup is ready for review
    order    = Order.query.get(data['order_id'])
    customer = User.query.get(order.user_id) if order else None
    if customer and customer.notify_email:
        order_num = order.order_number or str(order.id)
        _mockup_body = f"""
        <p style="color:#D8BC84;font-size:22px;font-family:Georgia,serif;font-style:italic;margin:0 0 20px;">
          Your design is ready.
        </p>
        <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.9;margin:0 0 28px;">
          {customer.name}, Buffy has uploaded your custom mockup for order #{order_num}.
          Head to your portal to review it — approve it to move into production,
          or request changes if something needs adjusting.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
          {_info_row('Order', f'#{order_num}')}
          {_info_row('Action Needed', 'Review &amp; Approve Your Mockup', highlight=True)}
        </table>
        {_primary_button('Review My Mockup', PORTAL_URL)}
        <p style="color:#44118C;font-size:12px;font-family:Arial,sans-serif;letter-spacing:1px;margin:24px 0 0;">
          You have up to 3 free revisions included with your order.
        </p>
        """
        send_email(
            customer.email,
            f'Your Mockup is Ready \u2756 Order #{order_num}',
            _email_wrap('Your Mockup is Ready', 'Action Required', _mockup_body)
        )

    return jsonify({'mockup': mockup.to_dict()}), 201


@app.route('/api/mockups/<int:mockup_id>/approve', methods=['POST'])
@require_auth
def approve_mockup(mockup_id):
    mockup = Mockup.query.get_or_404(mockup_id)
    order  = Order.query.get_or_404(mockup.order_id)
    if request.user_role == 'customer' and order.user_id != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403
    data     = request.get_json()
    approved = data.get('approved', False)
    notes    = data.get('notes', '')
    mockup.approved = approved
    if approved:
        mockup.approval_at = datetime.datetime.utcnow()
    else:
        existing_count  = Revision.query.filter_by(order_id=mockup.order_id).count()
        revision_number = existing_count + 1
        charge_amount   = 0 if revision_number <= 3 else 20.00
        revision = Revision(
            order_id=mockup.order_id, mockup_id=mockup_id,
            revision_number=revision_number,
            notes=notes or 'Customer requested changes',
            charge_amount=charge_amount,
        )
        db.session.add(revision)
    db.session.commit()
    # Notify all admins of customer's decision
    customer = User.query.get(order.user_id)
    order_num = order.order_number or str(order.id)
    admin_users = User.query.filter(User.role.in_(['owner', 'employee'])).all()
    if approved:
        _approval_body = f"""
        <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.8;margin:0 0 28px;">
          Great news — the customer has approved their mockup for order #{order_num}.
          This order is ready to move into production.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
          {_info_row('Order', f'#{order_num}')}
          {_info_row('Customer', customer.name if customer else '&mdash;')}
          {_info_row('Decision', 'Approved ✅', highlight=True)}
        </table>
        {_primary_button('View Order', PORTAL_URL)}
        """
        for admin in admin_users:
            send_email(
                admin.email,
                f'[Mockup Approved] Order #{order_num} — Ready for Production',
                _email_wrap('Mockup Approved', f'Order #{order_num}', _approval_body, accent_color='#D8BC84')
            )
    else:
        _revision_body = f"""
        <p style="color:#858488;font-size:15px;font-family:Georgia,serif;line-height:1.8;margin:0 0 28px;">
          The customer has requested changes to their mockup for order #{order_num}.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
          {_info_row('Order', f'#{order_num}')}
          {_info_row('Customer', customer.name if customer else '&mdash;')}
          {_info_row('Decision', 'Changes Requested', highlight=True)}
          {_info_row('Notes', notes or 'No notes provided')}
        </table>
        {_primary_button('View Order', PORTAL_URL)}
        """
        for admin in admin_users:
            send_email(
                admin.email,
                f'[Revision Requested] Order #{order_num} — Customer Wants Changes',
                _email_wrap('Revision Requested', f'Order #{order_num}', _revision_body, accent_color='#F217A5')
            )
    
    return jsonify({
        'mockup': mockup.to_dict(), 'approved': approved,
        'message': 'Mockup approved!' if approved else 'Changes requested — Buffy has been notified.',
    })

# ============================================================
# API: HOW IT WORKS STEPS
# ============================================================

@app.route('/api/how-it-works', methods=['GET'])
def get_how_it_works():
    try:
        steps = HowItWorksStep.query.order_by(HowItWorksStep.sort_order, HowItWorksStep.id).all()
        return jsonify([s.to_dict() for s in steps])
    except Exception:
        return jsonify([])


@app.route('/api/how-it-works', methods=['POST'])
@require_admin
def create_how_it_works():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': 'title required'}), 400
    step = HowItWorksStep(
        step_number=data.get('step_number', 1),
        title=data['title'].strip(),
        description=data.get('description', '').strip(),
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True),
    )
    db.session.add(step)
    db.session.commit()
    return jsonify(step.to_dict()), 201


@app.route('/api/how-it-works/<int:step_id>', methods=['PATCH'])
@require_admin
def update_how_it_works(step_id):
    step = HowItWorksStep.query.get_or_404(step_id)
    data = request.get_json()
    if 'step_number' in data: step.step_number = data['step_number']
    if 'title'       in data: step.title       = data['title'].strip()
    if 'description' in data: step.description = data['description'].strip()
    if 'sort_order'  in data: step.sort_order  = data['sort_order']
    if 'is_active'   in data: step.is_active   = data['is_active']
    db.session.commit()
    return jsonify(step.to_dict())


@app.route('/api/how-it-works/<int:step_id>', methods=['DELETE'])
@require_admin
def delete_how_it_works(step_id):
    step = HowItWorksStep.query.get_or_404(step_id)
    db.session.delete(step)
    db.session.commit()
    return jsonify({'deleted': step_id})

# ============================================================
# API: CUSTOM ITEMS & PRICING TIERS
# ============================================================

@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        items = CustomItem.query.filter_by(is_active=True).order_by(CustomItem.sort_order, CustomItem.id).all()
        return jsonify([i.to_dict() for i in items])
    except Exception:
        return jsonify([])


@app.route('/api/items/all', methods=['GET'])
@require_admin
def get_all_items():
    try:
        items = CustomItem.query.order_by(CustomItem.sort_order, CustomItem.id).all()
        return jsonify([i.to_dict() for i in items])
    except Exception:
        return jsonify([])


@app.route('/api/items', methods=['POST'])
@require_admin
def create_item():
    data = request.get_json()
    if not data or not data.get('label'):
        return jsonify({'error': 'label required'}), 400
    item = CustomItem(
        icon=data.get('icon', '✨').strip(),
        label=data['label'].strip(),
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route('/api/items/<int:item_id>', methods=['PATCH'])
@require_admin
def update_item(item_id):
    item = CustomItem.query.get_or_404(item_id)
    data = request.get_json()
    if 'icon'       in data: item.icon       = data['icon'].strip()
    if 'label'      in data: item.label      = data['label'].strip()
    if 'sort_order' in data: item.sort_order = data['sort_order']
    if 'is_active'  in data: item.is_active  = data['is_active']
    db.session.commit()
    return jsonify(item.to_dict())


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
@require_admin
def delete_item(item_id):
    item = CustomItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'deleted': item_id})


@app.route('/api/items/<int:item_id>/tiers', methods=['POST'])
@require_admin
def create_item_tier(item_id):
    CustomItem.query.get_or_404(item_id)
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name required'}), 400
    tier = ItemPricingTier(
        item_id=item_id,
        name=data['name'].strip(),
        price_label=data.get('price_label', '').strip(),
        description=data.get('description', '').strip(),
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True),
    )
    db.session.add(tier)
    db.session.commit()
    return jsonify(tier.to_dict()), 201


@app.route('/api/items/<int:item_id>/tiers/<int:tier_id>', methods=['PATCH'])
@require_admin
def update_item_tier(item_id, tier_id):
    tier = ItemPricingTier.query.filter_by(id=tier_id, item_id=item_id).first_or_404()
    data = request.get_json()
    if 'name'        in data: tier.name        = data['name'].strip()
    if 'price_label' in data: tier.price_label = data['price_label'].strip()
    if 'description' in data: tier.description = data['description'].strip()
    if 'sort_order'  in data: tier.sort_order  = data['sort_order']
    if 'is_active'   in data: tier.is_active   = data['is_active']
    db.session.commit()
    return jsonify(tier.to_dict())


@app.route('/api/items/<int:item_id>/tiers/<int:tier_id>', methods=['DELETE'])
@require_admin
def delete_item_tier(item_id, tier_id):
    tier = ItemPricingTier.query.filter_by(id=tier_id, item_id=item_id).first_or_404()
    db.session.delete(tier)
    db.session.commit()
    return jsonify({'deleted': tier_id})

# ============================================================
# APP ENTRY POINT
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
