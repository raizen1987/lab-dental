from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, PasswordField, SubmitField, SelectField, DateField, DecimalField, HiddenField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Regexp, Length, Email
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import date
from decimal import Decimal
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cambia_esto_por_un_secreto_fuerte'

#En Render usar PostgreSQL
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('postgresql://lab_mv_db_user:iLp2tARLiystvMKxVJHVV59UWQuB669M@dpg-d5ire89r0fns7388e8u0-a.virginia-postgres.render.com/lab_mv_db')

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

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    clinica_particular = db.Column(db.String(150))
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
    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), nullable=False, unique=True)
    fecha = db.Column(db.Date, nullable=False)
    destinatario = db.Column(db.String(150))
    trabajo_id = db.Column(db.Integer, db.ForeignKey('trabajo_tipo.id'), nullable=False)
    trabajo = db.relationship('TrabajoTipo', backref='facturas')
    importe = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(50), default='FACTURADO')
    paciente = db.Column(db.String(200))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    doctor = db.relationship('Doctor', backref='facturas')

class OrdenTrabajo(db.Model):
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
    fecha_entrega = db.Column(db.Date, nullable=False)  # CAMBIADO DE fecha_fin
    arancel = db.Column(db.Numeric(10, 2), nullable=False)
    indicaciones = db.Column(db.String(200))
    numero_factura_id = db.Column(db.Integer, db.ForeignKey('facturacion.id'))
    numero_factura = db.relationship('Facturacion', backref='ordenes')
    estado_pago = db.Column(db.String(50))
    estado_orden = db.Column(db.String(50), default='INICIADO')

# ---------------- FORMS ----------------

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class DoctorForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    clinica_particular = StringField('Clínica / Particular')
    direccion = StringField('Dirección')
    telefono = StringField('Teléfono')
    cuit = StringField('CUIT')
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
    numero_factura = StringField('Número Factura', validators=[DataRequired(), Regexp(r'^\d+$')])
    fecha = DateField('Fecha', validators=[DataRequired()])
    destinatario = StringField('Destinatario')
    trabajo = SelectField('Trabajo', coerce=int, validators=[DataRequired()])
    importe = DecimalField('Importe', places=2, render_kw={"readonly": True})
    estado = SelectField('Estado', choices=[('FACTURADO', 'Facturado'), ('PAGADO', 'Pagado')], validators=[DataRequired()])
    paciente = StringField('Paciente')
    doctor = SelectField('Doctor', coerce=int)
    submit = SubmitField('Guardar')

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
    numero_factura = SelectField('Número Factura', coerce=int)
    estado_pago = StringField('Estado Pago', render_kw={"readonly": True})
    estado_orden = SelectField('Estado Orden', choices=[('INICIADO', 'Iniciado'), ('EN PROCESO', 'En Proceso'), ('ENTREGADO', 'Entregado'), ('FINALIZADO', 'Finalizado')], validators=[DataRequired()])
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
            login_user(user, remember=True)
            flash(f'¡Bienvenido, {user.nombre}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Email o contraseña incorrecta', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ---------------- DOCTORES ----------------

@app.route('/doctores')
@login_required
def doctores():
    doctores = Doctor.query.all()
    return render_template('doctores.html', doctores=doctores)

@app.route('/doctores/agregar', methods=['GET', 'POST'])
@login_required
def agregar_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        nuevo = Doctor(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            clinica_particular=form.clinica_particular.data,
            direccion=form.direccion.data,
            telefono=form.telefono.data,
            cuit=form.cuit.data,
            medio_pago=form.medio_pago.data
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Doctor agregado', 'success')
        return redirect(url_for('doctores'))
    return render_template('doctor_form.html', form=form, titulo='Nuevo Doctor')

@app.route('/doctores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    form = DoctorForm(obj=doctor)
    if form.validate_on_submit():
        doctor.nombre = form.nombre.data
        doctor.apellido = form.apellido.data
        doctor.clinica_particular = form.clinica_particular.data
        doctor.direccion = form.direccion.data
        doctor.telefono = form.telefono.data
        doctor.cuit = form.cuit.data
        doctor.medio_pago = form.medio_pago.data
        db.session.commit()
        flash('Doctor actualizado', 'success')
        return redirect(url_for('doctores'))
    return render_template('doctor_form.html', form=form, titulo='Editar Doctor')

@app.route('/doctores/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor borrado', 'success')
    return redirect(url_for('doctores'))

# ---------------- TIPOS DE TRABAJO ----------------

@app.route('/tipos_trabajo')
@login_required
def tipos_trabajo():
    tipos = TipoTrabajo.query.all()
    return render_template('tipos_trabajo.html', tipos=tipos)

@app.route('/tipos_trabajo/agregar', methods=['GET', 'POST'])
@login_required
def agregar_tipo_trabajo():
    form = TipoTrabajoForm()
    if form.validate_on_submit():
        nuevo = TipoTrabajo(nombre=form.nombre.data.upper())
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
        tipo.nombre = form.nombre.data.upper()
        db.session.commit()
        flash('Tipo actualizado', 'success')
        return redirect(url_for('tipos_trabajo'))
    return render_template('tipo_trabajo_form.html', form=form, titulo='Editar Tipo')

@app.route('/tipos_trabajo/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_tipo_trabajo(id):
    tipo = TipoTrabajo.query.get_or_404(id)
    db.session.delete(tipo)
    db.session.commit()
    flash('Tipo borrado', 'success')
    return redirect(url_for('tipos_trabajo'))

# ---------------- TRABAJOS (CATÁLOGO) ----------------

@app.route('/trabajos')
@login_required
def trabajos():
    trabajos = TrabajoTipo.query.all()
    return render_template('trabajos.html', trabajos=trabajos)

@app.route('/trabajos/agregar', methods=['GET', 'POST'])
@login_required
def agregar_trabajo():
    form = TrabajoTipoForm()
    if form.validate_on_submit():
        nuevo = TrabajoTipo(
            nombre=form.nombre.data.upper(),
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
        trabajo.nombre = form.nombre.data.upper()
        trabajo.valor_arancel = form.valor_arancel.data or Decimal('0.00')
        db.session.commit()
        flash('Trabajo actualizado', 'success')
        return redirect(url_for('trabajos'))
    return render_template('trabajo_form.html', form=form, titulo='Editar Trabajo')

@app.route('/trabajos/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_trabajo(id):
    trabajo = TrabajoTipo.query.get_or_404(id)
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
    trabajo_id = request.args.get('trabajo_id')
    estado = request.args.get('estado')
    doctor_id = request.args.get('doctor_id')

    if fecha_desde:
        query = query.filter(Facturacion.fecha >= date.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.filter(Facturacion.fecha <= date.fromisoformat(fecha_hasta))
    if destinatario:
        query = query.filter(Facturacion.destinatario.ilike(f"%{destinatario}%"))
    if trabajo_id:
        query = query.filter(Facturacion.trabajo_id == int(trabajo_id))
    if estado:
        query = query.filter(Facturacion.estado == estado.upper())
    if doctor_id:
        query = query.filter(Facturacion.doctor_id == int(doctor_id))

    facturas = query.order_by(Facturacion.fecha.desc()).all()

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
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    form.doctor.choices = [(0, 'Sin doctor')] + [(d.id, d.nombre_completo()) for d in doctores]
    
    if form.validate_on_submit():
        # Chequear si el número de factura ya existe
        existente = Facturacion.query.filter_by(numero_factura=form.numero_factura.data).first()
        if existente:
            flash('Ese número de factura ya existe. Elegí otro.', 'danger')
            return render_template('factura_form.html', form=form, titulo='Nueva Factura', trabajos=trabajos, doctores=doctores)
        
        trabajo_seleccionado = TrabajoTipo.query.get(form.trabajo.data)
        nueva = Facturacion(
            numero_factura=form.numero_factura.data,
            fecha=form.fecha.data,
            destinatario=form.destinatario.data,
            trabajo_id=form.trabajo.data,
            importe=trabajo_seleccionado.valor_arancel,
            estado=form.estado.data.upper(),
            paciente=form.paciente.data,
            doctor_id=form.doctor.data if form.doctor.data != 0 else None
        )
        db.session.add(nueva)
        db.session.commit()
        flash('Factura agregada!', 'success')
        return redirect(url_for('facturacion'))
    
    return render_template('factura_form.html', form=form, titulo='Nueva Factura', trabajos=trabajos, doctores=doctores)

@app.route('/facturacion/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    factura = Facturacion.query.get_or_404(id)
    
    # 1. Cargar choices PRIMERO
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    
    # 2. Crear form VACÍO (sin obj todavía)
    form = FacturacionForm()
    
    # 3. Asignar choices INMEDIATAMENTE
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    form.doctor.choices = [(0, 'Sin doctor')] + [(d.id, d.nombre_completo()) for d in doctores]
    
    # 4. Ahora sí llenar manualmente los valores iniciales (esto fuerza la preselección)
    if request.method == 'GET':
        form.numero_factura.data = factura.numero_factura
        form.fecha.data = factura.fecha
        form.destinatario.data = factura.destinatario
        form.trabajo.data = factura.trabajo_id  # int
        form.importe.data = factura.importe
        form.estado.data = factura.estado
        form.paciente.data = factura.paciente
        form.doctor.data = factura.doctor_id if factura.doctor_id is not None else 0
    
    if form.validate_on_submit():
        trabajo_seleccionado = TrabajoTipo.query.get(form.trabajo.data)
        factura.numero_factura = form.numero_factura.data
        factura.fecha = form.fecha.data
        factura.destinatario = form.destinatario.data
        factura.trabajo_id = form.trabajo.data
        factura.importe = trabajo_seleccionado.valor_arancel
        factura.estado = form.estado.data.upper()
        factura.paciente = form.paciente.data
        factura.doctor_id = form.doctor.data if form.doctor.data != 0 else None
        
        db.session.commit()
        flash('Factura actualizada correctamente!', 'success')
        return redirect(url_for('facturacion'))
    
    return render_template('factura_form.html', form=form, titulo='Editar Factura', trabajos=trabajos, doctores=doctores)

@app.route('/facturacion/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_factura(id):
    factura = Facturacion.query.get_or_404(id)
    db.session.delete(factura)
    db.session.commit()
    flash('Factura borrada!', 'success')
    return redirect(url_for('facturacion'))

# ---------------- ÓRDENES DE TRABAJO ----------------

@app.route('/ordenes_trabajo')
@login_required
def ordenes_trabajo():
    query = OrdenTrabajo.query

    # Filtros
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_entrega = request.args.get('fecha_entrega')  # CAMBIADO
    doctor_id = request.args.get('doctor_id')
    estado_orden = request.args.get('estado_orden')
    estado_facturacion = request.args.get('estado_facturacion')
    q = request.args.get('q')

    if fecha_inicio:
        query = query.filter(OrdenTrabajo.fecha_inicio >= date.fromisoformat(fecha_inicio))
    if fecha_entrega:
        query = query.filter(OrdenTrabajo.fecha_entrega <= date.fromisoformat(fecha_entrega))
    if doctor_id:
        query = query.filter(OrdenTrabajo.doctor_id == int(doctor_id))
    if estado_orden:
        query = query.filter(OrdenTrabajo.estado_orden == estado_orden)
    if estado_facturacion:
        query = query.join(OrdenTrabajo.numero_factura).filter(Facturacion.estado == estado_facturacion)
    if q:
        q = f"%{q}%"
        query = query.filter(
            (OrdenTrabajo.paciente.ilike(q)) |
            (OrdenTrabajo.indicaciones.ilike(q)) |
            (OrdenTrabajo.detalle_piezas.ilike(q))
        )

    ordenes = query.order_by(OrdenTrabajo.fecha_inicio.desc()).all()

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
    facturas = Facturacion.query.order_by(Facturacion.fecha.desc()).all()
    
    form.doctor.choices = [(d.id, d.nombre_completo()) for d in doctores]
    form.tipo_trabajo.choices = [(t.id, t.nombre) for t in tipos_trabajo]
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    form.numero_factura.choices = [(0, 'Sin factura')] + [(f.id, f.numero_factura) for f in facturas]
    
    if form.validate_on_submit():
        trabajo = TrabajoTipo.query.get(form.trabajo.data)
        factura = Facturacion.query.get(form.numero_factura.data) if form.numero_factura.data != 0 else None
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
            numero_factura_id=form.numero_factura.data if form.numero_factura.data != 0 else None,
            estado_pago=factura.estado if factura else None,
            estado_orden=form.estado_orden.data
        )
        db.session.add(nueva)
        db.session.commit()
        flash('Orden agregada!', 'success')
        return redirect(url_for('ordenes_trabajo'))
    
    return render_template('orden_trabajo_form.html', form=form, titulo='Nueva Orden de Trabajo', doctores=doctores, tipos_trabajo=tipos_trabajo, trabajos=trabajos, facturas=facturas)

@app.route('/ordenes_trabajo/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_orden_trabajo(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    
    # 1. Cargar TODAS las opciones ANTES de crear el form (esto es lo que faltaba)
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    tipos_trabajo = TipoTrabajo.query.order_by(TipoTrabajo.nombre).all()
    trabajos = TrabajoTipo.query.order_by(TrabajoTipo.nombre).all()
    facturas = Facturacion.query.order_by(Facturacion.fecha.desc()).all()
    
    # 2. Crear el form con obj=orden (ahora ya tiene las choices listas)
    form = OrdenTrabajoForm(obj=orden)
    
    # 3. Asignar choices (ya puede preseleccionar correctamente)
    form.doctor.choices = [(d.id, d.nombre_completo()) for d in doctores]
    form.tipo_trabajo.choices = [(t.id, t.nombre) for t in tipos_trabajo]
    form.trabajo.choices = [(t.id, t.nombre) for t in trabajos]
    form.numero_factura.choices = [(0, 'Sin factura')] + [(f.id, f.numero_factura) for f in facturas]
    
    if request.method == 'GET':
        form.doctor.data = orden.doctor_id
        form.tipo_trabajo.data = orden.tipo_trabajo_id
        form.trabajo.data = orden.trabajo_id
        form.numero_factura.data = orden.numero_factura_id if orden.numero_factura_id else 0
    
    if form.validate_on_submit():
        trabajo = TrabajoTipo.query.get(form.trabajo.data)
        factura = Facturacion.query.get(form.numero_factura.data) if form.numero_factura.data != 0 else None
        
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
        orden.numero_factura_id = form.numero_factura.data if form.numero_factura.data != 0 else None
        orden.estado_pago = factura.estado if factura else None
        orden.estado_orden = form.estado_orden.data
        
        db.session.commit()
        flash('Orden actualizada!', 'success')
        return redirect(url_for('ordenes_trabajo'))
    
    return render_template('orden_trabajo_form.html', form=form, titulo='Editar Orden de Trabajo',
                          doctores=doctores, tipos_trabajo=tipos_trabajo, trabajos=trabajos, facturas=facturas)
    
@app.route('/ordenes_trabajo/borrar/<int:id>', methods=['POST'])
@login_required
def borrar_orden_trabajo(id):
    orden = OrdenTrabajo.query.get_or_404(id)
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
