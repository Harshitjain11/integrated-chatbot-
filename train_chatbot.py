import json
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder

# Load intents.json
with open("data/intents.json", "r") as file:
    data = json.load(file)

# Prepare training data
texts = []
labels = []

for intent in data["intents"]:
    for pattern in intent["patterns"]:
        texts.append(pattern.lower())
        labels.append(intent["tag"])

# Encode labels
label_encoder = LabelEncoder()
y = label_encoder.fit_transform(labels)

# Vectorize texts
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

# Train model
model = MultinomialNB()
model.fit(X, y)

# Save model and vectorizer
model_data = {
    "model": model,
    "vectorizer": vectorizer,
    "label_encoder": label_encoder
}

with open("data/intents.json", "r", encoding="utf-8") as file:
    pickle.dump(model_data, file)

print("✅ Model trained and saved successfully!")
