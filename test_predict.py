from chatbot.model_loader import ModelLoader

loader = ModelLoader()
text = input("Type something: ")
X = loader.vectorizer.transform([text])
pred = loader.model.predict(X)[0]
proba = loader.model.predict_proba(X)[0]
print("Predicted:", pred)
print("Classes:", loader.model.classes_)
print("Probabilities:", proba)
