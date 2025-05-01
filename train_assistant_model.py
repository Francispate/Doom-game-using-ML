import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import os

log_file = "assistant_logs.csv"

if not os.path.exists(log_file):
    print("Log file not found.")
    exit()

data = pd.read_csv(log_file)
data.dropna(inplace=True)

if data.empty:
    print("No data found in assistant_logs.csv. Play the game with the assistant to generate data.")
    exit()

features = [
    "player_health",
    "threat_count",
    "closest_enemy_distance",
    "in_fov",
    "is_hidden"
]
label = "advice"

X = data[features]
y = data[label]

if len(X) < 2:
    print("Not enough data to train a model. Need at least 2 rows.")
    exit()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

joblib.dump(model, "assistant_model.joblib")
print("\nModel saved as assistant_model.joblib")

def retrain_model(log_file="assistant_logs.csv"):
    if not os.path.exists(log_file):
        print("Log file not found.")
        return

    data = pd.read_csv(log_file)
    data.dropna(inplace=True)

    if data.empty:
        print("No data found in assistant_logs.csv.")
        return

    features = [
        "player_health",
        "threat_count",
        "closest_enemy_distance",
        "in_fov",
        "is_hidden"
    ]
    label = "advice"

    X = data[features]
    y = data[label]

    if len(X) < 2:
        print("Not enough data to retrain the model.")
        return

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    joblib.dump(model, "assistant_model.joblib")
    print("\nModel retrained and saved as assistant_model.joblib")
