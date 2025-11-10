import pandas as pd
import joblib
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

# === RUTAS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'static', 'data', 'plants_dataset.csv')
MODELS_PATH = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_PATH, exist_ok=True)

# === CARGAR DATOS ===
df = pd.read_csv(DATA_PATH)

# === VARIABLES ===
features = ['espacio', 'luz', 'tiempo_semanal', 'experiencia', 'preferencia_tipo',
            'mascotas', 'bajo_mantenimiento', 'pref_maceta', 'riego_auto', 'presupuesto', 'clima']

target_planta = 'label_planta'
target_maceta = 'label_maceta'

# === ENCODERS ===
encoders = {}
for col in features:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le

# === ENCODERS DE TARGET ===
plant_encoder = LabelEncoder()
df[target_planta] = plant_encoder.fit_transform(df[target_planta])

pot_encoder = LabelEncoder()
df[target_maceta] = pot_encoder.fit_transform(df[target_maceta])

# === ENTRENAR MODELOS ===
model_plant = RandomForestClassifier(random_state=42)
model_pot = RandomForestClassifier(random_state=42)

model_plant.fit(df[features], df[target_planta])
model_pot.fit(df[features], df[target_maceta])

# === GUARDAR MODELOS ===
joblib.dump(model_plant, os.path.join(MODELS_PATH, 'model_plant.pkl'))
joblib.dump(model_pot, os.path.join(MODELS_PATH, 'model_pot.pkl'))
joblib.dump(encoders, os.path.join(MODELS_PATH, 'encoders.pkl'))
joblib.dump(plant_encoder, os.path.join(MODELS_PATH, 'plant_encoder.pkl'))
joblib.dump(pot_encoder, os.path.join(MODELS_PATH, 'pot_encoder.pkl'))

print("✅ Modelos entrenados y guardados correctamente en /models/")
