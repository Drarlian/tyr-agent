import json
import os

class HistoryStorage:
    def __init__(self, filename: str = "conversation_history.json"):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)

    def save_history(self, agent_name: str, history: dict):
        try:
            data = self.load_all()

            if data.get(agent_name, False):
                data[agent_name].append(history)
            else:
                data[agent_name] = [history]

            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] - Erro ao salvar histórico: {e}")

    def load_history(self, agent_name: str) -> list:
        data = self.load_all()
        return data.get(agent_name, [])

    def load_all(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
