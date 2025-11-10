from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
import joblib

# ================= CONFIGURACIÓN INICIAL =================
pymysql.install_as_MySQLdb()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Contraseña2025')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/ecoa'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================= CARGA DE MODELOS ML =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    model_plant = joblib.load(os.path.join(BASE_DIR, 'models', 'model_plant.pkl'))
    model_pot = joblib.load(os.path.join(BASE_DIR, 'models', 'model_pot.pkl'))
    encoders = joblib.load(os.path.join(BASE_DIR, 'models', 'encoders.pkl'))
    plant_encoder = joblib.load(os.path.join(BASE_DIR, 'models', 'plant_encoder.pkl'))
    pot_encoder = joblib.load(os.path.join(BASE_DIR, 'models', 'pot_encoder.pkl'))
    print("✅ Modelos ML cargados correctamente.")
except Exception as e:
    print(f"⚠️ No se pudieron cargar los modelos: {e}")
    model_plant = model_pot = encoders = plant_encoder = pot_encoder = None

def predict_ideal(data):
    if not all([model_plant, model_pot, encoders, plant_encoder, pot_encoder]):
        return "Error: Modelos no cargados", "Error"
    try:
        X_input = {}
        for col, val in data.items():
            X_input[col] = encoders[col].transform([val])[0]
        df_input = pd.DataFrame([X_input])
        plant_pred = plant_encoder.inverse_transform(model_plant.predict(df_input))[0]
        pot_pred = pot_encoder.inverse_transform(model_pot.predict(df_input))[0]
        return plant_pred, pot_pred
    except Exception as e:
        print("⚠️ Error en predicción:", e)
        return "Planta genérica", "Maceta Expandible Eco"

# ================= BASE DE DATOS =================
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

# ================= PRODUCTOS =================
PRODUCTS = [
    {'id': 1, 'name': 'Maceta Expandible Eco', 'price': 25.99, 'image': 'hero1.png',
     'description': 'Maceta sostenible hecha con materiales 100% naturales.',
     'features': ['Expandible', 'Biodegradable', 'Ideal para plantas que crecen']},
    {'id': 2, 'name': 'Maceta Colgante Eco', 'price': 29.99, 'image': 'hero2.png',
     'description': 'Perfecta para balcones. Diseño colgante con cuerda natural.',
     'features': ['Colgante', 'Resistente al clima', 'Decorativa']},
    {'id': 3, 'name': 'Maceta Mini Eco', 'price': 18.50, 'image': 'hero3.png',
     'description': 'Ideal para escritorios. Pequeña pero llena de vida.',
     'features': ['Compacta', 'Ideal para principiantes', 'Decorativa']}
]

# ================= FUNCIONES DE RECIBO =================
def generate_simple_receipt(order_data, cart_items, total_amount):
    width, height = 600, 800
    image = Image.new('RGB', (width, height), '#f8faf8')
    draw = ImageDraw.Draw(image)
    normal_font = ImageFont.load_default()
    bold_font = ImageFont.load_default()

    y = 30
    draw.rectangle([(0, 0), (width, 80)], fill='#5f8266')
    draw.text((width//2, 40), "🌿 ECOA", fill='white', font=bold_font, anchor="mm")
    y = 100

    draw.text((50, y), f"Código: {order_data['order_code']}", fill='#2c3e2f', font=bold_font)
    y += 30
    draw.text((50, y), f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", fill='#5d725f', font=normal_font)
    y += 50

    for item in cart_items:
        draw.text((50, y), f"• {item['name']} x{item['quantity']} = ${item['price'] * item['quantity']:.2f}", fill='#2c3e2f', font=normal_font)
        y += 25

    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    total = subtotal + (5 if order_data['customer']['needsShipping'] else 0)
    y += 20
    draw.text((50, y), f"TOTAL: ${total:.2f}", fill='#5f8266', font=bold_font)

    img_io = io.BytesIO()
    image.save(img_io, 'JPEG', quality=95)
    img_io.seek(0)
    return img_io, f"recibo_ecoa_{order_data['order_code']}.jpg"

# ================= RUTAS PRINCIPALES =================
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

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('¡Mensaje enviado correctamente! Te contactaremos pronto.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# ================= AUTH =================
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
        db.session.add(User(name=name, email=email, password=hashed_pw))
        db.session.commit()
        flash("¡Registro exitoso! Ahora puedes iniciar sesión.")
        return redirect(url_for('login'))
    return render_template('register.html')

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
        flash("Correo o contraseña incorrectos.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión.")
    return redirect(url_for('index'))

# ================= CARRITO =================
@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        flash("Producto no disponible.")
        return redirect(url_for('products'))

    cart = session.get('cart', [])
    existing = next((item for item in cart if item['id'] == product_id), None)
    if existing:
        existing['quantity'] += 1
    else:
        cart.append({'id': product['id'], 'name': product['name'], 'price': product['price'],
                     'image': product['image'], 'quantity': 1})
    session['cart'] = cart
    flash(f"{product['name']} agregado al carrito.", 'success')
    return redirect(url_for('products'))
@app.route('/remove_from_cart/<int:item_index>')
def remove_from_cart(item_index):
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        removed_item = cart.pop(item_index)
        session['cart'] = cart
        flash(f"{removed_item['name']} fue eliminado del carrito.", "info")
    else:
        flash("El producto no existe en el carrito.", "error")
    return redirect(url_for('cart'))


# ================= CHECKOUT =================
@app.route('/checkout')
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        return redirect(url_for('cart'))
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    total = subtotal
    order_code = f"ECOA-{random.randint(10000, 99999)}-{datetime.now().strftime('%d%m')}"
    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, order_code=order_code)

@app.route('/download_receipt', methods=['POST'])
def download_receipt():
    customer_data = {
        'fullname': request.form.get('fullname'),
        'phone': request.form.get('phone'),
        'city': request.form.get('city'),
        'address': request.form.get('address', ''),
        'needsShipping': request.form.get('needsShipping') == 'true',
        'instructions': request.form.get('instructions', '')
    }
    order_code = request.form.get('order_code')
    cart_items = session.get('cart', [])
    total_amount = request.form.get('total_amount')
    order_data = {'order_code': order_code, 'customer': customer_data}
    img_io, filename = generate_simple_receipt(order_data, cart_items, total_amount)
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name=filename)

# ================= QUIZ DE PLANTA PERFECTA =================
@app.route('/mi-planta-perfecta', methods=['GET', 'POST'])
def perfect_plant():
    if request.method == 'POST':
        data = {
            'espacio': request.form['espacio'],
            'luz': request.form['luz'],
            'tiempo_semanal': request.form['tiempo_semanal'],
            'experiencia': request.form['experiencia'],
            'preferencia_tipo': request.form['preferencia_tipo'],
            'mascotas': request.form['mascotas'],
            'bajo_mantenimiento': request.form['bajo_mantenimiento'],
            'pref_maceta': request.form['pref_maceta'],
            'riego_auto': request.form['riego_auto'],
            'presupuesto': request.form['presupuesto'],
            'clima': request.form['clima']
        }
        planta, maceta = predict_ideal(data)
        return render_template('perfect_plant.html', planta=planta, maceta=maceta)
    return render_template('plant_quiz.html')

# ================= INICIO DE APP =================
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    os.makedirs('static/receipts', exist_ok=True)
    app.run(debug=True)
