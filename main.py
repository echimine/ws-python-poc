from WSClient import WSClient
from Message import *
from types import SimpleNamespace
from pathlib import Path
import subprocess
import json
import base64
import tempfile
import os
from nl_to_code.nl_to_code import execute_code_from

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE_PATH = BASE_DIR / "nl_to_code" / "current_state_memory.md"
NL_TO_CODE_MAIN_PATH = BASE_DIR / "nl_to_code" / "main"


def build_sensor_payload(tool_result):
    if not isinstance(tool_result, dict):
        return None

    sensor_id = tool_result.get("sensor_id")
    if not sensor_id:
        return None

    dest = tool_result.get("dest", "ALL")
    value = tool_result.get("value")

    if value is None:
        value = {
            key: val
            for key, val in tool_result.items()
            if key not in {"message_type", "sensor_id", "dest"}
        }

    if value in (None, {}):
        return None

    return sensor_id, value, dest


def main():

    sensor_message_output = {
        "BUTTON": SimpleNamespace(value=["button-pressed"]),
        "LIGHT": SimpleNamespace(value=["percent"]),
        "RFID": SimpleNamespace(value=["isdetected"]),
        "TEMPERATURE": SimpleNamespace(value=["humidity", "temperature"])
    }

    def gerer_led(**kwargs):
        sensor_id = kwargs.get("sensor_id")
        led_id = kwargs.get("led_id")
        dest = kwargs.get("dest")
        state = kwargs.get("state")

        print("Sensor:", sensor_id)
        print("LED:", led_id)
        print("State:", state)

        return {
            "sensor_id": sensor_id,
            "dest": dest,
            "value": {
                "led_id": int(led_id),
                "state": state
            }
        }

    def read_memory(category=None, path=MEMORY_FILE_PATH):
        """Lit un fichier mémoire sectionné par catégories Markdown (#...:)."""
        path = Path(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {} if category is None else []

        memoire_data = {}
        current_category = None

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("#") and line.endswith(":"):
                current_category = line
                memoire_data.setdefault(current_category, [])
                continue

            if current_category is not None:
                memoire_data[current_category].append(line)

        if category is not None:
            return memoire_data.get(category, [])

        return memoire_data

    def write_memory(category=None, content=None, path=MEMORY_FILE_PATH, sensor_id=None):
        """
        Écrit dans le fichier mémoire.
        - category : nom de la catégorie (ou sensor_id si fourni)
        - content : valeur à ajouter
        - path : chemin du fichier
        - sensor_id : si présent, utilisé comme category
        """
        if sensor_id:
            category = sensor_id

        if category is None or content is None:
            return None

        if not category.startswith("#"):
            category = f"#{category}"
        if not category.endswith(":"):
            category = f"{category}:"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        memoire_data = read_memory(path=path)

        # si la catégorie n'existe pas encore, on la crée
        if category not in memoire_data:
            memoire_data[category] = []

        # ajout du contenu
        memoire_data[category].append(str(content))

        # réécriture complète du fichier
        with open(path, "w", encoding="utf-8") as f:
            for cat, contents in memoire_data.items():
                f.write(cat + "\n")
                for item in contents:
                    f.write(item + "\n")
                f.write("\n")

        return memoire_data

    tool_mapping = {
        "gerer_led": gerer_led,
        "write_memory": write_memory,
        "read_memory": read_memory
    }

    categories = ["#TEMPERATURE:", "#OBJET DETECTE:", "#PREFERENCE UTILISATEUR:"]

    client = WSClient.dev()

    def on_connect():
        print("Connecté ! Démarrage du mac")

    def on_message_received(message):
        if message.receiver != client.username:
            return

        #print("receiver", message.value)
        #print("receiver", message.emitter)

        sensor_id = message.sensor_id
        value = message.value

        if message.emitter == "MON_APP":
            if message.message_type == MessageType.RECEPTION.IMAGE and isinstance(value, str) and value.startswith("IMG:"):
                img_b64 = value[4:]
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(base64.b64decode(img_b64))
                    tmp_path = tmp.name
                try:
                    result = subprocess.run(
                        [
                            "python3", "-m", "mlx_vlm", "generate",
                            "--model", "mlx-community/gemma-4-e4b-it-4bit",
                            "--image", tmp_path,
                            "--prompt", "Décris cette image en détail en français",
                            "--max-tokens", "300"
                        ],
                        capture_output=True, text=True
                    )
                    parts = result.stdout.split("==========")
                    if len(parts) >= 2:
                        block = parts[1]
                        marker = "<|turn>model\n\n"
                        idx = block.find(marker)
                        if idx != -1:
                            generated = block[idx + len(marker):].strip()
                            print(generated)
                            first_sentence = generated.split("\n")[0].strip()
                            print(first_sentence)
                            subprocess.run(["say", "-v", "Thomas", first_sentence])
                    else:
                        print(result.stdout)
                finally:
                    os.unlink(tmp_path)
            return
        

        if message.emitter == "ESP32_ELIOTT":
            # si message.value est du JSON sous forme de string
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass

            # Ignore les commandes texte de type @...
            if isinstance(value, str) and value.startswith("@"):
                return

            if sensor_id is not None and isinstance(value, dict):
                formatted_sensor_id = f"#{sensor_id}:"
                sensor_config = sensor_message_output.get(sensor_id)
                if sensor_config is None:
                    content = value
                else:
                    keys = sensor_config.value
                    content = {k: value[k] for k in keys if k in value}

                if content:
                    write_memory(
                        category=formatted_sensor_id,
                        path=MEMORY_FILE_PATH,
                        content=str(content)
                    )
                    temp = content.get("temperature")
                    if temp is not None:
                        client.send(
                            f"La température de la pièce est de {temp}°C",
                            "ALL"
                        )
            return

        if isinstance(value, str):
            prompt = value[3:].strip()
            response = execute_code_from(
                nl=prompt,
                filter_path=str(NL_TO_CODE_MAIN_PATH),
                tools=tool_mapping,
                categories=categories
            )
            payload = build_sensor_payload(response)
            if payload:
                out_sensor_id, out_value, dest = payload
                client.send_sensor(out_sensor_id, out_value, dest)
            else:
                print("Tool result:",)
            if message.message_type == MessageType.RECEPTION.TEXT:
                subprocess.run(["python3", "-m", "piper", "-m", "fr_FR-tom-medium", "--", f"{value}"])
            if message.message_type == MessageType.RECEPTION.IMAGE:
                print(value)
            print(response)
        else:
            print("Message non texte ignoré:", value)

    client.on_connect_callback = on_connect
    client.on_message_callback = on_message_received
    client.connect()


if __name__ == "__main__":
    main()
