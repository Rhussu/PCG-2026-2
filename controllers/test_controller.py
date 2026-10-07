from __future__ import annotations

import glob
import json
import os
import time
from datetime import datetime
from typing import Any

from PySide6.QtCore import QThread, Signal
from textworld import EnvInfos
import textworld.gym
import textworld.generator as tw_gen

from agente.factory import create_agent
from controllers.graph_controller import GraphController


def clean_observation(obs: str) -> str:
    """Limpia el texto de observación removiendo líneas de cabecera con puntaje/turnos."""
    lines = obs.split("\n")
    cleaned = [l for l in lines if not (">" in l and "/" in l and l.strip().startswith(">"))]
    return "\n".join(cleaned).strip()


class TestRunnerEngine:
    """Motor desacoplado para ejecutar benchmarks y suites de test de agentes TextWorld.
    Puede ejecutarse en terminal CLI pura (headless) o embebido dentro de hilos Qt.
    """

    def __init__(
        self,
        mode: str,
        world_config: dict,
        test_config: dict,
        max_steps: int = 50,
        request_infos: EnvInfos | dict | None = None,
        agent_type: str = "random",
        agent_config: dict | None = None,
        on_test_started: Callable[[int], None] | None = None,
        on_iteration_started: Callable[[int, int], None] | None = None,
        on_step_progress: Callable[[int, int, int], None] | None = None,
        on_iteration_completed: Callable[[dict], None] | None = None,
        on_progress_updated: Callable[[dict], None] | None = None,
        on_test_finished: Callable[[dict], None] | None = None,
        on_test_error: Callable[[str], None] | None = None,
    ) -> None:
        self.mode = mode
        self.world_config = dict(world_config or {})
        self.test_config = dict(test_config or {})
        self.max_steps = int(max_steps or 50)
        self.request_infos = request_infos
        self.agent_type = agent_type or self.test_config.get("agent_type", "random")
        self.agent_config = agent_config if agent_config is not None else self.test_config.get("agent_config", {})

        self._is_cancelled: bool = False
        self.num_iterations: int = int(self.test_config.get("num_iterations", 5))
        self.variation_mode: str = self.test_config.get("variation_mode", "same_world")
        self.step_delay_ms: int = int(self.test_config.get("step_delay_ms", 0))

        # Callbacks opcionales de reporte
        self.on_test_started = on_test_started
        self.on_iteration_started = on_iteration_started
        self.on_step_progress = on_step_progress
        self.on_iteration_completed = on_iteration_completed
        self.on_progress_updated = on_progress_updated
        self.on_test_finished = on_test_finished
        self.on_test_error = on_test_error

    def cancel(self) -> None:
        """Solicita la cancelación limpia del proceso de test."""
        self._is_cancelled = True

    def _compile_or_get_game(self, iteration: int) -> str:
        """Obtiene o compila el archivo .z8 para la iteración actual."""
        os.makedirs("tw", exist_ok=True)
        os.makedirs("test_results", exist_ok=True)

        if self.mode == "custom":
            opts = tw_gen.GameOptions()
            opts.nb_rooms = self.world_config["nb_rooms"]
            opts.nb_objects = self.world_config["nb_objects"]
            opts.quest_length = self.world_config["quest_length"]
            opts.quest_breadth = self.world_config["quest_breadth"]
            opts.nb_parallel_quests = self.world_config["nb_parallel_quests"]

            opts.chaining.subquests = self.world_config.get("subquests", False)
            opts.chaining.independent_chains = self.world_config.get("independent_chains", False)

            opts.grammar.theme = self.world_config.get("theme", "house")
            opts.grammar.include_adj = self.world_config.get("include_adj", False)
            opts.grammar.blend_descriptions = self.world_config.get("blend_descriptions", False)
            opts.grammar.blend_instructions = self.world_config.get("blend_instructions", False)
            opts.grammar.only_last_action = self.world_config.get("only_last_action", False)
            opts.grammar.ambiguous_instructions = self.world_config.get("ambiguous_instructions", False)
            opts.grammar.allowed_variables_numbering = self.world_config.get("entity_numbering", False)

            base_seed = self.world_config.get("seed")
            if self.variation_mode == "distinct_seeds":
                opts.seeds = (int(base_seed) if base_seed is not None else 1000) + iteration
            else:
                if base_seed is not None:
                    opts.seeds = int(base_seed)

            output_path = os.path.abspath(f"tw/test_world_{iteration if self.variation_mode == 'distinct_seeds' else 'base'}.z8")
            opts.path = output_path
            opts.force_recompile = True

            game = tw_gen.make_game(opts)
            compiled_path = tw_gen.compile_game(game, opts)
            return compiled_path

        elif self.mode == "challenge":
            import textworld.challenges as challenges
            ch_type = self.world_config.get("challenge_type", "tw-treasure_hunter")
            name, make_fn, _ = challenges.CHALLENGES[ch_type]

            opts = tw_gen.GameOptions()
            opts.path = os.path.abspath(f"tw/test_{ch_type}_{iteration if self.variation_mode == 'distinct_seeds' else 'base'}.z8")
            opts.force_recompile = True
            opts.grammar.only_last_action = self.world_config.get("only_last_action", False)

            base_seed = self.world_config.get("seed")
            if self.variation_mode == "distinct_seeds":
                opts.seeds = (int(base_seed) if base_seed is not None else 1000) + iteration
            elif base_seed is not None:
                opts.seeds = int(base_seed)

            settings = {}
            if ch_type in {"tw-treasure_hunter", "tw-coin_collector"}:
                settings["level"] = int(self.world_config.get("level", 1))

            game = make_fn(settings, opts)
            compiled_path = tw_gen.compile_game(game, opts)
            return compiled_path

        elif self.mode == "file":
            game_path = self.world_config.get("file_path", "")
            if not os.path.exists(game_path):
                raise FileNotFoundError(f"Archivo no encontrado: {game_path}")
            return game_path

        raise ValueError(f"Modo desconocido: {self.mode}")

    def run(self) -> dict:
        try:
            if self.on_test_started:
                self.on_test_started(self.num_iterations)
            start_wall_time = time.time()
            results: list[dict] = []

            # Si es same_world, compilamos el juego una sola vez para máxima eficiencia
            shared_game_path: str | None = None
            if self.variation_mode == "same_world" and self.mode in {"custom", "challenge"}:
                shared_game_path = self._compile_or_get_game(0)

            total_wins = 0
            agent = create_agent(self.agent_type, self.agent_config)

            for it in range(1, self.num_iterations + 1):
                if self._is_cancelled:
                    break

                if self.on_iteration_started:
                    self.on_iteration_started(it, self.num_iterations)
                it_start_time = time.time()

                game_file = shared_game_path if shared_game_path else self._compile_or_get_game(it)

                # Asegurar flags requeridos en EnvInfos
                desc_flag = True
                inv_flag = True
                if isinstance(self.request_infos, dict):
                    desc_flag = bool(self.request_infos.get("description", True))
                    inv_flag = bool(self.request_infos.get("inventory", True))
                elif self.request_infos is not None:
                    desc_flag = bool(getattr(self.request_infos, "description", True))
                    inv_flag = bool(getattr(self.request_infos, "inventory", True))

                req = EnvInfos(
                    admissible_commands=True,
                    location=True,
                    facts=True,
                    won=True,
                    lost=True,
                    score=True,
                    description=desc_flag,
                    inventory=inv_flag,
                )

                env_id = textworld.gym.register_game(
                    game_file,
                    max_episode_steps=self.max_steps,
                    request_infos=req,
                )
                env = textworld.gym.make(env_id)

                agent.reset()
                local_gc = GraphController()
                obs, infos = env.reset()
                clean_obs = clean_observation(obs)
                local_gc.update_map(infos)

                transcript: list[dict[str, str]] = [
                    {"role": "agent", "text": clean_obs}
                ]

                step_count = 0
                done = False
                won = False
                lost = False
                score = 0
                max_score = infos.get("max_score", 1) or 1

                while not done and step_count < self.max_steps:
                    if self._is_cancelled:
                        break

                    step_count += 1
                    if self.on_step_progress:
                        self.on_step_progress(it, step_count, self.max_steps)

                    valid_cmds = infos.get("admissible_commands", ["look"])
                    action = agent.answer(clean_obs, valid_cmds)
                    transcript.append({"role": "user", "text": action})

                    obs, reward, done, infos = env.step(action)
                    clean_obs = clean_observation(obs)
                    transcript.append({"role": "agent", "text": clean_obs})

                    local_gc.update_map(infos)

                    if self.step_delay_ms > 0:
                        time.sleep(self.step_delay_ms / 1000.0)

                env.close()

                won = bool(infos.get("won", False))
                lost = bool(infos.get("lost", False))
                score = int(infos.get("score", 0))
                it_duration = round(time.time() - it_start_time, 2)

                if won:
                    total_wins += 1
                    status_text = "Victoria"
                elif lost:
                    status_text = "Derrota"
                elif step_count >= self.max_steps:
                    status_text = "Límite de pasos"
                else:
                    status_text = "Interrumpido"

                iteration_data = {
                    "iteration": it,
                    "status": status_text,
                    "won": won,
                    "lost": lost,
                    "steps": step_count,
                    "max_steps": self.max_steps,
                    "score": score,
                    "max_score": max_score,
                    "duration": it_duration,
                    "rooms_discovered": len(local_gc.visited_rooms),
                    "total_rooms": len(local_gc.rooms_data),
                    "inventory": list(local_gc.player_inventory),
                    "transcript": transcript,
                    "map_snapshot": local_gc.get_snapshot(),
                    "representation_snapshot": agent.get_representation(),
                }
                results.append(iteration_data)
                if self.on_iteration_completed:
                    self.on_iteration_completed(iteration_data)

                # Calcular métricas globales intermedias y ETA
                elapsed = time.time() - start_wall_time
                avg_time_per_it = elapsed / it
                remaining_its = self.num_iterations - it
                eta = round(avg_time_per_it * remaining_its, 1)

                completed_count = len(results)
                win_rate = round((total_wins / completed_count) * 100, 1)
                avg_steps = round(sum(r["steps"] for r in results) / completed_count, 1)
                avg_score = round(sum(r["score"] for r in results) / completed_count, 2)

                if self.on_progress_updated:
                    self.on_progress_updated({
                        "completed": completed_count,
                        "total": self.num_iterations,
                        "percent": round((completed_count / self.num_iterations) * 100, 1),
                        "elapsed_s": round(elapsed, 1),
                        "eta_s": max(0.0, eta) if not self._is_cancelled else 0.0,
                        "wins": total_wins,
                        "win_rate": win_rate,
                        "avg_steps": avg_steps,
                        "avg_score": avg_score,
                        "is_cancelled": self._is_cancelled,
                    })

            # Generar resumen de sesión
            total_elapsed = round(time.time() - start_wall_time, 2)
            n_completed = len(results)

            if n_completed > 0:
                steps_list = [r["steps"] for r in results]
                scores_list = [r["score"] for r in results]
                rooms_list = [r["rooms_discovered"] for r in results]

                summary = {
                    "total_runs": n_completed,
                    "target_runs": self.num_iterations,
                    "status": "Cancelado" if self._is_cancelled else "Completado",
                    "total_duration_s": total_elapsed,
                    "wins": total_wins,
                    "losses": sum(1 for r in results if r["lost"]),
                    "timeouts": sum(1 for r in results if not r["won"] and not r["lost"]),
                    "win_rate_percent": round((total_wins / n_completed) * 100, 1),
                    "avg_steps": round(sum(steps_list) / n_completed, 2),
                    "min_steps": min(steps_list),
                    "max_steps": max(steps_list),
                    "avg_score": round(sum(scores_list) / n_completed, 2),
                    "max_score_achieved": max(scores_list),
                    "avg_rooms_discovered": round(sum(rooms_list) / n_completed, 1),
                    "efficiency_ratio": round(sum(scores_list) / max(1, sum(steps_list)), 4),
                }
            else:
                summary = {
                    "total_runs": 0,
                    "target_runs": self.num_iterations,
                    "status": "Cancelado sin partidas completadas",
                    "total_duration_s": total_elapsed,
                    "wins": 0,
                    "losses": 0,
                    "timeouts": 0,
                    "win_rate_percent": 0.0,
                    "avg_steps": 0,
                    "min_steps": 0,
                    "max_steps": 0,
                    "avg_score": 0.0,
                    "max_score_achieved": 0,
                    "avg_rooms_discovered": 0,
                    "efficiency_ratio": 0.0,
                }

            # Métricas acumuladas del agente durante la sesión
            agent_metrics = agent.get_metrics()

            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_filename = f"test_session_{timestamp_str}.json"
            saved_filepath = os.path.abspath(os.path.join("test_results", saved_filename))

            session_data = {
                "session_id": timestamp_str,
                "timestamp": datetime.now().isoformat(),
                "agent_type": self.agent_type,
                "agent_name": agent.name,
                "agent_config": self.agent_config,
                "mode": self.mode,
                "world_config": self.world_config,
                "test_config": self.test_config,
                "summary": summary,
                "agent_metrics": agent_metrics,
                "iterations": results,
                "saved_filepath": saved_filepath,
            }

            # Guardar en disco
            with open(saved_filepath, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            if self.on_test_finished:
                self.on_test_finished(session_data)

            return session_data

        except Exception as exc:
            if self.on_test_error:
                self.on_test_error(str(exc))
            raise


class TestRunnerWorker(QThread):
    """Worker en segundo plano para ejecutar benchmarks y suites de test del agente (PySide6)."""

    test_started = Signal(int)                          # total_iterations
    iteration_started = Signal(int, int)                # current_index (1-based), total_iterations
    step_progress = Signal(int, int, int)               # iteration_idx, current_step, max_steps
    iteration_completed = Signal(dict)                  # iteration_data
    progress_updated = Signal(dict)                     # progress_stats
    test_finished = Signal(dict)                        # session_data
    test_error = Signal(str)                            # error_message

    def __init__(
        self,
        mode: str,
        world_config: dict,
        test_config: dict,
        max_steps: int,
        request_infos: EnvInfos,
        agent_type: str = "random",
        agent_config: dict | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.world_config = world_config
        self.test_config = test_config
        self.max_steps = max_steps
        self.request_infos = request_infos
        self.agent_type = agent_type or test_config.get("agent_type", "random")
        self.agent_config = agent_config if agent_config is not None else test_config.get("agent_config", {})

        self.num_iterations: int = int(test_config.get("num_iterations", 5))
        self.variation_mode: str = test_config.get("variation_mode", "same_world")
        self.step_delay_ms: int = int(test_config.get("step_delay_ms", 0))

        self.engine = TestRunnerEngine(
            mode=self.mode,
            world_config=self.world_config,
            test_config=self.test_config,
            max_steps=self.max_steps,
            request_infos=self.request_infos,
            agent_type=self.agent_type,
            agent_config=self.agent_config,
            on_test_started=self.test_started.emit,
            on_iteration_started=self.iteration_started.emit,
            on_step_progress=self.step_progress.emit,
            on_iteration_completed=self.iteration_completed.emit,
            on_progress_updated=self.progress_updated.emit,
            on_test_finished=self.test_finished.emit,
            on_test_error=self.test_error.emit,
        )

    @property
    def _is_cancelled(self) -> bool:
        return self.engine._is_cancelled

    @_is_cancelled.setter
    def _is_cancelled(self, val: bool) -> None:
        self.engine._is_cancelled = val

    def cancel(self) -> None:
        """Solicita la cancelación limpia del proceso de test."""
        self.engine.cancel()

    def run(self) -> None:
        try:
            self.engine.run()
        except Exception:
            # El error ya fue capturado y emitido a través de on_test_error
            pass


def load_test_configuration(filepath: str) -> dict:
    """Carga y valida un archivo de configuración JSON para pruebas."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("El archivo de configuración debe contener un objeto JSON válido.")

    return data


def save_test_configuration(config_data: dict, filepath: str) -> str:
    """Guarda un diccionario de configuración de test en un archivo JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    return os.path.abspath(filepath)


def run_test_from_config(config_path: str, overrides: dict | None = None) -> dict:
    """Ejecuta una sesión de pruebas desde la terminal en modo headless y muestra el progreso simplificado."""
    import sys

    cfg = load_test_configuration(config_path)
    overrides = overrides or {}

    mode = overrides.get("mode", cfg.get("mode", "custom"))
    world_config = cfg.get("world_config", {})
    test_config = dict(cfg.get("test_config", {}))
    max_steps = int(overrides.get("max_steps", cfg.get("max_steps", 50)))
    request_infos = cfg.get("request_infos", {})

    agent_type = overrides.get(
        "agent_type",
        cfg.get("agent_type", test_config.get("agent_type", "random"))
    )
    agent_config = cfg.get("agent_config", test_config.get("agent_config", {}))

    if "num_iterations" in overrides and overrides["num_iterations"] is not None:
        test_config["num_iterations"] = int(overrides["num_iterations"])
    if "step_delay_ms" in overrides and overrides["step_delay_ms"] is not None:
        test_config["step_delay_ms"] = int(overrides["step_delay_ms"])

    num_iterations = int(test_config.get("num_iterations", 5))
    is_tty = sys.stdout.isatty()

    # Códigos ANSI simples para mejorar la visualización en terminal
    C_RESET = "\033[0m" if is_tty else ""
    C_BOLD = "\033[1m" if is_tty else ""
    C_CYAN = "\033[36m" if is_tty else ""
    C_GREEN = "\033[32m" if is_tty else ""
    C_YELLOW = "\033[33m" if is_tty else ""
    C_RED = "\033[31m" if is_tty else ""
    C_DIM = "\033[2m" if is_tty else ""

    print(f"\n{C_CYAN}{'='*75}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  TEXTWORLD AGENT BENCHMARK RUNNER (TERMINAL HEADLESS){C_RESET}")
    print(f"{C_CYAN}{'='*75}{C_RESET}")
    print(f"  {C_BOLD}Configuración :{C_RESET} {config_path}")
    print(f"  {C_BOLD}Modo          :{C_RESET} {mode}")
    print(f"  {C_BOLD}Agente        :{C_RESET} {agent_type}")
    if isinstance(agent_config, dict) and agent_config.get("llm_model"):
        print(f"  {C_BOLD}Modelo LLM    :{C_RESET} {agent_config.get('llm_model')} ({agent_config.get('llm_base_url', '')})")
    print(f"  {C_BOLD}Iteraciones   :{C_RESET} {num_iterations} partida(s)")
    print(f"  {C_BOLD}Límite pasos  :{C_RESET} {max_steps} pasos/partida")
    print(f"{C_CYAN}{'-'*75}{C_RESET}")
    print(f"  Iniciando ejecución... (Presiona Ctrl+C para detener limpiamente)\n")
    sys.stdout.flush()

    def on_iteration_started(it: int, total: int) -> None:
        if is_tty:
            sys.stdout.write(f"\r  {C_YELLOW}[{it}/{total}]{C_RESET} Ejecutando partida {it}...                              ")
            sys.stdout.flush()
        else:
            print(f"  [{it}/{total}] Ejecutando partida {it}...", flush=True)

    def on_step_progress(it: int, step: int, max_s: int) -> None:
        if is_tty and (step % 2 == 0 or step == max_s):
            sys.stdout.write(f"\r  {C_YELLOW}[{it}/{num_iterations}]{C_RESET} Paso {step}/{max_s}...                              ")
            sys.stdout.flush()

    def on_iteration_completed(data: dict) -> None:
        it = data["iteration"]
        won = data["won"]
        lost = data["lost"]
        status = data["status"]
        steps = data["steps"]
        score = data["score"]
        max_s = data["max_score"]
        dur = data["duration"]
        rooms = data["rooms_discovered"]

        if won:
            sym = f"{C_GREEN}✓ {status}{C_RESET}"
        elif lost:
            sym = f"{C_RED}✗ {status}{C_RESET}"
        else:
            sym = f"{C_YELLOW}⏱ {status}{C_RESET}"

        line = f"  [{it}/{num_iterations}] {sym} en {steps} pasos | Score: {score}/{max_s} | Salas: {rooms} | ({dur}s)"
        if is_tty:
            sys.stdout.write("\r" + " " * 75 + "\r")
        print(line, flush=True)

    def on_progress_updated(prog: dict) -> None:
        pct = prog.get("percent", 0.0)
        completed = prog.get("completed", 0)
        total = prog.get("total", num_iterations)
        wins = prog.get("wins", 0)
        rate = prog.get("win_rate", 0.0)
        elapsed = prog.get("elapsed_s", 0.0)
        eta = prog.get("eta_s", 0.0)

        filled = int(round(20 * completed / max(1, total)))
        bar = "█" * filled + "░" * (20 - filled)
        prog_line = f"  {C_DIM}Progreso: [{bar}] {pct:.1f}% ({completed}/{total}) | Victorias: {wins}/{completed} ({rate:.1f}%) | Tiempo: {elapsed}s | ETA: {eta}s{C_RESET}"
        print(prog_line, flush=True)

    engine = TestRunnerEngine(
        mode=mode,
        world_config=world_config,
        test_config=test_config,
        max_steps=max_steps,
        request_infos=request_infos,
        agent_type=agent_type,
        agent_config=agent_config,
        on_iteration_started=on_iteration_started,
        on_step_progress=on_step_progress,
        on_iteration_completed=on_iteration_completed,
        on_progress_updated=on_progress_updated,
    )

    try:
        session_data = engine.run()
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Interrupción detectada (Ctrl+C). Cancelando y guardando datos...{C_RESET}", flush=True)
        engine.cancel()
        raise
    except Exception as exc:
        print(f"\n{C_RED}[ERROR CRÍTICO] La ejecución del test se detuvo debido a un fallo en el modelo: {exc}{C_RESET}", flush=True)
        raise

    summary = session_data.get("summary", {})
    saved_path = session_data.get("saved_filepath", "")

    print(f"\n{C_CYAN}{'-'*75}{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}  RESUMEN FINAL DEL BENCHMARK:{C_RESET}")
    print(f"{C_CYAN}{'-'*75}{C_RESET}")
    print(f"  {C_BOLD}Estado              :{C_RESET} {summary.get('status', 'Completado')}")
    print(f"  {C_BOLD}Duración Total      :{C_RESET} {summary.get('total_duration_s', 0)}s")
    print(f"  {C_BOLD}Partidas            :{C_RESET} {summary.get('total_runs', 0)} / {summary.get('target_runs', num_iterations)}")
    print(f"  {C_BOLD}Victorias           :{C_RESET} {C_GREEN}{summary.get('wins', 0)}{C_RESET} ({summary.get('win_rate_percent', 0.0)}%)")
    print(f"  {C_BOLD}Derrotas            :{C_RESET} {C_RED}{summary.get('losses', 0)}{C_RESET}")
    print(f"  {C_BOLD}Límite de Pasos     :{C_RESET} {C_YELLOW}{summary.get('timeouts', 0)}{C_RESET}")
    print(f"  {C_BOLD}Pasos Promedio      :{C_RESET} {summary.get('avg_steps', 0.0)} (Mín: {summary.get('min_steps', 0)}, Máx: {summary.get('max_steps', 0)})")
    print(f"  {C_BOLD}Puntaje Promedio    :{C_RESET} {summary.get('avg_score', 0.0)}")
    print(f"  {C_BOLD}Habitaciones Prom.  :{C_RESET} {summary.get('avg_rooms_discovered', 0.0)}")
    print(f"  {C_BOLD}Ratio Eficiencia    :{C_RESET} {summary.get('efficiency_ratio', 0.0)} pts/paso")
    print(f"{C_CYAN}{'-'*75}{C_RESET}")
    print(f"  {C_BOLD}Resultados guardados en:{C_RESET}")
    print(f"  -> {C_BOLD}{saved_path}{C_RESET}")
    print(f"{C_CYAN}{'='*75}{C_RESET}\n")
    sys.stdout.flush()

    return session_data


def format_session_timestamp(timestamp_str: str) -> str:
    """Convierte un timestamp ISO o de sesión en una fecha y hora legible en español.
    Ejemplo: '2026-09-23T14:25:23.942355' -> '23/09/2026 14:25:23'
    """
    if not timestamp_str:
        return "Fecha desconocida"
    try:
        clean = timestamp_str.replace("Z", "")
        if "." in clean:
            clean = clean.split(".")[0]
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%d/%m/%Y a las %H:%M:%S")
    except Exception:
        return timestamp_str[:19].replace("T", " ")


def list_saved_test_sessions() -> list[dict]:
    """Lista las sesiones de test guardadas en el directorio test_results."""
    os.makedirs("test_results", exist_ok=True)
    files = sorted(glob.glob("test_results/test_session_*.json"), reverse=True)
    sessions = []
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                summary = data.get("summary", {})
                raw_ts = data.get("timestamp", "")
                raw_agent_type = data.get("agent_type", "random")
                raw_agent_name = data.get("agent_name") or (
                    "Agente Aleatorio (Baseline)" if raw_agent_type == "random" else raw_agent_type
                )
                sessions.append({
                    "filepath": os.path.abspath(filepath),
                    "filename": os.path.basename(filepath),
                    "timestamp": raw_ts,
                    "formatted_timestamp": format_session_timestamp(raw_ts),
                    "agent_type": raw_agent_type,
                    "agent_name": raw_agent_name,
                    "mode": data.get("mode", "unknown"),
                    "total_runs": summary.get("total_runs", 0),
                    "win_rate": summary.get("win_rate_percent", 0.0),
                    "avg_steps": summary.get("avg_steps", 0),
                })
        except Exception:
            continue
    return sessions


def load_test_session(filepath: str) -> dict:
    """Carga una sesión guardada desde un archivo JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

