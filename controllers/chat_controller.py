from __future__ import annotations
from textworld import EnvInfos
import textworld.gym
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal
from agente.Agente import Agente  # Asegúrate de que la ruta sea correcta

# Un mock de tu Agente para que el código corra sin errores de importación

@dataclass(slots=True)
class ChatMessage:
    role: str
    text: str

class ChatController(QObject):
    state_changed = Signal()

    def __init__(
        self,
        graph_controller,
        game_file: str | None = None,
        max_episode_steps: int = 50,
    ) -> None:
        super().__init__()
        self._model_name = "TextWorld Agent"
        self._is_online = True
        self._messages: list[ChatMessage] = []
        self.agente = Agente()
        self.graph_controller = graph_controller
        self.env = None
        self.env_id = None
        self.current_obs = ""
        self.valid_commands: list[str] = []
        self.done = False

        if game_file:
            self.start_game(game_file, max_episode_steps=max_episode_steps)

    @property
    def is_game_active(self) -> bool:
        return self.env is not None

    def start_game(
        self,
        game_file: str,
        max_episode_steps: int = 50,
        request_infos: EnvInfos | None = None,
    ) -> None:
        if self.env is not None:
            try:
                self.env.close()
            except Exception:
                pass

        if request_infos is None:
            request_infos = EnvInfos(
                admissible_commands=True,
                location=True,
                facts=True,
            )

        self.env_id = textworld.gym.register_game(
            game_file,
            max_episode_steps=max_episode_steps,
            request_infos=request_infos,
        )
        self.env = textworld.gym.make(self.env_id)
        self.graph_controller.reset()
        self.reset_conversation()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def reset_conversation(self) -> None:
        self._messages.clear()
        if self.env is None:
            self.state_changed.emit()
            return

        self.graph_controller.reset()
        obs, infos = self.env.reset()
        # Solo limpiamos el texto original
        self.current_obs = self._clean_obs(obs)
        self.valid_commands = infos.get("admissible_commands", ["look"])
        self.done = False
        self.graph_controller.update_map(infos)

        self._messages.append(ChatMessage(role="agent", text=self.current_obs))
        self.state_changed.emit()

    def get_map_data(self, infos: dict) -> dict:
        lugar_actual = infos.get("location", "Desconocido")
        facts = infos.get("facts", [])
        
        conexiones = []
        for fact in facts:
            # Convertimos el objeto Fact a texto para parsearlo fácil
            fact_str = str(fact)
            
            # Filtramos solo los datos geográficos que nos importan
            if "north_of" in fact_str or "south_of" in fact_str or "east_of" in fact_str or "west_of" in fact_str:
                conexiones.append(fact_str)
                
        return {
            "current_room": lugar_actual,
            "connections": conexiones
        }

    def add_game_message(self, text: str) -> None:
        self._messages.append(ChatMessage(role="agent", text=text))
        self.state_changed.emit()
        
    def add_action_message(self, text: str) -> None:
        self._messages.append(ChatMessage(role="user", text=text))
        self.state_changed.emit()

    def _clean_obs(self, obs: str) -> str:
        # Cortamos el texto en líneas y quitamos la que tiene el puntaje/turnos (ej: >Attic=-0/9)
        lineas = obs.split('\n')
        lineas_limpias = [l for l in lineas if not (">" in l and "/" in l and l.strip().startswith(">"))]
        
        # Volvemos a unir el texto y quitamos espacios en blanco extra a los bordes
        return '\n'.join(lineas_limpias).strip()

    def next_step(self) -> None:
        if self.env is None:
            self.add_game_message("No hay un entorno activo. Inicia uno desde el panel de configuración.")
            return

        if self.done:
            self.add_game_message("El juego ya terminó.")
            return

        action = self.agente.answer(self.current_obs, self.valid_commands)
        self.add_action_message(action)

        obs, reward, self.done, infos = self.env.step(action)
 
        
        self.current_obs = self._clean_obs(obs)
        self.valid_commands = infos.get("admissible_commands", ["look"])
        self.graph_controller.update_map(infos)

        self.add_game_message(self.current_obs)


