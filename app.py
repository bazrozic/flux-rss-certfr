import feedparser
import requests
import os
import json
import time

# URL du flux RSS CERT-FR
RSS_URL = "https://www.cert.ssi.gouv.fr/feed"

# URL du webhook Discord (à remplacer par ta propre URL)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1379737836978442290/WNGqqclvUZ_a3QfiLkU3wvOM5Eb31D4T7rNcMYS1m1SQMkH-16Woz8kd2JWATpmAzNAG"

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

def main():
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
    else:
        print("Pas de nouvelles alertes.")


if __name__ == "__main__":
    main()
