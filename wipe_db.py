from google.cloud import firestore

# Łączymy się z domyślną bazą
db = firestore.Client(project="balmy-hologram-392614")

collections = ["active_tables", "orders", "menu", "config"]

print("Rozpoczynam czyszczenie bazy...")
for coll_name in collections:
    docs = db.collection(coll_name).stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"Usunięto {count} dokumentów z kolekcji: {coll_name}")

print("✅ Baza Firestore została całkowicie wyzerowana!")
