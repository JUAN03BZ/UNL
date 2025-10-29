from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os

# Configuración inicial
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Contraseña2025')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/ecoa'  # tu base de datos XAMPP
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ======= MODELO DE USUARIO =======
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


# ======= FUNCIONES DE APOYO =======
def get_cart_count():
    return len(session.get("cart_items", []))


# ======= RUTAS =======
@app.route("/")
def index():
    return render_template("index.html", cart_count=get_cart_count())


@app.route("/materas")
def materas():
    productos = [
        {"id": 1, "nombre": "Ecoa Natural", "precio": 24.99, "imagen": "hero1.png"},
        {"id": 2, "nombre": "Ecoa Verde Bosque", "precio": 27.99, "imagen": "hero2.png"},
        {"id": 3, "nombre": "Ecoa Expandible XL", "precio": 32.99, "imagen": "hero3.png"},
    ]
    return render_template("materas.html", productos=productos, cart_count=get_cart_count())


@app.route("/about")
def about():
    return render_template("about.html", cart_count=get_cart_count())


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        mensaje = request.form.get("mensaje")
        flash("Gracias — tu mensaje fue enviado.", "success")
        return redirect(url_for("contacto"))
    return render_template("contacto.html", cart_count=get_cart_count())


# ======= CARRITO =======
# ======= CARRITO =======
@app.route("/add-to-cart/<int:producto_id>")
def add_to_cart(producto_id):
    productos = [
        {"id": 1, "nombre": "Ecoa Natural", "precio": 24.99, "imagen": "hero1.png"},
        {"id": 2, "nombre": "Ecoa Verde Bosque", "precio": 27.99, "imagen": "hero2.png"},
        {"id": 3, "nombre": "Ecoa Expandible XL", "precio": 32.99, "imagen": "hero3.png"},
    ]
    producto = next((p for p in productos if p["id"] == producto_id), None)
    if producto:
        cart = session.get("cart_items", {})

        # Si ya existe el producto, incrementa cantidad
        if str(producto_id) in cart:
            cart[str(producto_id)]["cantidad"] += 1
        else:
            cart[str(producto_id)] = {
                "id": producto["id"],
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "imagen": producto["imagen"],
                "cantidad": 1,
            }

        session["cart_items"] = cart
        session["cart_count"] = sum(item["cantidad"] for item in cart.values())
        flash(f"{producto['nombre']} agregado al carrito 🛒", "info")

    return redirect(url_for("materas"))


@app.route("/cart")
def cart():
    cart = session.get("cart_items", {})
    cart_items = list(cart.values())
    total = sum(item["precio"] * item["cantidad"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total, cart_count=sum(i['cantidad'] for i in cart_items))


@app.route("/remove-from-cart/<int:producto_id>")
def remove_from_cart(producto_id):
    cart = session.get("cart_items", {})
    if str(producto_id) in cart:
        del cart[str(producto_id)]
        session["cart_items"] = cart
        session["cart_count"] = sum(item["cantidad"] for item in cart.values())
        flash("Producto eliminado del carrito 🗑️", "info")
    return redirect(url_for("cart"))


# ======= REGISTRO Y LOGIN =======
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"], method="pbkdf2:sha256")

        if Usuario.query.filter_by(email=email).first():
            flash("Este correo ya está registrado.", "info")
            return redirect(url_for("register"))

        nuevo_usuario = Usuario(nombre=nombre, email=email, password=password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", cart_count=get_cart_count())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            # 👇 Guarda estos valores para que base.html los lea correctamente
            session["user_id"] = usuario.id
            session["username"] = usuario.nombre
            flash(f"Bienvenido, {usuario.nombre} 👋", "success")
            return redirect(url_for("index"))
        else:
            flash("Correo o contraseña incorrectos.", "info")
            return redirect(url_for("login"))

    return render_template("login.html", cart_count=get_cart_count())



@app.route("/logout")
def logout():
    session.clear()  # 🔥 Limpia toda la sesión (incluye carrito si quieres)
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("index"))



# ======= ERROR 404 =======
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# ======= EJECUCIÓN =======
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
