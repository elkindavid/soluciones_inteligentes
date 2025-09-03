from datetime import datetime
from flask_login import UserMixin
from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
            "is_admin": self.is_admin
        }
    
    
    # Método para asignar la contraseña
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Método para verificar la contraseña
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 👇 OFFLINE (SQLite) — MISMA TABLA, OTRO BIND
class LocalUser(UserMixin, db.Model):
    __tablename__ = "users"
    __bind_key__ = "local"         # <- clave
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class RegistroDestajo(db.Model):
    __tablename__ = "registros_destajo"
    id = db.Column(db.Integer, primary_key=True)
    empleado_documento = db.Column(db.String(50), nullable=False, index=True)
    empleado_nombre = db.Column(db.String(200), nullable=False)
    destajo_id = db.Column(db.Integer, nullable=False, index=True)
    cantidad = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sincronizado = db.Column(db.Boolean, default=False)
    last_sync = db.Column(db.DateTime)

    usuario = db.relationship('User', backref='destajos')

class GHDestajo(db.Model):
    __tablename__ = "GH_Destajos"
    Id = db.Column(db.Integer, primary_key=True)
    Planta = db.Column(db.String(200))
    Concepto = db.Column(db.String(200))
    Valor = db.Column(db.Float)

    def to_dict(self):
        return {
           "Id": self.Id,
           "Planta": self.Planta,
           "Concepto": self.Concepto,
           "Valor": self.Valor
        }
    
class GHEmpleado(db.Model):
    __tablename__ = "GH_Empleados"
    numeroDocumento = db.Column(db.String(50), primary_key=True)
    tipoIdentificacion = db.Column(db.String(50))
    nombreCompleto = db.Column(db.String(200))
    apellidoCompleto = db.Column(db.String(200))
    cargo = db.Column(db.String(200))
    centroCosto = db.Column(db.String(200))
    estado = db.Column(db.String(50))
    nombreNomina = db.Column(db.String(200))
    compania = db.Column(db.String(200))
    agrupador4 = db.Column(db.String(200))

    def to_dict(self):
        return {
           "numeroDocumento": self.numeroDocumento,
           "tipoIdentificacion": self.tipoIdentificacion,
           "nombreCompleto": self.nombreCompleto,
           "apellidoCompleto": self.apellidoCompleto,
           "cargo": self.cargo,
           "centroCosto": self.centroCosto,
           "estado": self.estado,
           "nombreNomina": self.nombreNomina,
           "compania": self.compania,
           "agrupador4": self.agrupador4
        }