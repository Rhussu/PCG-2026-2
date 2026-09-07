from __future__ import annotations

from dataclasses import dataclass

from controllers.chat_controller import ChatController
from controllers.graph_controller import GraphController
from interface.ui import MainWindow, create_application


@dataclass(frozen=True)
class WorldConfig:
    game_file: str = "text-world/simple_game.z8"
    max_episode_steps: int = 50


WORLD_CONFIG = WorldConfig(
    game_file="tw/mundo-c.z8",
    max_episode_steps=50,
)


def main() -> int:

    print("Initializing application...")
    app = create_application()

    graph_controller = GraphController()
    chat_controller = ChatController(graph_controller)

    window = MainWindow(graph_controller, chat_controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


