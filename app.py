from operator import or_
from sqlite3 import IntegrityError
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import BooleanField, StringField, PasswordField, SubmitField, SelectField, DateField, DecimalField, HiddenField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Regexp, Length, Email
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import date, time, timedelta,datetime
from decimal import Decimal
from werkzeug.utils import secure_filename
import os
from flask_session import Session
from wtforms import SelectMultipleField
from sqlalchemy import not_
from sqlalchemy import or_
from flask_wtf.file import FileField, FileAllowed, FileRequired
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

app = Flask(__name__)


app.config['SECRET_KEY'] = 'cambia_esto_por_un_secreto_fuerte'
# Configuración de sesión con expiración por inactividad
app.config['SESSION_TYPE'] = 'filesystem'  # o 'redis' si tenés Redis
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=2)  # 30 minutos de inactividad
ALLOWED_EXTENSIONS = {'pdf'}

# Inicializar Flask-Session
Session(app)

# Configuración (ponela al principio de app.py o en config)  
cloudinary.config( 
    cloud_name = "dnnpusoff", 
    api_key = "812463469552182", 
    api_secret = "ToQ7UAV-FLVLr33QZcYn0Wv4Z9Q", # Click 'View API Keys' above to copy your API secret
    secure=True
)

#En Render usar PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://lab_mv_db_8umv_user:63qIEDNC9hWIRxLqbMUxT7OiwkZa1CeZ@dpg-d5oga0e3jp1c73frhjr0-a.virginia-postgres.render.com/lab_mv_db_8umv?sslmode=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor iniciá sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

# ---------------- MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Refrescar sesión en cada request (extiende la vida útil si hay actividad)
@app.before_request
def refresh_session():
    if current_user.is_authenticated:
        session.permanent = True
        # Refrescar la expiración
        session.modified = True

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    clinica_particular = db.Column(db.String(150))
    provincia = db.Column(db.String(100), nullable=True)
    localidad = db.Column(db.String(100), nullable=True)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(50))
    cuit = db.Column(db.String(50))
    medio_pago = db.Column(db.String(100))

    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}".strip()

class TipoTrabajo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)

class TrabajoTipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False, unique=True)
    valor_arancel = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))

class Facturacion(db.Model):
    __tablename__ = 'facturacion'
    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), nullable=False, unique=True)
    fecha = db.Column(db.Date, nullable=False)
    destinatario = db.Column(db.String(150))
    importe = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    estado = db.Column(db.String(50), nullable=False, server_default='Facturado')
    archivo_pdf = db.Column(db.String(255), nullable=True)

    # Relación many-to-many con órdenes a través de FacturaDetalle
    detalles = db.relationship('FacturaDetalle', back_populates='factura', cascade="all, delete-orphan")


class OrdenTrabajo(db.Model):
    __tablename__ = 'orden_trabajo'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    doctor = db.relationship('Doctor', backref='ordenes')
    paciente = db.Column(db.String(200), nullable=False)
    tipo_trabajo_id = db.Column(db.Integer, db.ForeignKey('tipo_trabajo.id'), nullable=False)
    tipo_trabajo = db.relationship('TipoTrabajo', backref='ordenes')
    trabajo_id = db.Column(db.Integer, db.ForeignKey('trabajo_tipo.id'), nullable=False)
    trabajo = db.relationship('TrabajoTipo', backref='ordenes')
    maxilar = db.Column(db.String(50), nullable=False)
    detalle_piezas = db.Column(db.String(200))
    cant_piezas = db.Column(db.Integer, default=0)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_entrega = db.Column(db.Date, nullable=False)
    arancel = db.Column(db.Numeric(10, 2), nullable=False)
    indicaciones = db.Column(db.String(200))
    estado_orden = db.Column(db.String(50), default='INICIADO')

    # Relación many-to-many con facturas a través de FacturaDetalle
    detalles = db.relationship('FacturaDetalle', back_populates='orden', cascade="all, delete-orphan")
    
class FacturaDetalle(db.Model):
    __tablename__ = 'factura_detalle'
    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('facturacion.id'), nullable=False)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)  # Arancel de la orden

    factura = db.relationship('Facturacion', back_populates='detalles')
    orden = db.relationship('OrdenTrabajo', back_populates='detalles')

# ---------------- FORMS ----------------

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class DoctorForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    clinica_particular = StringField('Clínica / Particular')
    provincia = StringField('Provincia')
    localidad = StringField('Localidad')
    direccion = StringField('Dirección')
    telefono = StringField('Teléfono')
    cuit = StringField('Cuit')
    medio_pago = StringField('Medio de pago')
    submit = SubmitField('Guardar')

class TipoTrabajoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    submit = SubmitField('Guardar')

class TrabajoTipoForm(FlaskForm):
    nombre = StringField('Nombre Trabajo', validators=[DataRequired()])
    valor_arancel = DecimalField('Valor Arancel', places=2, default=Decimal('0.00'))
    submit = SubmitField('Guardar')

class FacturacionForm(FlaskForm):
    numero_factura = StringField('Número Factura', validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()])
    destinatario = StringField('Destinatario')
    ordenes = SelectMultipleField('Órdenes de Trabajo', coerce=int)  # Multiple
    importe = DecimalField('Importe', places=2, render_kw={"readonly": True})
    estado = SelectField('Estado', choices=[('Facturado', 'Facturado'), ('Pagado', 'Pagado')], validators=[DataRequired()])
    submit = SubmitField('Guardar')
    numero_factura = StringField('Número de Factura', validators=[DataRequired()])
    archivo_pdf = FileField('Factura Digital (PDF)', validators=[FileAllowed(['pdf'], 'Solo archivos PDF permitidos'),
        # FileRequired() si querés que sea obligatorio
    ])

class OrdenTrabajoForm(FlaskForm):
    doctor = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    paciente = StringField('Paciente', validators=[DataRequired()])
    tipo_trabajo = SelectField('Tipo Trabajo', coerce=int, validators=[DataRequired()])
    trabajo = SelectField('Trabajo', coerce=int, validators=[DataRequired()])
    maxilar = SelectField('Maxilar', choices=[('Inferior', 'Inferior'), ('Superior', 'Superior'), ('Ambos', 'Ambos')], validators=[DataRequired()])
    detalle_piezas = HiddenField('Detalle Piezas')
    cant_piezas = IntegerField('Cant. Piezas', render_kw={"readonly": True})
    fecha_inicio = DateField('Fecha Inicio', validators=[DataRequired()])
    fecha_entrega = DateField('Fecha Entrega', validators=[DataRequired()])  # CAMBIADO
    arancel = DecimalField('Arancel', places=2, render_kw={"readonly": True})
    indicaciones = TextAreaField('Indicaciones', validators=[Length(max=200)])
    estado_orden = SelectField('Estado Orden', choices=[('Iniciado', 'Iniciado'), ('En Proceso', 'En Proceso'), ('Entregado', 'Entregado'), ('Finalizado', 'Finalizado')], validators=[DataRequired()])
    submit = SubmitField('Guardar')

class UserForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$',
               message='La contraseña debe tener al menos 1 mayúscula, 1 número y 1 carácter especial')
    ])
    is_admin = BooleanField('Es Administrador')
    submit = SubmitField('Guardar')

# ---------------- ROUTES ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email_input = form.email.data.strip()
        user = User.query.filter(User.email.ilike(email_input)).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            # ¡Importante! remember=True + duración permanente
            login_user(user, remember=True, duration=timedelta(minutes=30))
            flash(f'¡Bienvenido, {user.nombre}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Email o contraseña incorrecta', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Tu sesión expiró por inactividad (30 minutos) o cerraste manualmente.', 'session_expired')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ---------------- DOCTORES ----------------

@app.route('/doctores')
@login_required
def doctores():
    
    query = Doctor.query
    doctores = query.order_by(Doctor.id.asc()).all()
    return render_template('doctores.html', doctores=doctores)

@app.route('/doctores/agregar', methods=['GET', 'POST'])
@login_required
def agregar_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        # Construimos el nombre completo manualmente (como en tu modelo)
        nombre = form.nombre.data.strip()
        apellido = form.apellido.data.strip()
        nombre_completo = f"{nombre} {apellido}"
        
        # Chequeamos si ya existe un doctor con ese nombre + apellido (case-insensitive)
        existente = Doctor.query.filter(
            func.lower(Doctor.nombre) == nombre.lower(),
            func.lower(Doctor.apellido) == apellido.lower()
        ).first()

        if existente:
            flash(f'El doctor "{nombre_completo}" ya existe. No se puede agregar duplicado.', 'danger')
            return render_template('doctor_form.html', form=form, titulo='Nuevo Doctor')
        
        nuevo_doctor = Doctor(
            nombre=nombre,
            apellido=apellido,
            clinica_particular=form.clinica_particular.data,
            provincia=form.provincia.data,
            localidad=form.localidad.data,
            direccion=form.direccion.data,
            telefono=form.telefono.data,
            cuit=form.cuit.data,
            medio_pago=form.medio_pago.data
        )
        db.session.add(nuevo_doctor)

        try:
            db.session.commit()
            flash('Doctor agregado correctamente!', 'success')
            return redirect(url_for('doctores'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe un doctor con ese nombre/apellido. No se pudo guardar.', 'danger')

    return render_template('doctor_form.html', form=form, titulo='Nuevo Doctor')

@app.route('/doctores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    form = DoctorForm(obj=doctor)

    if form.validate_on_submit():
        nuevo_nombre = form.nombre.data.strip()
        nuevo_apellido = form.apellido.data.strip()

        # Chequeamos si el nuevo nombre/apellido ya existe en OTRO doctor
        existente = Doctor.query.filter(
            func.lower(Doctor.nombre) == nuevo_nombre.lower(),
            func.lower(Doctor.apellido) == nuevo_apellido.lower(),
            Doctor.id != id
        ).first()

        if existente:
            flash(f'El nombre "{nuevo_nombre} {nuevo_apellido}" ya está en uso por otro doctor.', 'danger')
            return render_template('doctor_form.html', form=form, titulo='Editar Doctor')

        doctor.nombre = nuevo_nombre
        doctor.apellido = nuevo_apellido
        doctor.clinica_particular = form.clinica_particular.data
        doctor.provincia=form.provincia.data
        doctor.localidad=form.localidad.data
        doctor.direccion = form.direccion.data
        doctor.telefono = form.telefono.data
        doctor.cuit = form.cuit.data
        doctor.medio_pago = form.medio_pago.data

        try:
            db.session.commit()
            flash('Doctor actualizado correctamente!', 'success')
            return redirect(url_for('doctores'))
        except IntegrityError:
            db.session.rollback()
            flash('Error al guardar: nombre/apellido duplicado u otro problema.', 'danger')

    return render_template('doctor_form.html', form=form, titulo='Editar Doctor')

@app.route('/doctores/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    
    # Chequeamos si hay órdenes que usan este doctor
    if doctor.ordenes:  # asumiendo backref='ordenes' en la relación Doctor -> OrdenTrabajo
        flash(f'No se puede borrar este doctor porque está asociado a {len(doctor.ordenes)} órdenes.', 'danger')
        return redirect(url_for('doctores'))
    
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor borrado', 'success')
    return redirect(url_for('doctores'))

# ---------------- TIPOS DE TRABAJO ----------------

@app.route('/tipos_trabajo')
@login_required
def tipos_trabajo():
    
    query = TipoTrabajo.query
    tipos = query.order_by(TipoTrabajo.id.asc()).all()
    return render_template('tipos_trabajo.html', tipos=tipos)

@app.route('/tipos_trabajo/agregar', methods=['GET', 'POST'])
@login_required
def agregar_tipo_trabajo():
    form = TipoTrabajoForm()
    if form.validate_on_submit():
        
        existente = TipoTrabajo.query.filter(func.upper(TipoTrabajo.nombre) == func.upper(form.nombre.data)).first()
        if existente:
            flash('Ese nombre de Tipo de Trabajo ya existe. Elegí otro.', 'danger')
            return render_template('tipo_trabajo_form.html', form=form, titulo='Nuevo Tipo')

        nuevo = TipoTrabajo(nombre=form.nombre.data)
        db.session.add(nuevo)
        db.session.commit()
        flash('Tipo agregado', 'success')
        return redirect(url_for('tipos_trabajo'))
    return render_template('tipo_trabajo_form.html', form=form, titulo='Nuevo Tipo')

@app.route('/tipos_trabajo/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tipo_trabajo(id):
    tipo = TipoTrabajo.query.get_or_404(id)
    form = TipoTrabajoForm(obj=tipo)
    if form.validate_on_submit():
        tipo.nombre = form.nombre.data
        db.session.commit()
        flash('Tipo actualizado', 'success')
        return redirect(url_for('tipos_trabajo'))
    return render_template('tipo_trabajo_form.html', form=form, titulo='Editar Tipo')

@app.route('/tipos_trabajo/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_tipo_trabajo(id):
    tipo = TipoTrabajo.query.get_or_404(id)
    
    # Chequeamos si hay órdenes que usan este tipo
    if tipo.ordenes:  # asumiendo que tenés backref='ordenes' en la relación
        flash(f'No se puede borrar este tipo de trabajo porque está usado en {len(tipo.ordenes)} órdenes.', 'danger')
        return redirect(url_for('tipos_trabajo'))
    
    db.session.delete(tipo)
    db.session.commit()
    flash('Tipo borrado', 'success')
    return redirect(url_for('tipos_trabajo'))

# ---------------- TRABAJOS (CATÁLOGO) ----------------

@app.route('/trabajos')
@login_required
def trabajos():
    
    query = TrabajoTipo.query
    trabajos = query.order_by(TrabajoTipo.id.asc()).all()
    return render_template('trabajos.html', trabajos=trabajos)

@app.route('/trabajos/agregar', methods=['GET', 'POST'])
@login_required
def agregar_trabajo():
    form = TrabajoTipoForm()
    if form.validate_on_submit():
        existente = TrabajoTipo.query.filter(func.upper(TrabajoTipo.nombre) == func.upper(form.nombre.data)).first()
        if existente:
            flash('Ese nombre de Trabajo ya existe. Elegí otro.', 'danger')
            return render_template('trabajo_form.html', form=form, titulo='Nuevo Trabajo')

        nuevo = TrabajoTipo(
            nombre=form.nombre.data,
            valor_arancel=form.valor_arancel.data or Decimal('0.00')
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Trabajo agregado', 'success')
        return redirect(url_for('trabajos'))
    return render_template('trabajo_form.html', form=form, titulo='Nuevo Trabajo')

@app.route('/trabajos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_trabajo(id):
    trabajo = TrabajoTipo.query.get_or_404(id)
    form = TrabajoTipoForm(obj=trabajo)
    if form.validate_on_submit():
                      
        existente = TrabajoTipo.query.filter(func.upper(TrabajoTipo.nombre) == func.upper(form.nombre.data),TrabajoTipo.id != trabajo.id).first()
        if existente:
            flash(f'El nombre "{form.nombre.data}" ya está en uso por otro trabajo.', 'danger')
            return render_template('trabajo_form.html', form=form, titulo='Editar Trabajo')
        
        trabajo.nombre = form.nombre.data
        trabajo.valor_arancel = form.valor_arancel.data or Decimal('0.00')
        db.session.commit()
        flash('Trabajo actualizado', 'success')
        return redirect(url_for('trabajos'))
    return render_template('trabajo_form.html', form=form, titulo='Editar Trabajo')

@app.route('/trabajos/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_trabajo(id):
    trabajo = TrabajoTipo.query.get_or_404(id)
    
    # Chequeamos si hay órdenes que usan este trabajo
    if trabajo.ordenes:  # asumiendo backref='ordenes' en la relación
        flash(f'No se puede borrar este trabajo porque está usado en {len(trabajo.ordenes)} órdenes.', 'danger')
        return redirect(url_for('trabajos'))
    
    db.session.delete(trabajo)
    db.session.commit()
    flash('Trabajo borrado', 'success')
    return redirect(url_for('trabajos'))

# ---------------- FACTURACIÓN ----------------

@app.route('/facturacion')
@login_required
def facturacion():
    query = Facturacion.query

    # Filtros
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    destinatario = request.args.get('destinatario')
    estado = request.args.get('estado')
    clinica = request.args.get('clinica')  # NUEVO filtro por clinica_particular del doctor
    doctor_id = request.args.get('doctor_id')  # filtro por doctor

    if fecha_desde:
        query = query.filter(Facturacion.fecha >= date.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.filter(Facturacion.fecha <= date.fromisoformat(fecha_hasta))
    if destinatario:
        query = query.filter(Facturacion.destinatario.ilike(f"%{destinatario}%"))
    if estado:
        query = query.filter(Facturacion.estado== estado)
    if clinica:
            # Join múltiple: Facturacion → FacturaDetalle → OrdenTrabajo → Doctor
            query = query.join(FacturaDetalle, Facturacion.id == FacturaDetalle.factura_id)\
                        .join(OrdenTrabajo, FacturaDetalle.orden_id == OrdenTrabajo.id)\
                        .join(Doctor, OrdenTrabajo.doctor_id == Doctor.id)\
                        .filter(Doctor.clinica_particular.ilike(f"%{clinica}%"))\
                        .distinct()
    if doctor_id:
        query = query.join(FacturaDetalle).join(OrdenTrabajo).filter(
            OrdenTrabajo.doctor_id == int(doctor_id)
        ).distinct()

    facturas = query.order_by(Facturacion.numero_factura.asc()).all()

    # Totales
    total_importe = sum(f.importe for f in facturas)

    # Para los selects de filtros
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()

    return render_template('facturacion.html', facturas=facturas, total_importe=total_importe,
                           trabajos=trabajos, doctores=doctores)

@app.route('/facturacion/agregar', methods=['GET', 'POST'])
@login_required
def agregar_factura():
    form = FacturacionForm()
    
    # FILTROS (los mismos que en ordenes_trabajo)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    doctor_id = request.args.get('doctor_id')
    estado_orden = request.args.get('estado_orden')
    q = request.args.get('q')  # búsqueda rápida
    clinica = request.args.get('clinica')  # ← NUEVO
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    
    # Consulta base: solo órdenes sin factura
    query = OrdenTrabajo.query.filter(OrdenTrabajo.detalles == None)

    if fecha_desde:
        query = query.filter(OrdenTrabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(OrdenTrabajo.fecha_inicio <= fecha_hasta)
    if doctor_id:
        query = query.filter(OrdenTrabajo.doctor_id == doctor_id)
    if estado_orden:
        query = query.filter(OrdenTrabajo.estado_orden == estado_orden)
    if clinica:
        query = query.join(Doctor).filter(Doctor.clinica_particular.ilike(f"%{clinica}%"))
    if q:
        query = query.filter(
            or_(
                OrdenTrabajo.paciente.ilike(f"%{q}%"),
                OrdenTrabajo.detalle_piezas.ilike(f"%{q}%"),
                OrdenTrabajo.indicaciones.ilike(f"%{q}%")
            )
        )
        
    # Órdenes sin factura
    ordenes = query.filter(OrdenTrabajo.detalles == None).all()
    
    form.ordenes.choices = [
        (o.id, f"Orden {o.id} - {o.paciente} - Arancel ${o.arancel} - {o.trabajo.nombre} - Doctor {o.doctor.nombre_completo() if o.doctor else 'Sin doctor'}")
        for o in ordenes
    ]
    
    if form.validate_on_submit():
        existente = Facturacion.query.filter_by(numero_factura=form.numero_factura.data).first()
        if existente:
            flash('Ese número de factura ya existe. Elegí otro.', 'danger')
            return render_template('factura_form.html', form=form, titulo='Nueva Factura', ordenes=ordenes)
        
        nueva = Facturacion(
            numero_factura=form.numero_factura.data,
            fecha=form.fecha.data,
            destinatario=form.destinatario.data,
            estado=form.estado.data,
        )
        
    if 'archivo_pdf' in request.files and request.files['archivo_pdf'].filename != '':
        file = request.files['archivo_pdf']
        if file and file.filename.lower().endswith('.pdf'):
            try:
                # Nombre simple con timestamp para evitar conflictos
                timestamp = int(time.time())
                public_id = f"facturas/factura_{timestamp}"

                upload_result = cloudinary.uploader.upload(
                    file,
                    public_id=public_id,
                    folder="facturas",
                    resource_type="raw",
                    use_filename=True,
                    unique_filename=True,
                    overwrite=True
                )

                url = upload_result['secure_url']
                if not url.lower().endswith('.pdf'):
                    url += '.pdf'

                nueva.archivo_pdf = url
                print("PDF subido OK:", url)  # chequeá logs
            except Exception as e:
                flash(f'Error al subir PDF a Cloudinary: {str(e)}', 'danger')
                print("Cloudinary error:", str(e))
                return render_template('factura_form.html', form=form, titulo='Nueva Factura', ordenes=ordenes, doctores=doctores)
        else:
            flash('Solo se permiten archivos PDF.', 'danger')
            return render_template('factura_form.html', form=form, titulo='Nueva Factura', ordenes=ordenes, doctores=doctores)
                
        db.session.add(nueva)
        db.session.flush()
        
        total = Decimal('0.00')
        for orden_id in form.ordenes.data:
            orden = OrdenTrabajo.query.get(orden_id)
            detalle = FacturaDetalle(
                factura_id=nueva.id,
                orden_id=orden_id,
                subtotal=orden.arancel
            )
            db.session.add(detalle)
            total += orden.arancel
        
        nueva.importe = total
        db.session.commit()
        flash('Factura agregada con órdenes asociadas!', 'success')
        return redirect(url_for('facturacion'))
    
    return render_template('factura_form.html', form=form, titulo='Nueva Factura', ordenes=ordenes,doctores=doctores)

@app.route('/facturacion/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    factura = Facturacion.query.get_or_404(id)
    form = FacturacionForm(obj=factura)

    # FILTROS (los mismos que en agregar_factura)
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_entrega = request.args.get('fecha_entrega')
    doctor_id = request.args.get('doctor_id')
    estado_orden = request.args.get('estado_orden')
    estado_facturacion = request.args.get('estado_facturacion')
    clinica = request.args.get('clinica')
    q = request.args.get('q')

    # Órdenes disponibles: sin factura asociada O ya asociadas a esta factura
    query = OrdenTrabajo.query.filter(
        or_(
            OrdenTrabajo.detalles == None,
            OrdenTrabajo.detalles.any(FacturaDetalle.factura_id == id)
        )
    )

    if fecha_inicio:
        query = query.filter(OrdenTrabajo.fecha_inicio >= fecha_inicio)
    if fecha_entrega:
        query = query.filter(OrdenTrabajo.fecha_entrega <= fecha_entrega)
    if doctor_id:
        query = query.filter(OrdenTrabajo.doctor_id == doctor_id)
    if estado_orden:
        query = query.filter(OrdenTrabajo.estado_orden == estado_orden)
    if estado_facturacion:
        if estado_facturacion == 'Sin_Factura':
            query = query.filter(OrdenTrabajo.detalles == None)
        elif estado_facturacion in ['Facturado', 'Pagado']:
            query = query.join(FacturaDetalle).join(Facturacion).filter(Facturacion.estado == estado_facturacion).distinct()
    if clinica:
        query = query.join(Doctor).filter(Doctor.clinica_particular.ilike(f"%{clinica}%"))
    if q:
        query = query.filter(
            or_(
                OrdenTrabajo.paciente.ilike(f"%{q}%"),
                OrdenTrabajo.detalle_piezas.ilike(f"%{q}%"),
                OrdenTrabajo.indicaciones.ilike(f"%{q}%")
            )
        )

    ordenes_disponibles = query.all()

    form.ordenes.choices = [
        (o.id, f"Orden {o.id} - {o.paciente} - Arancel ${o.arancel} - {o.trabajo.nombre} - Doctor {o.doctor.nombre_completo() if o.doctor else 'Sin doctor'} - Clínica: {o.doctor.clinica_particular if o.doctor and o.doctor.clinica_particular else 'Sin clínica'}")
        for o in ordenes_disponibles
    ]

    if form.validate_on_submit():
        factura.numero_factura = form.numero_factura.data
        factura.fecha = form.fecha.data
        factura.destinatario = form.destinatario.data
        factura.estado = form.estado.data

        # 1. BORRAMOS TODOS LOS DETALLES VIEJOS de esta factura
        for detalle in factura.detalles:
            db.session.delete(detalle)

        # 2. CREAMOS SOLO LOS NUEVOS que seleccionaste
        total = Decimal('0.00')
        for orden_id in form.ordenes.data:
            orden = OrdenTrabajo.query.get(orden_id)
            detalle = FacturaDetalle(
                factura_id=factura.id,
                orden_id=orden_id,
                subtotal=orden.arancel
            )
            db.session.add(detalle)
            total += orden.arancel

        factura.importe = total
        
    if 'archivo_pdf' in request.files and request.files['archivo_pdf'].filename != '':
        file = request.files['archivo_pdf']
        if file and file.filename.lower().endswith('.pdf'):
            try:
                # Borrar viejo
                if factura.archivo_pdf:
                    public_id = factura.archivo_pdf.split('/')[-1].rsplit('.', 1)[0]
                    cloudinary.uploader.destroy(f"facturas/{public_id}", resource_type="raw")

                # Nuevo con timestamp
                timestamp = int(time.time())
                public_id = f"facturas/factura_{timestamp}"

                upload_result = cloudinary.uploader.upload(
                    file,
                    public_id=public_id,
                    folder="facturas",
                    resource_type="raw",
                    use_filename=True,
                    unique_filename=True,
                    overwrite=True
                )

                url = upload_result['secure_url']
                if not url.lower().endswith('.pdf'):
                    url += '.pdf'

                factura.archivo_pdf = url
            except Exception as e:
                flash(f'Error al subir PDF: {str(e)}', 'danger')
                return render_template('factura_form.html', form=form, titulo='Editar Factura', factura=factura, ordenes=ordenes_disponibles, doctores=doctores)
        else:
            flash('Solo se permiten archivos PDF.', 'danger')
            return render_template('factura_form.html', form=form, titulo='Editar Factura', factura=factura, ordenes=ordenes_disponibles, doctores=doctores)
                            
            db.session.commit()
            flash('Factura actualizada correctamente con las órdenes seleccionadas!', 'success')
            return redirect(url_for('facturacion'))

    # Preseleccionar las órdenes que ya estaban asociadas
    if request.method == 'GET':
        form.ordenes.data = [detalle.orden_id for detalle in factura.detalles]

    return render_template('factura_form.html', form=form, titulo='Editar Factura', ordenes=ordenes_disponibles, doctores=Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all(),factura=factura)

@app.route('/facturacion/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_factura(id):
    factura = Facturacion.query.get_or_404(id)
    # Chequeamos si tiene detalles (órdenes asociadas)
    if factura.detalles:  # si tiene al menos un detalle
        flash(f'No se puede borrar esta factura porque tiene {len(factura.detalles)} orden(es) asociada(s).', 'danger')
        return redirect(url_for('facturacion'))
    db.session.delete(factura)
    db.session.commit()
    flash('Factura borrada!', 'success')
    return redirect(url_for('facturacion'))

# ---------------- ÓRDENES DE TRABAJO ----------------

@app.route('/ordenes_trabajo')
@login_required
def ordenes_trabajo():
    query = OrdenTrabajo.query

    # Filtros existentes
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_entrega = request.args.get('fecha_entrega')
    doctor_id = request.args.get('doctor_id')
    estado_orden = request.args.get('estado_orden')
    q = request.args.get('q')
    estado_facturacion = request.args.get('estado_facturacion')  # NUEVO
    clinica = request.args.get('clinica')  # NUEVO filtro por clinica_particular

    if fecha_inicio:
        query = query.filter(OrdenTrabajo.fecha_inicio >= date.fromisoformat(fecha_inicio))
    if fecha_entrega:
        query = query.filter(OrdenTrabajo.fecha_entrega <= date.fromisoformat(fecha_entrega))
    if doctor_id:
        query = query.filter(OrdenTrabajo.doctor_id == int(doctor_id))
    if estado_orden:
        query = query.filter(OrdenTrabajo.estado_orden == estado_orden)
    if q:
        q = f"%{q}%"
        query = query.filter(
            (OrdenTrabajo.paciente.ilike(q)) |
            (OrdenTrabajo.indicaciones.ilike(q)) |
            (OrdenTrabajo.detalle_piezas.ilike(q))
        )

    # Filtro por Estado Facturación (esto faltaba)
    if estado_facturacion:
        if estado_facturacion == 'Sin_Factura':
            # Órdenes sin factura asociada
            query = query.filter(~OrdenTrabajo.detalles.any())
        else:
            # Órdenes con factura en ese estado
            query = query.join(FacturaDetalle).join(Facturacion).filter(
                Facturacion.estado == estado_facturacion
            ).distinct()

    if clinica:
            query = query.join(Doctor, OrdenTrabajo.doctor_id == Doctor.id).filter(
                Doctor.clinica_particular.ilike(f"%{clinica}%")
            )
       
    ordenes = query.order_by(OrdenTrabajo.id.asc()).all()

    # Totales
    total_piezas = sum(o.cant_piezas for o in ordenes)
    total_arancel = sum(o.arancel for o in ordenes)

    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()

    return render_template('ordenes_trabajo.html', ordenes=ordenes, doctores=doctores,
                           total_piezas=total_piezas, total_arancel=total_arancel)

@app.route('/ordenes_trabajo/agregar', methods=['GET', 'POST'])
@login_required
def agregar_orden_trabajo():
    form = OrdenTrabajoForm()
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    tipos_trabajo = TipoTrabajo.query.order_by(TipoTrabajo.nombre).all()
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    
    form.doctor.choices = [(d.id, d.nombre_completo()) for d in doctores]
    form.tipo_trabajo.choices = [(t.id, t.nombre) for t in tipos_trabajo]
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    
    if form.validate_on_submit():
        trabajo = TrabajoTipo.query.get(form.trabajo.data)
        nueva = OrdenTrabajo(
            doctor_id=form.doctor.data,
            paciente=form.paciente.data,
            tipo_trabajo_id=form.tipo_trabajo.data,
            trabajo_id=form.trabajo.data,
            maxilar=form.maxilar.data,
            detalle_piezas=form.detalle_piezas.data,
            cant_piezas=form.cant_piezas.data,
            fecha_inicio=form.fecha_inicio.data,
            fecha_entrega=form.fecha_entrega.data,  # CAMBIADO
            arancel=trabajo.valor_arancel,
            indicaciones=form.indicaciones.data,
            estado_orden=form.estado_orden.data
        )
        db.session.add(nueva)
        db.session.commit()
        flash('Orden agregada!', 'success')
        return redirect(url_for('ordenes_trabajo'))
    
    return render_template('orden_trabajo_form.html', form=form, titulo='Nueva Orden de Trabajo', doctores=doctores, tipos_trabajo=tipos_trabajo, trabajos=trabajos)

@app.route('/ordenes_trabajo/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_orden_trabajo(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    
    # 1. Cargar TODAS las opciones ANTES de crear el form (esto es lo que faltaba)
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    tipos_trabajo = TipoTrabajo.query.order_by(TipoTrabajo.nombre).all()
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    
    # 2. Crear el form con obj=orden (ahora ya tiene las choices listas)
    form = OrdenTrabajoForm(obj=orden)
    
    # 3. Asignar choices (ya puede preseleccionar correctamente)
    form.doctor.choices = [(d.id, d.nombre_completo()) for d in doctores]
    form.tipo_trabajo.choices = [(t.id, t.nombre) for t in tipos_trabajo]
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    
    if request.method == 'GET':
        form.doctor.data = orden.doctor_id
        form.tipo_trabajo.data = orden.tipo_trabajo_id
        form.trabajo.data = orden.trabajo_id
              
    if form.validate_on_submit():
        trabajo = TrabajoTipo.query.get(form.trabajo.data)
        
        orden.doctor_id = form.doctor.data
        orden.paciente = form.paciente.data
        orden.tipo_trabajo_id = form.tipo_trabajo.data
        orden.trabajo_id = form.trabajo.data
        orden.maxilar = form.maxilar.data
        orden.detalle_piezas = form.detalle_piezas.data
        orden.cant_piezas = form.cant_piezas.data
        orden.fecha_inicio = form.fecha_inicio.data
        orden.fecha_entrega = form.fecha_entrega.data
        orden.arancel = trabajo.valor_arancel
        orden.indicaciones = form.indicaciones.data
        orden.estado_orden = form.estado_orden.data
        
        db.session.commit()
        flash('Orden actualizada!', 'success')
        return redirect(url_for('ordenes_trabajo'))
    
    return render_template('orden_trabajo_form.html', form=form, titulo='Editar Orden de Trabajo',
                          doctores=doctores, tipos_trabajo=tipos_trabajo, trabajos=trabajos)
    
@app.route('/ordenes_trabajo/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_orden_trabajo(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    # Chequeamos si está asociada a alguna factura
    if orden.detalles:  # si tiene al menos un detalle en FacturaDetalle
        flash(f'No se puede borrar esta orden porque está asociada a {len(orden.detalles)} factura(s).', 'danger')
        return redirect(url_for('ordenes_trabajo'))
    db.session.delete(orden)
    db.session.commit()
    flash('Orden borrada', 'success')
    return redirect(url_for('ordenes_trabajo'))

# ---------------- USUARIOS ----------------

@app.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin:
        flash('No tenés permisos para acceder a esta sección.', 'danger')
        return redirect(url_for('index'))
    
    usuarios = User.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/agregar', methods=['GET', 'POST'])
@login_required
def agregar_usuario():
    if not current_user.is_admin:
        flash('No tenés permisos.', 'danger')
        return redirect(url_for('index'))
    
    form = UserForm()
    if form.validate_on_submit():
        nuevo = User(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            email=form.email.data.lower(),
            is_admin=form.is_admin.data
        )
        nuevo.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db.session.add(nuevo)
        db.session.commit()
        flash('Usuario agregado', 'success')
        return redirect(url_for('usuarios'))
    
    return render_template('usuario_form.html', form=form, titulo='Nuevo Usuario')

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if not current_user.is_admin:
        flash('No tenés permisos para editar usuarios.', 'danger')
        return redirect(url_for('index'))
    
    usuario = User.query.get_or_404(id)
    form = UserForm(obj=usuario)
    if form.validate_on_submit():
        usuario.nombre = form.nombre.data
        usuario.apellido = form.apellido.data
        usuario.email = form.email.data.lower()
        usuario.is_admin = form.is_admin.data
        if form.password.data:
            usuario.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db.session.commit()
        flash('Usuario actualizado', 'success')
        return redirect(url_for('usuarios'))
    
    return render_template('usuario_form.html', form=form, titulo='Editar Usuario')

@app.route('/usuarios/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_usuario(id):
    if not current_user.is_admin:
        flash('No tenés permisos para borrar usuarios.', 'danger')
        return redirect(url_for('index'))
    
    usuario = User.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No podés borrar tu propio usuario', 'danger')
        return redirect(url_for('usuarios'))
    
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario borrado', 'success')
    return redirect(url_for('usuarios'))

#------------------- TICKET ------------------#
@app.route('/orden/<int:id>/ticket')
@login_required
def orden_ticket(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    return render_template('orden_ticket.html', orden=orden)

# ---------------- CREACIÓN DE TABLAS Y USUARIOS ----------------

# Descomentá solo la primera vez para crear tablas y usuarios iniciales
with app.app_context():
     db.create_all()
     print("Tablas creadas o ya existían.")
     if User.query.count() == 0:
         print("Creando usuarios...")
         admin = User(nombre='Gabriel', apellido='Amaya', email='gfamaya@laboratoriomv.com', is_admin=True)
         admin.password_hash = bcrypt.generate_password_hash('@Gabriel14021987').decode('utf-8')
         usuario1 = User(nombre='Eliana', apellido='Maltempo', email='ebmaltempo@laboratoriomv.com')
         usuario1.password_hash = bcrypt.generate_password_hash('@Eliana05051989').decode('utf-8')
         usuario2 = User(nombre='Gisella', apellido='Vallejos', email='gvallejos@laboratoriomv.com')
         usuario2.password_hash = bcrypt.generate_password_hash('@Gisella1402').decode('utf-8')
         db.session.add_all([admin, usuario1, usuario2])
         db.session.commit()
         print("¡Usuarios creados correctamente!")

if __name__ == '__main__':
   port = int(os.environ.get("PORT", 5000))
   app.run(host="0.0.0.0", port=port, debug=False)  # debug=False en producción! 
