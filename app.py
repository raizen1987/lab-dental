from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap5
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import date
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField

app = Flask(__name__)
bootstrap = Bootstrap5(app)
app.config['SECRET_KEY'] = 'cambia_esta_clave_por_algo_muy_secreto_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trabajos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ========================
# MODELOS (actualizado)
# ========================

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(50))
    email = db.Column(db.String(120))
    matricula = db.Column(db.String(50))
    notas = db.Column(db.Text)

    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def __str__(self):
        return self.nombre_completo()

class Trabajo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)  # Relación
    doctor = db.relationship('Doctor', backref='trabajos')  # Para acceder fácil
    prosthesis = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(20), default='Pendiente')
    fecha_entrada = db.Column(db.Date, default=date.today)
    fecha_entrega = db.Column(db.Date)
    notas = db.Column(db.Text)

# ========================
# FORMULARIOS
# ========================

class TrabajoForm(FlaskForm):
    paciente = StringField('Paciente', validators=[DataRequired()])
    doctor = SelectField('Doctor / Dentista', coerce=int)  # coerce=int para que guarde el ID
    prosthesis = StringField('Tipo de Prótesis', validators=[DataRequired()])
    estado = SelectField('Estado', choices=['Pendiente', 'En proceso', 'Listo', 'Entregado'])
    fecha_entrega = DateField('Fecha Entrega')
    notas = TextAreaField('Notas')
    submit = SubmitField('Guardar')

class DoctorForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    telefono = StringField('Teléfono')
    email = StringField('Email')
    matricula = StringField('Matrícula')
    notas = TextAreaField('Notas')
    submit = SubmitField('Guardar')

# ========================
# RUTAS TRABAJOS
# ========================

@app.route('/')
def index():
    trabajos = Trabajo.query.all()
    return render_template('index.html', trabajos=trabajos)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    form = TrabajoForm()
    form.doctor.choices = [(0, 'Sin doctor asignado')] + [(d.id, d.nombre_completo()) for d in Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()]
    
    if form.validate_on_submit():
        nuevo = Trabajo(
            paciente=form.paciente.data,
            doctor_id=form.doctor.data if form.doctor.data != 0 else None,
            prosthesis=form.prosthesis.data,
            estado=form.estado.data,
            fecha_entrega=form.fecha_entrega.data,
            notas=form.notas.data
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Trabajo agregado!')
        return redirect(url_for('index'))
    return render_template('form.html', form=form, titulo='Nuevo Trabajo')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    trabajo = Trabajo.query.get_or_404(id)
    form = TrabajoForm(obj=trabajo)
    form.doctor.choices = [(0, 'Sin doctor asignado')] + [(d.id, d.nombre_completo()) for d in Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()]
    
    if form.validate_on_submit():
        trabajo.paciente = form.paciente.data
        trabajo.doctor_id = form.doctor.data if form.doctor.data != 0 else None
        trabajo.prosthesis = form.prosthesis.data
        trabajo.estado = form.estado.data
        trabajo.fecha_entrega = form.fecha_entrega.data
        trabajo.notas = form.notas.data
        db.session.commit()
        flash('Trabajo actualizado!')
        return redirect(url_for('index'))
    
    # Precargar el doctor actual
    if trabajo.doctor:
        form.doctor.data = trabajo.doctor.id
    else:
        form.doctor.data = 0
        
    return render_template('form.html', form=form, titulo='Editar Trabajo')

@app.route('/borrar/<int:id>', methods=['POST'])
def borrar(id):
    trabajo = Trabajo.query.get_or_404(id)
    db.session.delete(trabajo)
    db.session.commit()
    flash('Trabajo borrado!')
    return redirect(url_for('index'))

# ========================
# RUTAS DOCTORES
# ========================

@app.route('/doctores')
def doctores():
    doctores = Doctor.query.order_by(Doctor.apellido, Doctor.nombre).all()
    return render_template('doctores.html', doctores=doctores)

@app.route('/doctores/agregar', methods=['GET', 'POST'])
def agregar_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        nuevo = Doctor(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            telefono=form.telefono.data,
            email=form.email.data,
            matricula=form.matricula.data,
            notas=form.notas.data
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Doctor agregado correctamente!')
        return redirect(url_for('doctores'))
    return render_template('doctor_form.html', form=form, titulo='Nuevo Doctor')

@app.route('/doctores/editar/<int:id>', methods=['GET', 'POST'])
def editar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    form = DoctorForm(obj=doctor)
    if form.validate_on_submit():
        doctor.nombre = form.nombre.data
        doctor.apellido = form.apellido.data
        doctor.telefono = form.telefono.data
        doctor.email = form.email.data
        doctor.matricula = form.matricula.data
        doctor.notas = form.notas.data
        db.session.commit()
        flash('Doctor actualizado!')
        return redirect(url_for('doctores'))
    return render_template('doctor_form.html', form=form, titulo='Editar Doctor')

@app.route('/doctores/borrar/<int:id>', methods=['POST'])
def borrar_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor borrado!')
    return redirect(url_for('doctores'))

# ========================
# CREAR TABLAS Y CORRER APP
# ========================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))  # Render asigna PORT, si no usa 5000
    app.run(host='0.0.0.0', port=port, debug=False)  # host 0.0.0.0 para que sea accesible desde afuera
