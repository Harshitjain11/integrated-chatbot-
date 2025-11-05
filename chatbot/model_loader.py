# import pickle
# from pathlib import Path
# import json

# class ModelLoader:
#     def __init__(self):
#         model_path = Path("data/chatbot_model.pkl")
#         intents_path = Path("data/intents.json")

#         if not model_path.exists():
#             raise FileNotFoundError(f"Model not found: {model_path}")

#         with open(model_path, "rb") as f:
#             data = pickle.load(f)

#         self.model = data.get("model")
#         self.label_encoder = data.get("label_encoder")

#         with open(intents_path, "r", encoding="utf-8") as f:
#             self.intents = json.load(f)

#         print("✅ Model loaded successfully")

#     def predict(self, text):
#         y_pred = self.model.predict([text.lower()])[0]
#         conf = max(self.model.predict_proba([text.lower()])[0])
#         tag = self.label_encoder.inverse_transform([y_pred])[0]
#         return tag, conf
# chatbot/model_loader.py
import pickle
from pathlib import Path
import json

class ModelLoader:
    def __init__(self, model_path: Path = Path("data/chatbot_model.pkl"),
                 intents_path: Path = Path("data/intents.json")):
        self.model_path = Path(model_path)
        self.intents_path = Path(intents_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # load model dict (expects {"model": pipeline, "label_encoder": le})
        with open(self.model_path, "rb") as f:
            data = pickle.load(f)

        if not isinstance(data, dict) or "model" not in data or "label_encoder" not in data:
            raise ValueError("Model file must be a dict with keys 'model' and 'label_encoder'")

        self.model = data["model"]                  # pipeline: vectorizer + classifier
        self.label_encoder = data["label_encoder"]  # LabelEncoder fitted on tags

        # load intents.json (for response lookups if needed)
        if self.intents_path.exists():
            with open(self.intents_path, "r", encoding="utf-8") as f:
                self.intents = json.load(f)
        else:
            self.intents = None

        print("✅ ModelLoader: model and label_encoder loaded.")

    def predict_proba(self, texts):
        """
        texts: list[str] or list-like
        returns: array-like probabilities as model.predict_proba output
        """
        return self.model.predict_proba(texts)

    def predict_raw(self, texts):
        """
        returns raw model.class predictions (encoded labels)
        """
        return self.model.predict(texts)

    def decode_label(self, class_index):
        """
        class_index: integer index into self.model.classes_ (i.e. position)
        returns: decoded tag string via label_encoder
        """
        # get the actual encoded class value at that position
        encoded_value = self.model.classes_[class_index]
        # decode to original string tag
        return self.label_encoder.inverse_transform([encoded_value])[0]
