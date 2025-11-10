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


# Permite usar PyMySQL como reemplazo de MySQLdb
pymysql.install_as_MySQLdb()

app = Flask(__name__)

# 🔐 Clave secreta
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Contraseña2025')

# 🌐 Configuración de base de datos
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # ✅ Asegura compatibilidad con MySQL usando PyMySQL
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
    # ✅ Asegura compatibilidad con PostgreSQL (si cambiaras de DB en Render)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # 🧩 Configuración local (modo desarrollo)
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/ecoa"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializa la base de datos
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
def generate_receipt_jpg(order_data, cart_items, total_amount):
    try:
        # Convertir total_amount a float si es string
        if isinstance(total_amount, str):
            total_amount = float(total_amount.replace('$', '').replace(',', '').strip())
        
        # Crear imagen con dimensiones similares al ejemplo
        width, height = 650, 1100  # Aumenté la altura para espacio adicional
        image = Image.new('RGB', (width, height), '#ffffff')
        draw = ImageDraw.Draw(image)
        
        # Intentar cargar fuentes - usar fuentes que soporten emojis
        try:
            # Intentar con fuentes que mejor soporten emojis
            title_font = ImageFont.truetype("arial.ttf", 28)
            header_font = ImageFont.truetype("arial.ttf", 20)
            normal_font = ImageFont.truetype("arial.ttf", 16)
            small_font = ImageFont.truetype("arial.ttf", 14)
            bold_font = ImageFont.truetype("arialbd.ttf", 18)
            
            # Fuente específica para emojis (si está disponible)
            try:
                emoji_font = ImageFont.truetype("seguiemj.ttf", 20)  # Windows
            except:
                try:
                    emoji_font = ImageFont.truetype("Apple Color Emoji.ttf", 20)  # macOS
                except:
                    try:
                        emoji_font = ImageFont.truetype("NotoColorEmoji.ttf", 20)  # Linux
                    except:
                        emoji_font = header_font  # Fallback a fuente normal
        except:
            # Fuentes por defecto
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            bold_font = ImageFont.load_default()
            emoji_font = ImageFont.load_default()

        y_position = 30
        
        # ===== ENCABEZADO CON FONDO VERDE =====
        header_height = 120
        draw.rectangle([(0, y_position), (width, y_position + header_height)], 
                      fill='#4a7c59', outline=None)
        
        # Logo y título principal - USAR EMOJI FONT PARA EMOJIS
        draw.text((width//2, y_position + 30), "🌿", fill='white', 
                 font=emoji_font, 
                 anchor="mm")
        draw.text((width//2, y_position + 70), "ECOA", fill='white', font=title_font, anchor="mm")
        draw.text((width//2, y_position + 100), "Materas Sostenibles", fill='#e8f4e8', font=small_font, anchor="mm")
        
        y_position += header_height + 20
        
        # ===== CÓDIGO DEL PEDIDO =====
        draw.text((width//2, y_position), f"Código: {order_data['order_code']}", 
                 fill='#333333', font=bold_font, anchor="mm")
        
        y_position += 40
        
        # Línea verde divisoria
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
        y_position += 20
        
        # ===== INFORMACIÓN DEL PEDIDO =====
        # Título de sección con fondo verde - USAR EMOJI
        section_height = 35
        draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        
        # Dibujar emoji y texto por separado para mejor compatibilidad
        draw.text((60, y_position + section_height//2), "📋", 
                 fill='white', font=emoji_font, anchor="lm")
        draw.text((width//2, y_position + section_height//2), "INFORMACIÓN DEL PEDIDO", 
                 fill='white', font=bold_font, anchor="mm")
        
        y_position += section_height + 15
        
        # Fecha
        draw.text((50, y_position), f"Fecha: {datetime.now().strftime('%d de %B de %Y, %I:%M %p').lower()}", 
                 fill='#333333', font=normal_font)
        y_position += 25
        
        # Cliente
        draw.text((50, y_position), f"Cliente: {order_data['customer']['fullname']}", 
                 fill='#333333', font=normal_font)
        y_position += 25
        
        # Teléfono
        draw.text((50, y_position), f"Teléfono: {order_data['customer']['phone']}", 
                 fill='#333333', font=normal_font)
        
        y_position += 30
        
        # Línea verde divisoria
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
        y_position += 20
        
        # ===== PRODUCTOS SOLICITADOS =====
        # Título de sección con fondo verde
        draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        
        draw.text((60, y_position + section_height//2), "🛒", 
                 fill='white', font=emoji_font, anchor="lm")
        draw.text((width//2, y_position + section_height//2), "PRODUCTOS SOLICITADOS", 
                 fill='white', font=bold_font, anchor="mm")
        
        y_position += section_height + 15
        
        # Lista de productos
        for item in cart_items:
            # Asegurarse de que price y quantity sean números
            price = float(item['price']) if isinstance(item['price'], str) else item['price']
            quantity = int(item['quantity']) if isinstance(item['quantity'], str) else item['quantity']
            
            # Nombre del producto con emoji si está disponible
            product_line = item['name']
            if 'emoji' in item and item['emoji']:
                # Dibujar emoji y texto por separado
                draw.text((50, y_position), item['emoji'], 
                         fill='#333333', font=emoji_font)
                draw.text((70, y_position), product_line, 
                         fill='#333333', font=normal_font)
            else:
                draw.text((50, y_position), f"• {product_line}", 
                         fill='#333333', font=normal_font)
            
            y_position += 20
            
            # Información de cantidad
            quantity_info = f"{quantity} unidad{'es' if quantity > 1 else ''}"
            if 'pack_info' in item:
                quantity_info = item['pack_info']
            
            draw.text((50, y_position), quantity_info, fill='#666666', font=small_font)
            
            # Precio alineado a la derecha
            draw.text((width - 50, y_position), f"${price * quantity:.2f}", 
                     fill='#333333', font=normal_font, anchor="rm")
            y_position += 25
        
        y_position += 10
        
        # Línea verde divisoria
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
        y_position += 20
        
        # ===== TOTALES =====
        # Título de sección con fondo verde
        draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        
        draw.text((60, y_position + section_height//2), "💰", 
                 fill='white', font=emoji_font, anchor="lm")
        draw.text((width//2, y_position + section_height//2), "TOTALES", 
                 fill='white', font=bold_font, anchor="mm")
        
        y_position += section_height + 15
        
        # Calcular subtotal asegurándose de que todos los valores sean números
        subtotal = 0
        for item in cart_items:
            price = float(item['price']) if isinstance(item['price'], str) else item['price']
            quantity = int(item['quantity']) if isinstance(item['quantity'], str) else item['quantity']
            subtotal += price * quantity
        
        shipping = 5.00 if order_data['customer']['needsShipping'] else 0.00
        total = subtotal + shipping
        
        # Subtotal
        draw.text((50, y_position), "Subtotal:", fill='#333333', font=normal_font)
        draw.text((width - 50, y_position), f"${subtotal:.2f}", 
                 fill='#333333', font=normal_font, anchor="rm")
        y_position += 25
        
        # Envío
        draw.text((50, y_position), "Envío:", fill='#333333', font=normal_font)
        draw.text((width - 50, y_position), f"${shipping:.2f}", 
                 fill='#333333', font=normal_font, anchor="rm")
        y_position += 25
        
        # Línea antes del total
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=1)
        y_position += 25
        
        # TOTAL
        draw.text((50, y_position), "TOTAL A PAGAR:", fill='#000000', font=bold_font)
        draw.text((width - 50, y_position), f"${total:.2f}", 
                 fill='#000000', font=bold_font, anchor="rm")
        
        y_position += 40
        
        # Línea verde divisoria
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
        y_position += 20
        
        # ===== INFORMACIÓN DE PAGO =====
        # Título de sección con fondo verde
        draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        
        draw.text((60, y_position + section_height//2), "💳", 
                 fill='white', font=emoji_font, anchor="lm")
        draw.text((width//2, y_position + section_height//2), "INFORMACIÓN DE PAGO", 
                 fill='white', font=bold_font, anchor="mm")
        
        y_position += section_height + 15
        
        # Método de pago
        payment_method = order_data.get('payment_method', 'Transferencia Bancaria')
        draw.text((50, y_position), f"Método: {payment_method}", fill='#333333', font=normal_font)
        y_position += 25
        
        # Número de cuenta (si está disponible)
        if 'account_number' in order_data:
            draw.text((50, y_position), f"Número: {order_data['account_number']}", 
                     fill='#333333', font=normal_font)
            y_position += 25
        
        # Referencia
        draw.text((50, y_position), f"Referencia: {order_data['order_code']}", 
                 fill='#333333', font=normal_font)
        y_position += 25
        
        # Instrucción adicional
        draw.text((50, y_position), "▲ Incluye el código en la descripción del pago", 
                 fill='#666666', font=small_font)
        
        y_position += 40
        
        # Línea verde divisoria
        draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
        y_position += 20
        
        # ===== INFORMACIÓN DE ENVÍO =====
        # Título de sección con fondo verde
        draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        
        draw.text((60, y_position + section_height//2), "🚚", 
                 fill='white', font=emoji_font, anchor="lm")
        draw.text((width//2, y_position + section_height//2), "INFORMACIÓN DE ENVÍO", 
                 fill='white', font=bold_font, anchor="mm")
        
        y_position += section_height + 15
        
        # Datos de envío - SIEMPRE mostrar dirección si existe
        draw.text((50, y_position), f"Destinatario: {order_data['customer']['fullname']}", 
                 fill='#333333', font=normal_font)
        y_position += 25
        
        draw.text((50, y_position), f"Teléfono: {order_data['customer']['phone']}", 
                 fill='#333333', font=normal_font)
        y_position += 25
        
        # MOSTRAR DIRECCIÓN SIEMPRE QUE EXISTA
        if order_data['customer'].get('address'):
            address = order_data['customer']['address']
            if len(address) > 50:
                parts = address.split(',')
                if len(parts) >= 2:
                    draw.text((50, y_position), f"Dirección: {parts[0].strip()}", 
                             fill='#333333', font=normal_font)
                    y_position += 20
                    draw.text((65, y_position), f"{','.join(parts[1:]).strip()}", 
                             fill='#333333', font=normal_font)
                    y_position += 25
                else:
                    words = address.split()
                    line1 = ' '.join(words[:len(words)//2])
                    line2 = ' '.join(words[len(words)//2:])
                    draw.text((50, y_position), f"Dirección: {line1}", 
                             fill='#333333', font=normal_font)
                    y_position += 20
                    draw.text((65, y_position), line2, 
                             fill='#333333', font=normal_font)
                    y_position += 25
            else:
                draw.text((50, y_position), f"Dirección: {address}", 
                         fill='#333333', font=normal_font)
                y_position += 25
        else:
            draw.text((50, y_position), "Dirección: No especificada", 
                     fill='#666666', font=normal_font)
            y_position += 25
        
        draw.text((50, y_position), f"Ciudad: {order_data['customer']['city']}", 
                 fill='#333333', font=normal_font)
        
        y_position += 25
        
        # ===== INSTRUCCIONES ADICIONALES (NUEVA SECCIÓN) =====
        if order_data['customer'].get('instructions'):
            y_position += 15
            
            # Línea verde divisoria
            draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
            y_position += 20
            
            # Título de sección con fondo verde
            draw.rectangle([(40, y_position), (width-40, y_position + section_height)], 
                          fill='#4a7c59', outline='#4a7c59', width=1)
            
            draw.text((60, y_position + section_height//2), "📝", 
                     fill='white', font=emoji_font, anchor="lm")
            draw.text((width//2, y_position + section_height//2), "INSTRUCCIONES ADICIONALES", 
                     fill='white', font=bold_font, anchor="mm")
            
            y_position += section_height + 15
            
            instructions = order_data['customer']['instructions']
            # Dividir instrucciones si son muy largas
            if len(instructions) > 80:
                # Dividir en líneas de máximo 80 caracteres
                words = instructions.split()
                lines = []
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= 80:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                    else:
                        lines.append(current_line)
                        current_line = word
                
                if current_line:
                    lines.append(current_line)
                
                # Dibujar cada línea
                for i, line in enumerate(lines):
                    if i == 0:
                        draw.text((50, y_position), f"• {line}", 
                                 fill='#333333', font=normal_font)
                    else:
                        draw.text((65, y_position), line, 
                                 fill='#333333', font=normal_font)
                    y_position += 20
            else:
                draw.text((50, y_position), f"• {instructions}", 
                         fill='#333333', font=normal_font)
                y_position += 25
        
        y_position += 40
        
        # ===== PIE DE PÁGINA CON FONDO VERDE =====
        footer_height = 60
        # Asegurar que el pie de página esté en la parte inferior
        if y_position < height - footer_height:
            draw.rectangle([(0, y_position), (width, height)], fill='#4a7c59', outline=None)
            
            draw.text((width//2, y_position + 20), "¡Gracias por elegir Ecoa!", 
                     fill='white', font=bold_font, anchor="mm")
            
            # Dibujar emoji de planeta por separado
            planet_x = width//2 + 150  # Posición después del texto
            draw.text((planet_x, y_position + 45), "🌍", 
                     fill='#e8f4e8', font=emoji_font, anchor="mm")
            draw.text((width//2, y_position + 45), "Tu compra ayuda a crear un planeta más verde", 
                     fill='#e8f4e8', font=small_font, anchor="mm")
        else:
            # Si hay mucho contenido, poner el pie de página al final
            draw.rectangle([(0, height - footer_height), (width, height)], fill='#4a7c59', outline=None)
            
            draw.text((width//2, height - footer_height + 20), "¡Gracias por elegir Ecoa!", 
                     fill='white', font=bold_font, anchor="mm")
            
            draw.text((width//2, height - footer_height + 45), "Tu compra ayuda a crear un planeta más verde 🌍", 
                     fill='#e8f4e8', font=small_font, anchor="mm")
        
        # Guardar imagen
        img_io = io.BytesIO()
        image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        return img_io, f"recibo_ecoa_{order_data['order_code']}.jpg"
        
    except Exception as e:
        print(f"Error generando recibo: {e}")
        # Versión alternativa sin emojis si hay problemas
        return generate_simple_receipt(order_data, cart_items, total_amount)

def generate_simple_receipt(order_data, cart_items, total_amount):
    """Versión simple SIN EMOJIS para máxima compatibilidad"""
    # Convertir total_amount a float si es string
    if isinstance(total_amount, str):
        total_amount = float(total_amount.replace('$', '').replace(',', '').strip())
    
    width, height = 600, 900  # Aumenté la altura
    image = Image.new('RGB', (width, height), '#ffffff')
    draw = ImageDraw.Draw(image)
    
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        normal_font = ImageFont.truetype("arial.ttf", 16)
        bold_font = ImageFont.truetype("arialbd.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
        bold_font = ImageFont.load_default()
    
    y_position = 30
    
    # Encabezado con fondo verde - SIN EMOJIS
    header_height = 80
    draw.rectangle([(0, y_position), (width, y_position + header_height)], 
                  fill='#4a7c59', outline=None)
    draw.text((width//2, y_position + 25), "ECOA", fill='white', font=title_font, anchor="mm")
    draw.text((width//2, y_position + 55), "Materas Sostenibles", fill='#e8f4e8', font=normal_font, anchor="mm")
    
    y_position += header_height + 20
    
    # Código
    draw.text((width//2, y_position), f"Código: {order_data['order_code']}", 
             fill='#333333', font=bold_font, anchor="mm")
    
    y_position += 40
    
    # Línea verde
    draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
    y_position += 20
    
    # Calcular subtotal
    subtotal = 0
    for item in cart_items:
        price = float(item['price']) if isinstance(item['price'], str) else item['price']
        quantity = int(item['quantity']) if isinstance(item['quantity'], str) else item['quantity']
        subtotal += price * quantity
    
    shipping = 5.00 if order_data['customer']['needsShipping'] else 0.00
    
    # Información del pedido con secciones verdes - SIN EMOJIS
    sections = [
        ("INFORMACIÓN DEL PEDIDO", [
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Cliente: {order_data['customer']['fullname']}",
            f"Teléfono: {order_data['customer']['phone']}"
        ]),
        ("PRODUCTOS SOLICITADOS", [
            f"• {item['name']} - ${float(item['price']) * int(item['quantity']):.2f}" 
            for item in cart_items
        ]),
        ("TOTALES", [
            f"Subtotal: ${subtotal:.2f}",
            f"Envío: ${shipping:.2f}",
            f"TOTAL: ${total_amount:.2f}"
        ]),
        ("INFORMACIÓN DE PAGO", [
            f"Método: Transferencia Bancaria",
            f"Referencia: {order_data['order_code']}"
        ]),
        ("INFORMACIÓN DE ENVÍO", [
            f"Destinatario: {order_data['customer']['fullname']}",
            f"Teléfono: {order_data['customer']['phone']}",
            f"Dirección: {order_data['customer'].get('address', 'No especificada')}",
            f"Ciudad: {order_data['customer']['city']}"
        ])
    ]
    
    # Agregar sección de instrucciones si existen
    if order_data['customer'].get('instructions'):
        sections.append(("INSTRUCCIONES ADICIONALES", [
            order_data['customer']['instructions']
        ]))
    
    for section_title, section_items in sections:
        # Fondo verde para título de sección
        draw.rectangle([(40, y_position), (width-40, y_position + 30)], 
                      fill='#4a7c59', outline='#4a7c59', width=1)
        draw.text((width//2, y_position + 15), section_title, 
                 fill='white', font=bold_font, anchor="mm")
        y_position += 35
        
        for item in section_items:
            draw.text((50, y_position), item, fill='#333333', font=normal_font)
            y_position += 25
        
        # Línea verde entre secciones
        if section_title != "INSTRUCCIONES ADICIONALES":  # No poner línea después de la última sección
            draw.line([(40, y_position), (width-40, y_position)], fill='#4a7c59', width=2)
            y_position += 20
    
    # Pie de página con fondo verde
    footer_height = 50
    draw.rectangle([(0, y_position), (width, height)], fill='#4a7c59', outline=None)
    draw.text((width//2, y_position + 15), "¡Gracias por tu compra en Ecoa!", 
             fill='white', font=bold_font, anchor="mm")
    draw.text((width//2, y_position + 35), "Tu compra ayuda al planeta", 
             fill='#e8f4e8', font=normal_font, anchor="mm")
    
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
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para ver tu carrito.", "warning")
        return redirect(url_for('login'))
    
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para agregar productos al carrito.", "warning")
        return redirect(url_for('login'))
    
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
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para modificar tu carrito.", "warning")
        return redirect(url_for('login'))
    
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        removed_item = cart.pop(item_index)
        session['cart'] = cart
        flash(f"{removed_item['name']} fue eliminado del carrito.", "info")
    else:
        flash("El producto no existe en el carrito.", "error")
    return redirect(url_for('cart'))

@app.route('/update_quantity/<int:item_index>', methods=['POST'])
def update_quantity(item_index):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Debes iniciar sesión'})
    
    try:
        cart = session.get('cart', [])
        if 0 <= item_index < len(cart):
            new_quantity = int(request.form.get('quantity', 1))
            
            if new_quantity < 1:
                # Eliminar producto si cantidad es 0
                removed_item = cart.pop(item_index)
                session['cart'] = cart
                return jsonify({
                    'success': True,
                    'removed': True,
                    'message': f"{removed_item['name']} fue eliminado del carrito.",
                    'new_total': f"${sum(item['price'] * item['quantity'] for item in cart):.2f}"
                })
            else:
                # Actualizar cantidad
                cart[item_index]['quantity'] = new_quantity
                session['cart'] = cart
                
                return jsonify({
                    'success': True,
                    'removed': False,
                    'new_quantity': new_quantity,
                    'item_subtotal': f"${cart[item_index]['price'] * new_quantity:.2f}",
                    'new_total': f"${sum(item['price'] * item['quantity'] for item in cart):.2f}"
                })
        else:
            return jsonify({'success': False, 'error': 'Producto no encontrado'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update_cart_quantity/<int:item_index>', methods=['POST'])
def update_cart_quantity(item_index):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para modificar tu carrito.", "warning")
        return redirect(url_for('login'))
    
    cart = session.get('cart', [])
    if 0 <= item_index < len(cart):
        action = request.form.get('action')
        if action == 'increase':
            cart[item_index]['quantity'] += 1
        elif action == 'decrease':
            if cart[item_index]['quantity'] > 1:
                cart[item_index]['quantity'] -= 1
            else:
                # Si la cantidad es 1 y se intenta disminuir, eliminar el producto
                removed_item = cart.pop(item_index)
                session['cart'] = cart
                flash(f"{removed_item['name']} fue eliminado del carrito.", "info")
                return redirect(url_for('cart'))
        
        session['cart'] = cart
        flash("Carrito actualizado.", "success")
    else:
        flash("El producto no existe en el carrito.", "error")
    return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para modificar tu carrito.", "warning")
        return redirect(url_for('login'))
    
    session['cart'] = []
    flash("Carrito vaciado.", "info")
    return redirect(url_for('cart'))

# ================= CHECKOUT =================
@app.route('/checkout')
def checkout():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para realizar una compra.", "warning")
        return redirect(url_for('login'))
    
    cart_items = session.get('cart', [])
    if not cart_items:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for('cart'))
    
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    total = subtotal
    order_code = f"ECOA-{random.randint(10000, 99999)}-{datetime.now().strftime('%d%m')}"
    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, order_code=order_code)

@app.route('/download_receipt', methods=['POST'])
def download_receipt():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para descargar recibos.", "warning")
        return redirect(url_for('login'))
    
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
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para realizar el quiz de planta perfecta.", "warning")
        return redirect(url_for('login'))
    
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
        
        # Guardar las recomendaciones en el perfil del usuario
        try:
            user_profile = UserProfile.query.filter_by(user_id=session['user_id']).first()
            if user_profile:
                user_profile.light = data['luz']
                user_profile.time = data['tiempo_semanal']
                user_profile.space = data['espacio']
                user_profile.has_pets = data['mascotas'] == 'si'
                user_profile.style = data['preferencia_tipo']
                user_profile.recommended_plant = planta
            else:
                user_profile = UserProfile(
                    user_id=session['user_id'],
                    light=data['luz'],
                    time=data['tiempo_semanal'],
                    space=data['espacio'],
                    has_pets=data['mascotas'] == 'si',
                    style=data['preferencia_tipo'],
                    recommended_plant=planta
                )
                db.session.add(user_profile)
            
            db.session.commit()
        except Exception as e:
            print(f"Error guardando perfil de usuario: {e}")
            # No interrumpir el flujo si hay error al guardar el perfil
        
        return render_template('perfect_plant.html', planta=planta, maceta=maceta)
    return render_template('plant_quiz.html')

# ================= INICIO DE APP =================
with app.app_context():
    db.create_all()

# Configuración para producción
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    os.makedirs('static/receipts', exist_ok=True)
    app.run(host='0.0.0.0', port=port, debug=False)