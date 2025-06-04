import feedparser
import requests
import os
import json
import time
from dotenv import load_dotenv
from flask import Flask

# Charger les variables d'environnement
load_dotenv()

# Créer l'application Flask
flask_app = Flask(__name__)

# URL du flux RSS CERT-FR
RSS_URL = "https://www.cert.ssi.gouv.fr/feed"

# URL du webhook Discord (à remplacer par ta propre URL)
DISCORD_WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Fichier local pour mémoriser les alertes déjà envoyées
CACHE_FILE = "alertes_certfr_cache.json"


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return []


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def send_to_discord(webhook_url, title, link, published):
    data = {
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": f"Alerte publiée le : {published}",
                "color": 15158332  # rouge clair
            }
        ]
    }

    while True:
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            return  # Succès
        elif response.status_code == 429:
            retry_after = response.json().get("retry_after", 1)
            print(f"Rate limited. Attente de {retry_after} seconde(s)...")
            time.sleep(retry_after)
        else:
            print(f"Erreur en envoyant sur Discord: {response.status_code}, {response.text}")
            return

def check_alerts():
    """Fonction principale pour vérifier et envoyer les alertes"""
    cache = load_cache()
    print(f"Cache contient {len(cache)} alertes sauvegardées.")

    feed = feedparser.parse(RSS_URL)
    print(f"{len(feed.entries)} alertes trouvées dans le flux RSS.")
    
    print(f"Statut du parsing : {feed.get('bozo', False)}")
    if feed.get("bozo_exception"):
        print(f"Erreur feedparser : {feed.bozo_exception}")

    new_alerts = []

    for entry in feed.entries:
        alert_id = entry.link
        print(f"Traitement alerte ID: {alert_id}")

        if alert_id not in cache:
            title = entry.title
            link = entry.link
            published = entry.get("published", "Date inconnue")
            message = f"**Nouvelle alerte CERT-FR**\n{title}\nPublié le : {published}\n{link}"

            send_to_discord(DISCORD_WEBHOOK_URL, title, link, published)
            print(f"Alerte envoyée : {title}")

            new_alerts.append(alert_id)
        else:
            print("Alerte déjà envoyée.")

    if new_alerts:
        cache.extend(new_alerts)
        save_cache(cache)
        print(f"{len(new_alerts)} nouvelles alertes envoyées.")
        return f"{len(new_alerts)} nouvelles alertes envoyées."
    else:
        print("Pas de nouvelles alertes.")
        return "Pas de nouvelles alertes."

@flask_app.route("/")
def trigger_alerts():
    """Endpoint pour déclencher la vérification des alertes"""
    try:
        result = check_alerts()
        return f"OK - {result}"
    except Exception as e:
        return f"Erreur: {str(e)}", 500

@flask_app.route("/health")
def health_check():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    return "Service actif"

def main():
    check_alerts()

if __name__ == "__main__":
    # En mode développement, lancer directement le script
    if os.getenv('FLASK_ENV') == 'development':
        flask_app.run(debug=True)
    else:
        main()
