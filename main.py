from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime


def run_cli_test(
    config_file: str,
    iterations: int | None = None,
    agent: str | None = None,
    max_steps: int | None = None,
    delay: int | None = None,
    background: bool = False,
) -> int:
    """Ejecuta los benchmarks de testeo desde la terminal (modo headless) sin interfaz gráfica."""
    if not os.path.exists(config_file):
        print(f"\n[ERROR] El archivo de configuración no existe: {config_file}", file=sys.stderr)
        return 1

    if background:
        # Lanzar el proceso desacoplado en segundo plano
        log_dir = "test_results"
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.abspath(os.path.join(log_dir, f"test_run_{ts}.log"))

        cmd = [
            sys.executable,
            os.path.abspath(__file__),
            "--config-file",
            os.path.abspath(config_file),
        ]
        if iterations is not None:
            cmd += ["--iterations", str(iterations)]
        if agent is not None:
            cmd += ["--agent", str(agent)]
        if max_steps is not None:
            cmd += ["--max-steps", str(max_steps)]
        if delay is not None:
            cmd += ["--delay", str(delay)]

        with open(log_file, "w", encoding="utf-8") as out:
            proc = subprocess.Popen(
                cmd,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                cwd=os.getcwd(),
            )

        print(f"\n[✓] Test iniciado en segundo plano con PID {proc.pid}")
        print(f"    Archivo de log: {log_file}")
        print(f"    Para monitorear el progreso simplificado en tiempo real ejecuta:")
        print(f"      tail -f {log_file}\n")
        return 0

    from controllers.test_controller import run_test_from_config

    overrides = {}
    if iterations is not None:
        overrides["num_iterations"] = iterations
    if agent is not None:
        overrides["agent_type"] = agent
    if max_steps is not None:
        overrides["max_steps"] = max_steps
    if delay is not None:
        overrides["step_delay_ms"] = delay

    try:
        session_data = run_test_from_config(config_file, overrides=overrides)
        return 0 if session_data else 1
    except KeyboardInterrupt:
        print("\n[!] Ejecución interrumpida por el usuario.")
        return 130
    except Exception as exc:
        print(f"\n[ERROR] Falló la ejecución del test: {exc}", file=sys.stderr)
        return 1


def run_gui() -> int:
    """Inicia la interfaz gráfica de usuario con PySide6."""
    from controllers.chat_controller import ChatController
    from controllers.graph_controller import GraphController
    from interface.ui import MainWindow, create_application

    print("Initializing application...")
    app = create_application()

    graph_controller = GraphController()
    chat_controller = ChatController(graph_controller)

    window = MainWindow(graph_controller, chat_controller)
    window.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TextWorld Agent Platform - Interfaz Gráfica y Benchmark Headless CLI"
    )
    parser.add_argument(
        "--config-file",
        "-c",
        type=str,
        default=None,
        help="Ruta al archivo JSON de configuración exportado para ejecutar los tests desde la terminal.",
    )
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=None,
        help="Sobrescribe el número de iteraciones/partidas a ejecutar.",
    )
    parser.add_argument(
        "--agent",
        "-a",
        type=str,
        default=None,
        help="Sobrescribe el tipo de agente ('random', 'classic_memory', 'rag_memory').",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Sobrescribe el límite máximo de pasos por partida.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=None,
        help="Delay en milisegundos entre pasos (0 para máxima velocidad).",
    )
    parser.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="Ejecuta el test desacoplado en segundo plano y redirige la salida a un archivo de log en test_results/.",
    )

    args = parser.parse_args()

    if args.config_file:
        return run_cli_test(
            config_file=args.config_file,
            iterations=args.iterations,
            agent=args.agent,
            max_steps=args.max_steps,
            delay=args.delay,
            background=args.background,
        )
    else:
        return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
