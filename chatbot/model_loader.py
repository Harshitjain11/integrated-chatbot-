import pickle
from pathlib import Path

class ModelLoader:
    def __init__(self):
        model_path = Path("data/chatbot_model.pkl")

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        # if model file contains both model and vectorizer
        if isinstance(data, dict) and "model" in data and "vectorizer" in data:
            self.model = data["model"]
            self.vectorizer = data["vectorizer"]
            self.label_encoder = data.get("label_encoder", None)
        else:
            # fallback (old style)
            self.model = data
            self.vectorizer = None
            self.label_encoder = None

        print("✅ Model loaded successfully")

    def get_model(self):
        return self.model

    def get_vectorizer(self):
        return self.vectorizer

    def predict_proba(self, texts):
        """Transform text using vectorizer and return model probabilities."""
        if self.vectorizer is None:
            raise ValueError("Vectorizer not found in the loaded model.")
        X = self.vectorizer.transform(texts)
        return self.model.predict_proba(X)

    # 🟢 Add this function to decode predicted label index into actual tag
    def decode_label(self, index):
        """Convert label index into actual tag name."""
        if self.label_encoder:
            return self.label_encoder.inverse_transform([index])[0]
        # fallback if label_encoder not found
        if hasattr(self.model, "classes_"):
            return self.model.classes_[index]
        return str(index)
