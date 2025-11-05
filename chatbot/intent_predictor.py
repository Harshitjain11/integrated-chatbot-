import numpy as np

class IntentPredictor:
    def __init__(self, model_loader, threshold=0.45):
        """
        Intent predictor handles model predictions and confidence threshold.
        """
        self.model_loader = model_loader
        self.model = model_loader.model
        self.label_encoder = model_loader.label_encoder
        self.intents = model_loader.intents
        self.threshold = threshold

    def predict(self, message: str):
        """
        Predict intent tag and confidence using the trained pipeline.
        """
        if not message or not self.model:
            return "fallback", 0.0

        # Use pipeline directly
        probs = self.model.predict_proba([message.lower().strip()])[0]
        best_idx = int(np.argmax(probs))
        conf = float(probs[best_idx])

        tag = self.label_encoder.inverse_transform([best_idx])[0]
        if conf < self.threshold:
            return "fallback", conf

        return str(tag), conf
