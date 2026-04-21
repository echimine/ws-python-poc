# ws-python-poc

Système domotique qui reçoit des données de capteurs IoT (ESP32) via WebSocket, interprète des commandes en langage naturel, et analyse des images — le tout en local avec des modèles d'IA.

## Ce que ça fait

- Reçoit des messages WebSocket depuis des appareils ESP32 (température, lumière, bouton, RFID, LED)
- Interprète des commandes en langage naturel pour contrôler le hardware (ex : "allume la LED")
- Analyse des images envoyées par `MY_APP` et lit la description à voix haute
- Maintient une mémoire persistante des états et préférences utilisateur

## Modèles IA utilisés

### Langage naturel → actions (texte)

**Gemma 4 Q4_K_M** via [llama.cpp](https://github.com/ggerganov/llama.cpp)

```bash
llama-server -m /Users/eliott/Models/Gemma\ 4/google_gemma-4-E4B-it-Q4_K_M.gguf --port 8080
```

Doit tourner en arrière-plan avant de lancer `main.py`.

### Vision (images)

**mlx-community/gemma-4-e4b-it-4bit** via [mlx_vlm](https://github.com/Blaizzy/mlx-vlm)

Invoqué automatiquement en subprocess à la réception d'une image. Nécessite Apple Silicon (MLX).

## Installation

```bash
# Créer et activer le venv
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Télécharger le modèle de vision (première utilisation)
pip install mlx-vlm
```

## Lancement

```bash
# 1. Démarrer le serveur llama.cpp
llama-server -m /Users/eliott/Models/Gemma\ 4/google_gemma-4-E4B-it-Q4_K_M.gguf --port 8080

# 2. Lancer l'application
python3 main.py
```

## Configuration

Par défaut l'app se connecte en mode **dev** (`ws://0.0.0.0:8765`).  
Pour se connecter en prod (`ws://192.168.10.127:9000`), modifier `main.py` : remplacer `WSClient.dev()` par `WSClient.prod()`.
