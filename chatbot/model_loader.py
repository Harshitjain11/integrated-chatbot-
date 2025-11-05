import pickle
from pathlib import Path
import json

class ModelLoader:
    def __init__(self):
        model_path = Path("data/chatbot_model.pkl")
        intents_path = Path("data/intents.json")

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.model = data.get("model")
        self.label_encoder = data.get("label_encoder")

        with open(intents_path, "r", encoding="utf-8") as f:
            self.intents = json.load(f)

        print("✅ Model loaded successfully")

    def predict(self, text):
        y_pred = self.model.predict([text.lower()])[0]
        conf = max(self.model.predict_proba([text.lower()])[0])
        tag = self.label_encoder.inverse_transform([y_pred])[0]
        return tag, conf
