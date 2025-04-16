# Docker Cleanup und Funktionstests

Diese Anleitung zeigt Dir, wie Du alte Docker-Container und nicht verwendete Ressourcen bereinigst und anschließend alle Funktionen Deines Projekts über das Terminal testest.

---

## 1. Docker System Bereinigen

Um sicherzustellen, dass keine alten Container, Images oder Netzwerke Konflikte verursachen, führe folgende Schritte aus:

### 1.1 Alle Container anzeigen
Zeige alle laufenden und gestoppten Container an:
bash
docker ps -a

### 1.2 Einzelne Container stoppen und löschen

Um einen bestimmten Container (z. B. rss-zookeeper) zu stoppen und zu entfernen:

docker stop rss-zookeeper
docker rm -f rss-zookeeper

### 1.3 Alle Container entfernen

Um alle Container zu löschen, verwende:

docker rm -f $(docker ps -aq)

### 1.4 Nicht verwendete Ressourcen bereinigen

Entferne alle ungenutzten Container, Images, Netzwerke und Caches:

docker system prune -a

Hinweis: Dieser Befehl löscht alle nicht verwendeten Ressourcen. Stelle sicher, dass Du keine wichtigen Images oder Container verlierst.
## 2. Docker Compose Neustart

Nachdem Du das System bereinigt hast, baue und starte alle Container neu.
### 2.1 Docker-Images bauen

Navigiere in das Projektverzeichnis (wo sich die Dockerfile und docker-compose.yml befinden) und führe aus:

docker-compose build

### 2.2 Container im Hintergrund starten

Starte alle Container mit:

docker-compose up -d

### 2.3 Überprüfe laufende Container

Verifiziere, dass alle Container laufen:

docker ps

## 3. Funktionstests über das Terminal
### 3.1 Flask-Webanwendung testen

    Im Browser:
    Öffne http://localhost:5000 in Deinem Browser.
    Mit curl:

    curl http://localhost:5000

### 3.2 Dashboard testen

    Im Browser:
    Öffne http://localhost:5000/dashboard in Deinem Browser.
    Mit curl:

    curl http://localhost:5000/dashboard

### 3.3 Scraper-Funktion testen

Führe den Scraper manuell aus:

python -m rss_analyzer.scraper

Überprüfe in der Terminal-Ausgabe, ob Artikel verarbeitet und korrekt in die Datenbank eingefügt werden (und ob die Themen in der Topics-Tabelle aktualisiert werden).
3.4 Kafka-Integration testen

Um zu prüfen, ob Nachrichten im Kafka-Topic ankommen, führe in einem Terminal (oder innerhalb des Kafka-Containers) folgenden Befehl aus:

docker exec -it rss-kafka-ingest kafka-console-consumer --bootstrap-server localhost:9092 --topic UserQuestions --from-beginning

Dies zeigt alle Nachrichten im Topic UserQuestions an.
### 3.5 Spark-Integration testen (optional)

Falls Du den Spark-Job nutzen möchtest, führe folgendes aus:

spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.5,org.apache.kafka:kafka-clients:2.0.0 spark_read_from_topic_and_show.py

Überprüfe, ob die Nachrichten aus Kafka korrekt angezeigt werden.
## 4. Logs und Fehlersuche

Um die Logs eines bestimmten Containers einzusehen, benutze:

docker-compose logs <service_name>

Beispiel für die Flask-App:

docker-compose logs rag-app

Dies hilft Dir, eventuelle Fehler in der Anwendung zu identifizieren.