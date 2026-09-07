import random

class Agente:
    def answer(self, text: str, valid_commands: list[str]) -> str:
        # Si por alguna razón no hay comandos, hacemos un fallback seguro
        if not valid_commands:
            return "look"
        
        # ¡Magia! Elige una acción al azar de las disponibles
        comando = random.choice(valid_commands)
        print(f"[Agente] Opciones disponibles: {len(valid_commands)} | Eligió: {comando}")
        return comando