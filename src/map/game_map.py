from typing import Any, Optional

from src.map.hex import Hex
from src.map.painter import Painter
from src.vehicles.tank import Tank


class Map:
    def __init__(self, game_map: dict, game_state: dict, players_in_game: dict) -> None:
        self.__map: dict[Hex, dict] = {}  # in order not to import Map in Painter
        self.__painter: Optional[Painter] = None
        self.__tanks: dict[int, Tank] = {}
        self.__tank_positions: dict[int, Hex] = {}

        self.__base: list[Hex] = []
        self.__obstacles: list[Hex] = []
        self.__spawn: list[Hex] = []
        self.__light_repair: list[Hex] = []
        self.__heavy_repair: list[Hex] = []
        self.__catapult: dict[Hex, int] = {}

        self.__shoot_actions: dict[int, []] = {}
        self.__players: list = []
        self.__initialize_map(game_map, game_state, players_in_game)

    def __initialize_map(self, game_map: dict, game_state: dict, players_in_game: dict) -> None:
        self.__map = {h: {"type": "empty", "tank": None} for h in Hex.hex_spiral(Hex(0, 0, 0), game_map["size"])}
        for idx, player in players_in_game.items():
            if not player.is_observer:
                self.__players.append(player)

        for p in self.__players:
            self.__shoot_actions[p.id] = []

        for tank_id, tank_info in game_state["vehicles"].items():
            player = players_in_game[tank_info["player_id"]]
            tank = Tank(int(tank_id), tank_info, player.tank_color, player.spawn_color)
            self.__tanks[int(tank_id)] = tank
            player.add_tank(tank)
            self.__map[Hex.dict_to_hex(tank_info["spawn_position"])]["tank"] = tank
            self.__spawn.append(Hex.dict_to_hex(tank_info["spawn_position"]))

        for player in players_in_game.values():
            if not player.is_observer:
                player.reorder()

        for h, positions in game_map["content"].items():
            for position in positions:
                new_hex = Hex.dict_to_hex(position)
                if h == "base":
                    self.__map[new_hex]["type"] = "base"
                    self.__base.append(new_hex)
                elif h == "obstacle":
                    self.__map[new_hex]["type"] = "obstacle"
                    self.__obstacles.append(new_hex)
                elif h == "light_repair":
                    self.__map[new_hex]["type"] = "light_repair"
                    self.__light_repair.append(new_hex)
                elif h == "hard_repair":
                    self.__map[new_hex]["type"] = "hard_repair"
                    self.__heavy_repair.append(new_hex)
                elif h == "catapult":
                    self.__map[new_hex]["type"] = "catapult"
                    self.__catapult[new_hex] = 3
        self.__painter = Painter(self.__map, self.__players)

    def update_map(self, game_state: dict) -> None:
        for tank_id, tank_info in game_state["vehicles"].items():
            tank_id = int(tank_id)
            self.__tank_positions[tank_id] = Hex.dict_to_hex(tank_info["position"])
            server_position = Hex.dict_to_hex(tank_info["position"])
            server_hp = tank_info["health"]
            server_cp = tank_info["capture_points"]

            tank = self.__tanks[tank_id]
            tank_position = tank.get_position()
            tank_hp = tank.get_hp()
            tank_cp = tank.get_cp()

            if server_position != tank_position:
                # local movement
                self.__tank_positions[tank.get_id()] = server_position
                tank.update_position(server_position)
            if server_hp != tank_hp:
                tank.update_hp(server_hp)
            if server_cp != tank_cp:
                tank.update_cp(server_cp)

    def draw_map(self, current_turn: int, num_of_turns: int) -> None:
        self.__painter.draw(current_turn, num_of_turns)

    def get_painter(self) -> Painter:
        return self.__painter

    def get_map(self) -> dict[Hex, dict]:
        return self.__map

    def get_tank_positions(self) -> dict[int, Hex]:
        return self.__tank_positions

    def get_tanks(self) -> dict[int, Tank]:
        return self.__tanks

    def get_base(self) -> list[Hex]:
        return self.__base

    def get_obstacles(self) -> list[Hex]:
        return self.__obstacles

    def get_spawn(self) -> list[Hex]:
        return self.__spawn

    def get_catapult(self) -> dict[Hex, int]:
        return self.__catapult

    def get_heavy_repair(self) -> list[Hex]:
        return self.__heavy_repair

    def get_light_repair(self) -> list[Hex]:
        return self.__light_repair

    def get_players(self) -> list[int]:
        return self.__players

    def get_shoot_actions(self) -> dict[int, Any]:
        return self.__shoot_actions

    def catapult_check(self, tank: Tank, move_coord: Hex) -> None:
        if move_coord in self.__catapult.keys() and self.__catapult[move_coord] > 0:
            tank.set_bonus_range(1)
            self.__catapult[move_coord] -= 1

    def heavy_repair_check(self, tank: Tank, move_coord: Hex) -> None:
        tank_type = tank.get_type()
        if (tank_type == "heavy_tank" or tank_type == "at_spg") and move_coord in self.__heavy_repair:
            tank.repair()

    def light_repair_check(self, tank: Tank, move_coord: Hex) -> None:
        tank_type = tank.get_type()
        if tank_type == "medium_tank" and move_coord in self.__light_repair:
            tank.repair()
