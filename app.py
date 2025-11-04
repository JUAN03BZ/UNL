from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os

# Configuración de MySQL
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Contraseña2025')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/ecoa'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# === MODELOS ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    light = db.Column(db.String(20))
    time = db.Column(db.String(20))
    space = db.Column(db.String(20))
    has_pets = db.Column(db.Boolean)
    style = db.Column(db.String(20))
    recommended_plant = db.Column(db.String(100))

# === PRODUCTOS (simulados por ahora) ===
PRODUCTS = [
    {
        'id': 1,
        'name': 'Mata Equitable Eco',
        'price': 25.99,
        'image': 'hero1.png',
        'description': 'Mata sostenible hecha con materiales 100% naturales.',
        'features': ['Color Natural', 'Biodegradable', 'Fácil de cultivar']
    },
    {
        'id': 2,
        'name': 'Mata Colgante Eco',
        'price': 29.99,
        'image': 'hero2.png',
        'description': 'Perfecta para balcones. Diseño colgante con cuerda natural.',
        'features': ['Colgante', 'Resistente al clima', 'Estilo rústico']
    },
    {
        'id': 3,
        'name': 'Mata Mini Eco',
        'price': 18.50,
        'image': 'hero3.png',
        'description': 'Ideal para escritorios. Pequeña pero llena de vida.',
        'features': ['Compacta', 'Ideal para principiantes', 'Decorativa']
    }
]


# === FUNCIÓN DE RECOMENDACIÓN ===
def recommend_plant(light, time, space, has_pets, style):
    plants = [
        {
            "name": "Sansevieria (Lengua de suegra)",
            "light": "baja",
            "time": "poco",
            "space": ["pequeño", "mediano"],
            "pets_safe": True,
            "style": ["minimalista"],
            "image": "sansevieria.jpg"
        },
        {
            "name": "Pothos Dorado",
            "light": "media",
            "time": "moderado",
            "space": ["pequeño"],
            "pets_safe": False,
            "style": ["colgante"],
            "image": "pothos.jpg"
        },
        {
            "name": "Orquídea Phalaenopsis",
            "light": "alta",
            "time": "moderado",
            "space": ["pequeño"],
            "pets_safe": True,
            "style": ["flores"],
            "image": "orquidea.jpg"
        },
        {
            "name": "Helecho de Boston",
            "light": "media",
            "time": "mucho",
            "space": ["mediano"],
            "pets_safe": True,
            "style": ["tropical"],
            "image": "helecho.jpg"
        }
    ]

    candidates = []
    for plant in plants:
        if plant["light"] != light:
            continue
        if plant["time"] != time:
            continue
        if space not in plant["space"]:
            continue
        if has_pets and not plant["pets_safe"]:
            continue
        if style not in plant["style"]:
            continue
        candidates.append(plant)

    if candidates:
        return candidates[0]
    else:
        return {
            "name": "Sansevieria",
            "light": "baja",
            "time": "poco",
            "space": ["pequeño", "mediano"],
            "pets_safe": True,
            "style": ["minimalista"],
            "image": "sansevieria.jpg"
        }

# === RUTAS ===

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    return render_template('products.html', products=PRODUCTS)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        flash("Producto no encontrado.")
        return redirect(url_for('products'))
    return render_template('product_detail.html', product=product)

@app.route('/acerca')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Las contraseñas no coinciden.")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("El correo ya está registrado.")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("¡Registro exitoso! Ahora puedes iniciar sesión.")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f"¡Bienvenido, {user.name}!")
            return redirect(url_for('index'))
        else:
            flash("Correo o contraseña incorrectos.")
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión.")
    return redirect(url_for('index'))

# Carrito (usando sesión)
@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para agregar productos al carrito.', 'warning')
        return redirect(url_for('login'))

    # Buscar el producto real en PRODUCTS
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        flash("Producto no disponible.")
        return redirect(url_for('products'))

    cart = session.get('cart', [])
    existing = next((item for item in cart if item['id'] == product_id), None)

    if existing:
        existing['quantity'] += 1
    else:
        cart.append({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'image': product['image'],  # ← ¡OBLIGATORIO!
            'quantity': 1
        })

    session['cart'] = cart
    flash(f"{product['name']} agregado al carrito.", 'success')
    return redirect(url_for('products'))

# Añadir esta ruta en app.py
@app.route('/update_cart/<int:item_index>', methods=['POST'])
def update_cart(item_index):
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        new_quantity = request.form.get('quantity', type=int)
        if new_quantity and new_quantity > 0:
            cart[item_index]['quantity'] = new_quantity
        else:
            cart.pop(item_index)  # Si la cantidad es 0 o menor, eliminar
    session['cart'] = cart
    return redirect(url_for('cart'))

# Asegúrate de tener también la ruta para eliminar
@app.route('/remove_from_cart/<int:item_index>')
def remove_from_cart(item_index):
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        removed = cart.pop(item_index)
        session['cart'] = cart
        flash(f"{removed['name']} eliminado del carrito.")
    return redirect(url_for('cart'))

@app.route('/update_quantity/<int:item_index>', methods=['POST'])
def update_quantity(item_index):
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        new_quantity = request.form.get('quantity', type=int)
        if new_quantity and new_quantity > 0:
            cart[item_index]['quantity'] = new_quantity
            session['cart'] = cart
            # Recalculamos el total
            total = sum(item['price'] * item['quantity'] for item in cart)
            return jsonify({
                'success': True,
                'new_quantity': new_quantity,
                'new_total': f"${total:.2f}",
                'item_subtotal': f"${cart[item_index]['price'] * new_quantity:.2f}"
            })
        elif new_quantity == 0:
            removed_item = cart.pop(item_index)
            session['cart'] = cart
            # Recalculamos el total
            total = sum(item['price'] * item['quantity'] for item in cart)
            return jsonify({
                'success': True,
                'removed': True,
                'new_total': f"${total:.2f}",
                'message': f"{removed_item['name']} eliminado del carrito."
            })
    return jsonify({'success': False}), 400
# === TU PLANTA PERFECTA ===
@app.route('/mi-planta-perfecta', methods=['GET', 'POST'])
def perfect_plant():
    if 'user_id' not in session:
        flash("Debes iniciar sesión para acceder a esta función.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        light = request.form['light']
        time = request.form['time']
        space = request.form['space']
        has_pets = request.form.get('pets') == 'si'
        style = request.form['style']

        plant = recommend_plant(light, time, space, has_pets, style)

        # Opcional: guardar en base de datos
        profile = UserProfile.query.filter_by(user_id=session['user_id']).first()
        if profile:
            profile.light = light
            profile.time = time
            profile.space = space
            profile.has_pets = has_pets
            profile.style = style
            profile.recommended_plant = plant['name']
        else:
            profile = UserProfile(
                user_id=session['user_id'],
                light=light,
                time=time,
                space=space,
                has_pets=has_pets,
                style=style,
                recommended_plant=plant['name']
            )
            db.session.add(profile)
        db.session.commit()

        return render_template('perfect_plant.html', plant=plant)

    # Si ya tiene perfil, mostrar recomendación guardada (opcional)
    return render_template('plant_quiz.html')

# Checkout simulado
@app.route('/checkout')
def checkout():
    if not session.get('cart'):
        flash("Tu carrito está vacío.")
        return redirect(url_for('cart'))
    total = sum(item['price'] * item['quantity'] for item in session.get('cart', []))
    return render_template('checkout.html', total=total)

# === Crear tablas al iniciar (solo en desarrollo) ===
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)