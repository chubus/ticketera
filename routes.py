@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("panel"))
    return redirect(url_for("login"))
from flask import request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask import current_app as app
from db_init import db
from flask_login import login_manager
from flask_socketio import SocketIO
socketio = SocketIO(app)
from models import User, Ticket
from flask_socketio import emit
from werkzeug.security import generate_password_hash, check_password_hash
import json

## El user_loader ya está registrado en app.py

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("panel"))
        flash("Credenciales incorrectas", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/panel")
@login_required
def panel():
    if current_user.role == "admin":
        tickets = Ticket.query.all()
        return render_template("admin_panel.html", tickets=tickets)
    elif current_user.role == "flota":
        tickets = Ticket.query.filter_by(asignado_a=current_user.id).all()
        return render_template("flota_panel.html", tickets=tickets)
    else:
        return "Acceso no permitido", 403

@app.route("/api/tickets", methods=["POST"])
def recibir_ticket():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos no recibidos'}), 400
    ticket = Ticket(
        numero=data.get('numero'),
        cliente_nombre=data.get('cliente_nombre'),
        cliente_direccion=data.get('cliente_direccion'),
        cliente_telefono=data.get('cliente_telefono'),
        cliente_email=data.get('cliente_email'),
        productos=json.dumps(data.get('productos', [])),
        estado='pendiente',
        prioridad=data.get('prioridad', 'normal'),
        indicaciones=data.get('indicaciones', '')
    )
    db.session.add(ticket)
    db.session.commit()
    socketio.emit('nuevo_ticket', {'ticket_id': ticket.id, 'numero': ticket.numero})
    return jsonify({'exito': True, 'ticket_id': ticket.id})
