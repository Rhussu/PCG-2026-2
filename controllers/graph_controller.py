from __future__ import annotations

from collections import deque
import re


class GraphController:
    """Controlador que procesa los hechos (facts) y estado de TextWorld,
    generando una representación espacial y ontológica detallada del mundo.
    """

    def __init__(self) -> None:
        self.room_coords: dict[str, tuple[float, float]] = {}
        self.grid_coords: dict[str, tuple[int, int]] = {}
        self.connections: list[dict] = []
        self.raw_connections: list[tuple[str, str]] = []
        self.current_room: str = ""
        self.visited_rooms: set[str] = set()

        # Datos detallados del estado del mundo
        self.rooms_data: dict[str, dict] = {}
        self.doors_data: dict[tuple[str, str], dict] = {}
        self.player_inventory: list[str] = []
        self.matching_keys: dict[str, str] = {}  # key -> target (container o puerta)

    def reset(self) -> None:
        """Reinicia el estado del grafo, habitaciones, entidades y salas visitadas."""
        self.room_coords.clear()
        self.grid_coords.clear()
        self.connections.clear()
        self.raw_connections.clear()
        self.current_room = ""
        self.visited_rooms.clear()
        self.rooms_data.clear()
        self.doors_data.clear()
        self.player_inventory.clear()
        self.matching_keys.clear()

    @staticmethod
    def _clean_name(value: object) -> str:
        """Limpia el nombre de entidades removiendo prefijos/sufijos y comillas."""
        if hasattr(value, "name"):
            name = str(value.name)
        else:
            name = str(value)
        name = name.strip()
        if name.startswith("'") and name.endswith("'"):
            name = name[1:-1]
        name = re.sub(r"\s*:\s*[a-z]$", "", name)
        return name

    @classmethod
    def _extract_arg_and_type(cls, arg: object) -> tuple[str, str | None]:
        """Extrae el nombre limpio y el tipo ('r', 'c', 's', 'd', 'k', 'f', 'o', etc.)."""
        raw_str = str(arg).strip()
        arg_type = getattr(arg, "type", None)
        if not arg_type:
            type_match = re.search(r":\s*([a-z])\b", raw_str)
            if type_match:
                arg_type = type_match.group(1)
        name = cls._clean_name(raw_str)
        return name, arg_type

    def _room_from_facts(self, facts: list[object]) -> str:
        for fact in facts:
            if hasattr(fact, "name") and fact.name == "at":
                args = fact.arguments
                if len(args) >= 2 and self._clean_name(args[0]) == "P":
                    return self._clean_name(args[1])
            else:
                match = re.search(r"\bat\(P\s*,\s*([^\)]+)\)", str(fact))
                if match:
                    return self._clean_name(match.group(1))
        return "Desconocido"

    def update_map(self, infos: dict) -> None:
        """Parsea los hechos del entorno TextWorld y actualiza la representación
        espacial y el inventario del mundo.
        """
        facts = infos.get("facts", [])
        location = infos.get("location")
        self.current_room = self._clean_name(location) if location else self._room_from_facts(facts)

        if self.current_room and self.current_room != "Desconocido":
            self.visited_rooms.add(self.current_room)

        # Estructuras temporales para parsear el estado actual
        all_rooms: set[str] = set()
        spatial_relations: list[tuple[str, str, str]] = []  # (dir, r1, r2)
        raw_conns: set[tuple[str, str]] = set()

        # Entidades y relaciones
        containers_by_room: dict[str, set[str]] = {}
        supporters_by_room: dict[str, set[str]] = {}
        items_by_room: dict[str, list[dict]] = {}  # {room: [{"name": str, "type": str}]}

        container_contents: dict[str, list[str]] = {}
        supporter_contents: dict[str, list[str]] = {}
        inventory_items: list[str] = []

        closed_entities: set[str] = set()
        open_entities: set[str] = set()
        locked_entities: set[str] = set()
        doors_between: dict[tuple[str, str], str] = {}  # (r1, r2) -> door_name
        matches: dict[str, str] = {}

        # 1. Procesar todos los hechos (facts)
        for fact in facts:
            fact_name = getattr(fact, "name", None)
            arguments = getattr(fact, "arguments", None)

            if fact_name and arguments is not None:
                fact_predicate = str(fact_name)
                args_extracted = [self._extract_arg_and_type(arg) for arg in arguments]
            else:
                fact_str = str(fact)
                match_pred = re.match(r"^([a-z_]+)\((.*)\)$", fact_str.strip())
                if not match_pred:
                    continue
                fact_predicate = match_pred.group(1)
                args_raw = [a.strip() for a in match_pred.group(2).split(",") if a.strip()]
                args_extracted = [self._extract_arg_and_type(a) for a in args_raw]

            arg_names = [name for name, _ in args_extracted]
            arg_types = [t for _, t in args_extracted]

            # Direcciones cardinales: dir_of(r1, r2) significa r1 está al <dir> de r2
            if fact_predicate in {"north_of", "south_of", "east_of", "west_of"} and len(arg_names) >= 2:
                direction = fact_predicate.replace("_of", "")
                r1, r2 = arg_names[0], arg_names[1]
                spatial_relations.append((direction, r1, r2))
                raw_conns.add(tuple(sorted((r1, r2))))
                all_rooms.add(r1)
                all_rooms.add(r2)

            # Localización en sala: at(ent, room)
            elif fact_predicate == "at" and len(arg_names) >= 2:
                ent, loc = arg_names[0], arg_names[1]
                ent_type = arg_types[0]
                if ent == "P":
                    all_rooms.add(loc)
                    continue

                all_rooms.add(loc)
                if ent_type == "c":
                    containers_by_room.setdefault(loc, set()).add(ent)
                elif ent_type == "s":
                    supporters_by_room.setdefault(loc, set()).add(ent)
                else:
                    item_category = "key" if ent_type == "k" else ("food" if ent_type == "f" else "object")
                    items_by_room.setdefault(loc, []).append({"name": ent, "category": item_category})

            # Contenido: in(item, container_or_I)
            elif fact_predicate == "in" and len(arg_names) >= 2:
                item, holder = arg_names[0], arg_names[1]
                if holder == "I":
                    inventory_items.append(item)
                else:
                    container_contents.setdefault(holder, []).append(item)

            # Superficie: on(item, supporter)
            elif fact_predicate == "on" and len(arg_names) >= 2:
                item, supp = arg_names[0], arg_names[1]
                supporter_contents.setdefault(supp, []).append(item)

            # Puertas conectando salas: link(r1, door, r2)
            elif fact_predicate == "link" and len(arg_names) >= 3:
                r1, door_name, r2 = arg_names[0], arg_names[1], arg_names[2]
                doors_between[(r1, r2)] = door_name
                doors_between[(r2, r1)] = door_name
                raw_conns.add(tuple(sorted((r1, r2))))
                all_rooms.add(r1)
                all_rooms.add(r2)

            # Estados
            elif fact_predicate == "closed" and arg_names:
                closed_entities.add(arg_names[0])
            elif fact_predicate == "open" and arg_names:
                open_entities.add(arg_names[0])
            elif fact_predicate == "locked" and arg_names:
                locked_entities.add(arg_names[0])
            elif fact_predicate == "match" and len(arg_names) >= 2:
                matches[arg_names[0]] = arg_names[1]

        # Guardar inventario
        self.player_inventory = sorted(inventory_items)
        self.matching_keys = matches
        self.raw_connections = sorted(raw_conns)

        if self.current_room and self.current_room != "Desconocido":
            all_rooms.add(self.current_room)

        # 2. Construir mapa de adyacencia y calcular Layout en rejilla con BFS
        self._calculate_grid_layout(all_rooms, spatial_relations)

        # 3. Construir datos completos de cada sala y conexiones con puertas
        self.rooms_data.clear()
        self.doors_data.clear()

        # Construir información de puertas
        for (r1, r2), door_name in doors_between.items():
            if door_name in locked_entities:
                door_state = "locked"
            elif door_name in open_entities:
                door_state = "open"
            else:
                door_state = "closed"

            matching_key = next((k for k, target in matches.items() if target == door_name), None)
            self.doors_data[(r1, r2)] = {
                "door_name": door_name,
                "state": door_state,
                "matching_key": matching_key,
            }

        # Construir datos de cada sala
        for room in all_rooms:
            room_containers = []
            for c_name in sorted(containers_by_room.get(room, set())):
                c_state = "locked" if c_name in locked_entities else ("open" if c_name in open_entities else "closed")
                c_items = container_contents.get(c_name, [])
                c_key = next((k for k, target in matches.items() if target == c_name), None)
                room_containers.append({
                    "name": c_name,
                    "state": c_state,
                    "is_open": c_state == "open",
                    "is_locked": c_state == "locked",
                    "items": sorted(c_items),
                    "matching_key": c_key,
                })

            room_supporters = []
            for s_name in sorted(supporters_by_room.get(room, set())):
                s_items = supporter_contents.get(s_name, [])
                room_supporters.append({
                    "name": s_name,
                    "items": sorted(s_items),
                })

            room_items = items_by_room.get(room, [])

            # Salidas desde esta sala
            exits = []
            for dir_name, r1, r2 in spatial_relations:
                if r2 == room:
                    # r1 está al <dir_name> de esta sala
                    door_info = self.doors_data.get((room, r1))
                    exits.append({
                        "direction": dir_name,
                        "target_room": r1,
                        "is_door": door_info is not None,
                        "door_name": door_info["door_name"] if door_info else None,
                        "door_state": door_info["state"] if door_info else "free",
                    })

            self.rooms_data[room] = {
                "name": room,
                "is_current": room == self.current_room,
                "visited": room in self.visited_rooms,
                "containers": room_containers,
                "supporters": room_supporters,
                "items": room_items,
                "exits": exits,
                "grid_coord": self.grid_coords.get(room, (0, 0)),
                "coord": self.room_coords.get(room, (50.0, 50.0)),
            }

        # Construir lista de conexiones enriquecidas
        self.connections.clear()
        for r1, r2 in self.raw_connections:
            if r1 in self.room_coords and r2 in self.room_coords:
                door_info = self.doors_data.get((r1, r2))
                is_door = door_info is not None
                door_name = door_info["door_name"] if door_info else None
                door_state = door_info["state"] if door_info else "free"
                matching_key = door_info.get("matching_key") if door_info else None

                self.connections.append({
                    "r1": r1,
                    "r2": r2,
                    "start": self.room_coords[r1],
                    "end": self.room_coords[r2],
                    "is_door": is_door,
                    "door_name": door_name,
                    "door_state": door_state,
                    "matching_key": matching_key,
                })

    def _calculate_grid_layout(
        self,
        rooms: set[str],
        spatial_relations: list[tuple[str, str, str]],
    ) -> None:
        """Calcula coordenadas discretas (gx, gy) para cada sala mediante BFS,
        garantizando que no se superpongan y reflejen fielmente la orientación cardinal.
        """
        if not rooms:
            return

        adj: dict[str, list[tuple[str, int, int]]] = {r: [] for r in rooms}
        for d, r1, r2 in spatial_relations:
            if r1 not in adj or r2 not in adj:
                continue
            # north_of(r1, r2): r1 está al norte de r2 => r1.y = r2.y - 1
            if d == "north":
                adj[r2].append((r1, 0, -1))
                adj[r1].append((r2, 0, 1))
            elif d == "south":
                adj[r2].append((r1, 0, 1))
                adj[r1].append((r2, 0, -1))
            elif d == "east":
                adj[r2].append((r1, 1, 0))
                adj[r1].append((r2, -1, 0))
            elif d == "west":
                adj[r2].append((r1, -1, 0))
                adj[r1].append((r2, 1, 0))

        start_room = self.current_room if self.current_room in rooms else next(iter(rooms))
        coords: dict[str, tuple[int, int]] = {start_room: (0, 0)}
        occupied: set[tuple[int, int]] = {(0, 0)}

        queue = deque([start_room])
        while queue:
            curr = queue.popleft()
            cx, cy = coords[curr]
            for nxt, dx, dy in adj[curr]:
                if nxt not in coords:
                    target_pos = (cx + dx, cy + dy)
                    # En caso de colisión planar inesperada en el mundo generado:
                    if target_pos in occupied:
                        # Buscar la celda vecina disponible más cercana
                        shift_y = 1
                        while (target_pos[0], target_pos[1] + shift_y) in occupied:
                            shift_y += 1
                        target_pos = (target_pos[0], target_pos[1] + shift_y)

                    coords[nxt] = target_pos
                    occupied.add(target_pos)
                    queue.append(nxt)

        # Salas aisladas (si existieran)
        for r in rooms:
            if r not in coords:
                # Asignar posición adyacente libre
                pos_x = max((c[0] for c in coords.values()), default=0) + 1
                coords[r] = (pos_x, 0)

        self.grid_coords = coords

        # Convertir a coordenadas normalizadas 0-100 para compatibilidad hacia atrás
        min_x = min(c[0] for c in coords.values())
        max_x = max(c[0] for c in coords.values())
        min_y = min(c[1] for c in coords.values())
        max_y = max(c[1] for c in coords.values())

        span_x = max(1, max_x - min_x)
        span_y = max(1, max_y - min_y)

        self.room_coords.clear()
        for r, (gx, gy) in coords.items():
            norm_x = 15.0 + ((gx - min_x) / span_x) * 70.0
            norm_y = 15.0 + ((gy - min_y) / span_y) * 70.0
            self.room_coords[r] = (round(norm_x, 2), round(norm_y, 2))

    def get_world_state(self) -> dict:
        """Devuelve una vista completa y estructurada del estado del mundo."""
        return {
            "current_room": self.current_room,
            "visited_rooms": sorted(self.visited_rooms),
            "inventory": self.player_inventory,
            "rooms": self.rooms_data,
            "doors": self.doors_data,
            "connections": self.connections,
            "grid_coords": self.grid_coords,
        }

    def get_primitives(self) -> dict[str, list[dict]]:
        """Devuelve las primitivas gráficas enriquecidas para MapPanel."""
        lines = []
        for conn in self.connections:
            color = "#444444"
            if conn["is_door"]:
                if conn["door_state"] == "locked":
                    color = "#e06c75"
                elif conn["door_state"] == "open":
                    color = "#98c379"
                else:
                    color = "#e5c07b"

            lines.append({
                "start": conn["start"],
                "end": conn["end"],
                "color": color,
                "width": 2.5 if conn["is_door"] else 2.0,
                "is_door": conn["is_door"],
                "door_name": conn["door_name"],
                "door_state": conn["door_state"],
                "r1": conn["r1"],
                "r2": conn["r2"],
            })

        rectangles = []
        for room, data in self.rooms_data.items():
            x, y = data["coord"]
            is_current = data["is_current"]
            visited = data["visited"]

            color = "#61afef" if is_current else ("#282c34" if visited else "#1e2227")

            rectangles.append({
                "x": x - 7.0,
                "y": y - 5.0,
                "width": 14.0,
                "height": 10.0,
                "color": color,
                "room": room,
                "center": (x, y),
                "grid_coord": data["grid_coord"],
                "is_current": is_current,
                "visited": visited,
                "containers": data["containers"],
                "supporters": data["supporters"],
                "items": data["items"],
                "exits": data["exits"],
            })

        return {
            "circles": [],
            "rectangles": rectangles,
            "triangles": [],
            "lines": lines,
            "world_state": self.get_world_state(),
        }