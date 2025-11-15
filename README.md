# 📘 Projekt-Anleitung: Flask + MySQL auf PythonAnywhere
Diese Anleitung beschreibt den kompletten Ablauf, um das Projekt auszuführen und im Team (GitHub + PythonAnywhere) zu entwickeln.

## ✅ Voraussetzungen

### 👥 Team

-   Alle Teammitglieder besitzen einen **GitHub-Account**
-   **Eine Person** besitzt einen **PythonAnywhere-Account**
-   Diese Person teilt das PythonAnywhere-Login **mit dem Team** (damit alle deployen können)

------------------------------------------------------------------------

## 🚀 1. GitHub-Projekt einrichten

### 1.1 Vorlage importieren

1.  Repository öffnen:\
    👉 https://github.com/EgliMNG/db-project
2.  Rechts oben **Fork** klicken
3.  Das neue Repo heisst z.B. username/db-project

### 1.2 Teammitglieder einladen
Im geforkte Repo:
1.  Settings
2.  Collaborators
3.  Add people
4.  Teammitglieder + **Lehrperson** einladen

------------------------------------------------------------------------

## 🌐 2. PythonAnywhere vorbereiten

### 2.1 Neue Flask-Webapp erstellen
1.	Login auf https://www.pythonanywhere.com
2.	Menü: Web → Add new web app
3.	Flask auswählen
4.	Python 3.13 auswählen

### 2.2 Webapp-Verzeichnis ersetzen
1.	Zurück zur Webübersicht
2.	Jetzt Terminal öffnen\
→ Open Bash Console

``` bash
# Das von GitHub geforkte Repo klonen
git clone https://github.com/dein_name>/<dein_repo>.git

# Alte Struktur löschen
rm -rf mysite

# Neuen Code als Webapp-Verzeichnis verwenden
mv <dein_repo> mysite 
```

------------------------------------------------------------------------

### 2.3 Autodeployment (post-merge Hook)
Damit Änderungen von GitHub automatisch deployed werden:

``` bash
cd mysite/.git/hooks
vim post-merge
```

Im Vim-Editor:
1.	Taste *i* (insert mode)
2.	Folgenden Inhalt einfügen:

``` bash
#!/bin/bash
touch /var/www/<username>_pythonanywhere_com_wsgi.py
```

3.  *Esc*
4.  *:x* (speichern & schliessen)
5.  Ausführbar machen:

``` bash
chmod +x post-merge
```

------------------------------------------------------------------------

## 🗄️ 3. MySQL-Datenbank einrichten

### 3.1 Datenbank erstellen
1.  Im Menü auf *Databases*
2.  Unter MySQL ein DB-Passwort wählen und mit "Initialize MySQL" bestätigen
3.  Mit einem Klick auf die neu erstellte DB "&lt;username&gt;$default"
4.  In MySQL-Konsole SQL Script ausführen:

``` sql
SOURCE mysite/db/TODOS.sql;
```
Dadurch wird die gesamte Struktur erstellt.

------------------------------------------------------------------------

### 3.2 `.env` erstellen
1.  Im Menü auf *Files*
2.  Im Textfeld *.env* eintippen und auf "New file" klicken (unbedingt auf der obersten Stufe und **nicht** im "mysite"-Ordner)

3.  Inhalt:
```
DB_HOST=<username>.mysql.pythonanywhere-services.com
DB_USER=<username>
DB_PASSWORD=<dein_db_passwort>
DB_DATABASE=<username>$default
W_SECRET=<irgend_ein_secret>
```
Für `W_SECRET` darfst du irgend eine Buchstaben- und Zahlenkombination wählen und notieren, da du diese im nächsten Schhritt wieder brauchst

------------------------------------------------------------------------

## 🔄 4. GitHub-WebHook für automatisches Deployment

Im GitHub-Repo:
1.  Settings → Webhooks → Add webhook
2.  URL:\
    https://&lt;username&gt;.pythonanywhere.com/update_server
3.  Content type: `application/json`
4.  Secret: Die geheime Kombination, die du im ".env" unter `W_SECRET` gesetzt hast
5.  **Add webhook**