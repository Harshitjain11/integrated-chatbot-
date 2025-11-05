# from chatbot.model_loader import ModelLoader

# loader = ModelLoader()
# text = input("Type something: ")
# X = loader.vectorizer.transform([text])
# pred = loader.model.predict(X)[0]
# proba = loader.model.predict_proba(X)[0]
# print("Predicted:", pred)
# print("Classes:", loader.model.classes_)
# print("Probabilities:", proba)

from chatbot.model_loader import ModelLoader

# Load model
loader = ModelLoader()

while True:
    text = input("Type something (or press Enter to quit): ").strip()
    if not text:
        break

    # Get probability predictions
    probs = loader.predict_proba([text])[0]

    # Get best index and confidence
    best_pos = probs.argmax()
    conf = probs[best_pos]

    # Decode tag name
    tag = loader.decode_label(best_pos)

    print(f"\n🧠 Predicted tag: {tag}")
    print(f"🔢 Confidence: {conf:.4f}")
    print(f"📊 All classes: {loader.model.classes_}\n")
