import torch
from sklearn.metrics import confusion_matrix
from fraud_ai.federated.client import FraudBankClient

checkpoint = torch.load(
    "ai_engine/artifacts/federated/global_model.pt",
    map_location="cpu",
    weights_only=False,
)

totals = [0, 0, 0, 0]

for bank in ("alpha", "beta", "gamma"):
    client = FraudBankClient(bank)
    client.model.load_state_dict(checkpoint["model_state_dict"])
    client.model.eval()

    with torch.no_grad():
        probabilities = torch.sigmoid(client.model(client.X_test)).numpy()

    predictions = (probabilities >= 0.5).astype(int)
    actual = client.y_test.numpy().astype(int)

    tn, fp, fn, tp = confusion_matrix(
        actual, predictions, labels=[0, 1]
    ).ravel()

    totals = [a + b for a, b in zip(totals, [tn, fp, fn, tp])]

    print(f"\n{bank.upper()}")
    print(f"True negatives : {tn}")
    print(f"False positives: {fp}")
    print(f"False negatives: {fn}")
    print(f"True positives : {tp}")

tn, fp, fn, tp = totals

print("\nOVERALL — ALL THREE BANKS")
print(f"True negatives : {tn}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")
print(f"True positives : {tp}")
