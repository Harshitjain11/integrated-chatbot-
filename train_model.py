# import json
# import pickle
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.naive_bayes import MultinomialNB

# # ----------------------------
# # Load intents.json
# # ----------------------------
# with open("data/intents.json", "r", encoding="utf-8") as f:
#     intents = json.load(f)

# texts = []
# labels = []

# for intent in intents["intents"]:
#     tag = intent["tag"]
#     for pattern in intent["patterns"]:
#         texts.append(pattern)
#         labels.append(tag)

# # ----------------------------
# # Create TF-IDF vectorizer + classifier
# # ----------------------------
# vectorizer = TfidfVectorizer()
# X = vectorizer.fit_transform(texts)

# model = MultinomialNB()
# model.fit(X, labels)

# # ----------------------------
# # Save both in one dictionary
# # ----------------------------
# data_to_save = {"model": model, "vectorizer": vectorizer}

# with open("data/chatbot_model.pkl", "wb") as f:
#     pickle.dump(data_to_save, f)

# print("✅ Chatbot model and vectorizer saved successfully in data/chatbot_model.pkl")
import json
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# ----------------------------
# Load intents.json
# ----------------------------
with open("data/intents.json", "r", encoding="utf-8") as f:
    intents = json.load(f)

texts = []
labels = []

for intent in intents["intents"]:
    tag = intent["tag"]
    for pattern in intent["patterns"]:
        texts.append(pattern)
        labels.append(tag)

# ----------------------------
# Create TF-IDF vectorizer + classifier
# ----------------------------
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

model = MultinomialNB()
model.fit(X, labels)

# ----------------------------
# Save both in one dictionary
# ----------------------------
data_to_save = {"model": model, "vectorizer": vectorizer}

with open("data/chatbot_model.pkl", "wb") as f:
    pickle.dump(data_to_save, f)

print("✅ Chatbot model and vectorizer saved successfully in data/chatbot_model.pkl")
