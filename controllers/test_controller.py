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

from agente.Agente import Agente
from controllers.graph_controller import GraphController


def clean_observation(obs: str) -> str:
    """Limpia el texto de observación removiendo líneas de cabecera con puntaje/turnos."""
    lines = obs.split("\n")
    cleaned = [l for l in lines if not (">" in l and "/" in l and l.strip().startswith(">"))]
    return "\n".join(cleaned).strip()


class TestRunnerWorker(QThread):
    """Worker en segundo plano para ejecutar benchmarks y suites de test del agente."""

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
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.world_config = world_config
        self.test_config = test_config
        self.max_steps = max_steps
        self.request_infos = request_infos

        self._is_cancelled: bool = False
        self.num_iterations: int = int(test_config.get("num_iterations", 5))
        self.variation_mode: str = test_config.get("variation_mode", "same_world")
        self.step_delay_ms: int = int(test_config.get("step_delay_ms", 0))

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
                # Semilla distinta por vuelta
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

    def run(self) -> None:
        try:
            self.test_started.emit(self.num_iterations)
            start_wall_time = time.time()
            results: list[dict] = []

            # Si es same_world, compilamos el juego una sola vez para máxima eficiencia
            shared_game_path: str | None = None
            if self.variation_mode == "same_world" and self.mode in {"custom", "challenge"}:
                shared_game_path = self._compile_or_get_game(0)

            total_wins = 0

            for it in range(1, self.num_iterations + 1):
                if self._is_cancelled:
                    break

                self.iteration_started.emit(it, self.num_iterations)
                it_start_time = time.time()

                game_file = shared_game_path if shared_game_path else self._compile_or_get_game(it)

                # Asegurar flags requeridos en EnvInfos
                req = EnvInfos(
                    admissible_commands=True,
                    location=True,
                    facts=True,
                    won=True,
                    lost=True,
                    score=True,
                    description=getattr(self.request_infos, "description", True),
                    inventory=getattr(self.request_infos, "inventory", True),
                )

                env_id = textworld.gym.register_game(
                    game_file,
                    max_episode_steps=self.max_steps,
                    request_infos=req,
                )
                env = textworld.gym.make(env_id)

                agent = Agente()
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
                    self.step_progress.emit(it, step_count, self.max_steps)

                    valid_cmds = infos.get("admissible_commands", ["look"])
                    action = agent.answer(clean_obs, valid_cmds)
                    transcript.append({"role": "user", "text": action})

                    obs, reward, done, infos = env.step(action)
                    clean_obs = clean_observation(obs)
                    transcript.append({"role": "agent", "text": clean_obs})

                    local_gc.update_map(infos)

                    if self.step_delay_ms > 0:
                        self.msleep(self.step_delay_ms)

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
                }
                results.append(iteration_data)
                self.iteration_completed.emit(iteration_data)

                # Calcular métricas globales intermedias y ETA
                elapsed = time.time() - start_wall_time
                avg_time_per_it = elapsed / it
                remaining_its = self.num_iterations - it
                eta = round(avg_time_per_it * remaining_its, 1)

                completed_count = len(results)
                win_rate = round((total_wins / completed_count) * 100, 1)
                avg_steps = round(sum(r["steps"] for r in results) / completed_count, 1)
                avg_score = round(sum(r["score"] for r in results) / completed_count, 2)

                self.progress_updated.emit({
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

            # Apartado extensible para métricas de agente (futuras)
            agent_metrics = {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "avg_inference_latency_ms": None,
                "api_calls": None,
                "estimated_cost_usd": None,
                "status": "pending_implementation",
            }

            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_filename = f"test_session_{timestamp_str}.json"
            saved_filepath = os.path.abspath(os.path.join("test_results", saved_filename))

            session_data = {
                "session_id": timestamp_str,
                "timestamp": datetime.now().isoformat(),
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

            self.test_finished.emit(session_data)

        except Exception as exc:
            self.test_error.emit(str(exc))


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
                sessions.append({
                    "filepath": os.path.abspath(filepath),
                    "filename": os.path.basename(filepath),
                    "timestamp": raw_ts,
                    "formatted_timestamp": format_session_timestamp(raw_ts),
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

