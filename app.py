from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

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

# === FUNCIÓN PARA GENERAR RECIBO JPG ===
def generate_receipt_jpg(order_data, cart_items, total_amount):
    try:
        # Crear imagen
        width, height = 600, 800
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Intentar cargar fuentes
        try:
            # En Windows
            title_font = ImageFont.truetype("arial.ttf", 24)
            header_font = ImageFont.truetype("arial.ttf", 18)
            normal_font = ImageFont.truetype("arial.ttf", 14)
            small_font = ImageFont.truetype("arial.ttf", 12)
        except:
            try:
                # En Linux/Mac
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
                normal_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                # Fuentes por defecto
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                normal_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        y_position = 30
        
        # Logo y título
        draw.text((width//2, y_position), "🌿 ECOA", fill=(95, 130, 102), font=title_font, anchor="mm")
        y_position += 40
        draw.text((width//2, y_position), "RECIBO DE COMPRA", fill=(0, 0, 0), font=header_font, anchor="mm")
        y_position += 40
        
        # Línea separadora
        draw.line([(50, y_position), (width-50, y_position)], fill=(200, 200, 200), width=2)
        y_position += 30
        
        # Información del pedido
        draw.text((50, y_position), f"Código: {order_data['order_code']}", fill=(0, 0, 0), font=normal_font)
        y_position += 25
        draw.text((50, y_position), f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", fill=(0, 0, 0), font=normal_font)
        y_position += 40
        
        # Información del cliente
        draw.text((50, y_position), "DATOS DEL CLIENTE", fill=(95, 130, 102), font=header_font)
        y_position += 30
        draw.text((50, y_position), f"Nombre: {order_data['customer']['fullname']}", fill=(0, 0, 0), font=normal_font)
        y_position += 25
        draw.text((50, y_position), f"Teléfono: {order_data['customer']['phone']}", fill=(0, 0, 0), font=normal_font)
        y_position += 25
        draw.text((50, y_position), f"Ciudad: {order_data['customer']['city']}", fill=(0, 0, 0), font=normal_font)
        
        if order_data['customer']['needsShipping'] and order_data['customer']['address']:
            y_position += 25
            draw.text((50, y_position), f"Dirección: {order_data['customer']['address']}", fill=(0, 0, 0), font=normal_font)
        
        y_position += 40
        
        # Productos
        draw.text((50, y_position), "PRODUCTOS", fill=(95, 130, 102), font=header_font)
        y_position += 30
        
        for item in cart_items:
            product_text = f"• {item['name']}"
            draw.text((50, y_position), product_text, fill=(0, 0, 0), font=normal_font)
            y_position += 20
            
            details_text = f"  Cantidad: {item['quantity']} x ${item['price']:.2f} = ${item['price'] * item['quantity']:.2f}"
            draw.text((50, y_position), details_text, fill=(100, 100, 100), font=small_font)
            y_position += 25
        
        y_position += 20
        
        # Totales
        draw.line([(50, y_position), (width-50, y_position)], fill=(200, 200, 200), width=1)
        y_position += 20
        
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        shipping = 5.00 if order_data['customer']['needsShipping'] else 0.00
        total = subtotal + shipping
        
        draw.text((50, y_position), f"Subtotal: ${subtotal:.2f}", fill=(0, 0, 0), font=normal_font)
        y_position += 25
        draw.text((50, y_position), f"Envío: ${shipping:.2f}", fill=(0, 0, 0), font=normal_font)
        y_position += 25
        
        draw.text((50, y_position), f"TOTAL: ${total:.2f}", fill=(95, 130, 102), font=header_font)
        y_position += 40
        
        # Mensaje final
        draw.text((width//2, y_position), "¡Gracias por tu compra!", fill=(95, 130, 102), font=header_font, anchor="mm")
        y_position += 30
        draw.text((width//2, y_position), "🌿 Ecoa - Materas Sostenibles", fill=(150, 150, 150), font=small_font, anchor="mm")
        
        # Guardar imagen en memoria
        img_io = io.BytesIO()
        image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        return img_io, f"recibo_{order_data['order_code']}.jpg"
        
    except Exception as e:
        print(f"Error generando recibo: {e}")
        raise e

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

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Obtener datos del formulario
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Aquí puedes agregar la lógica para enviar el email
        # o guardar en base de datos
        print(f"Mensaje recibido de: {name} ({email})")
        print(f"Asunto: {subject}")
        print(f"Mensaje: {message}")
        
        # Mostrar mensaje de éxito
        flash('¡Mensaje enviado correctamente! Te contactaremos pronto.', 'success')
        return redirect(url_for('contact'))
    
    # Si es GET, simplemente renderiza la página
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
            'image': product['image'],
            'quantity': 1
        })

    session['cart'] = cart
    flash(f"{product['name']} agregado al carrito.", 'success')
    return redirect(url_for('products'))

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

# Checkout
@app.route('/checkout')
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        return redirect(url_for('cart'))
    
    # Calcular totales
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    total = subtotal  # El envío se calcula en el frontend
    
    # Generar código de pedido único
    random_num = random.randint(10000, 99999)
    date_str = datetime.now().strftime('%d%m')
    order_code = f"ECOA-{random_num}-{date_str}"
    
    return render_template('checkout.html', 
                         cart_items=cart_items,
                         subtotal=subtotal,
                         total=total,
                         order_code=order_code)

# Descargar recibo - RUTA CORREGIDA
@app.route('/download_receipt', methods=['POST'])
def download_receipt():
    try:
        # Obtener datos del formulario
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
        
        order_data = {
            'order_code': order_code,
            'customer': customer_data
        }
        
        # Generar el recibo JPG
        img_io, filename = generate_receipt_jpg(order_data, cart_items, total_amount)
        
        # Devolver el archivo directamente
        return send_file(
            img_io,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error en download_receipt: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Ruta de prueba para recibos
@app.route('/test_receipt')
def test_receipt():
    """Ruta temporal para probar la generación de recibos"""
    try:
        # Crear imagen de prueba
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "TEST RECIBO ECOA", fill=(0, 0, 0))
        d.text((10, 40), "Si ves esto, Pillow funciona!", fill=(95, 130, 102))
        d.text((10, 70), f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", fill=(0, 0, 0))
        
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="test_recibo.jpg")
    except Exception as e:
        return f"Error: {str(e)}", 500

# === Crear tablas al iniciar (solo en desarrollo) ===
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Crear directorio de recibos si no existe
    os.makedirs('static/receipts', exist_ok=True)
    app.run(debug=True)