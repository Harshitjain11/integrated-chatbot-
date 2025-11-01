# chatbot/intent_predictor.py
from .model_loader import ModelLoader

# Default threshold (tune later)
DEFAULT_THRESHOLD = 0.45

class IntentPredictor:
    def __init__(self, model_loader: ModelLoader, threshold: float = DEFAULT_THRESHOLD):
        self.loader = model_loader
        self.threshold = threshold

    def predict(self, text):
        """
        Returns (tag, confidence)
        If confidence < threshold => returns ("fallback", confidence)
        """
        if not text or not text.strip():
            return "fallback", 0.0
        probs = self.loader.predict_proba([text.lower().strip()])[0]
        best_idx = int(probs.argmax())
        best_conf = float(probs[best_idx])
        label = self.loader.decode_label(best_idx)
        if best_conf < self.threshold:
            return "fallback", best_conf
        return label, best_conf
