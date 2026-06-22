import warnings
from abc import ABC

import pandapower as pp
from psycopg2.extras import execute_values
from shapely.geometry import LineString

from src.config_loader import *
from src.database.base_mixin import BaseMixin

warnings.simplefilter(action='ignore', category=UserWarning)


class GridMixin(BaseMixin, ABC):
    def __init__(self):
        super().__init__()
        self._lines_buffer = []
        self._grid_result_id_cache = {}

    def fetch_cables(self) -> list:
        query = """SELECT name,
                       r_mohm_per_km / 1000.0 as r_ohm_per_km,
                       x_mohm_per_km / 1000.0 as x_ohm_per_km,
                       max_i_a / 1000.0       as max_i_ka
                FROM equipment_data
                WHERE typ = 'Cable' \
                """
        self.cur.execute(query)
        return self.cur.fetchall()

    def get_vertices_from_bcid(
        self,
        plz: int,
        kcid: int,
        bcid: int,
        country_code: str | None = None,
    ) -> tuple[dict, int]:
        ont = self.get_ont_info_from_bc(plz, kcid, bcid, country_code)["ont_vertice_id"]

        consumer_query = """SELECT vertice_id
                            FROM buildings_tem
                            WHERE plz = %(p)s
                              AND kcid = %(k)s
                              AND bcid = %(b)s;"""
        self.cur.execute(consumer_query, {"p": plz, "k": kcid, "b": bcid})
        consumer = [t[0] for t in self.cur.fetchall()]

        connection_query = """SELECT DISTINCT connection_point
                              FROM buildings_tem
                              WHERE plz = %(p)s
                                AND kcid = %(k)s
                                AND bcid = %(b)s;"""
        self.cur.execute(connection_query, {"p": plz, "k": kcid, "b": bcid})
        connection = [t[0] for t in self.cur.fetchall()]

        vertices_query = """ SELECT DISTINCT node, agg_cost
                             FROM pgr_dijkstra(
                                     'SELECT way_id as id, source, target, cost, reverse_cost FROM ways_tem'::text,
                                     %(o)s, %(c)s::integer[], false)
                             ORDER BY agg_cost;"""
        self.cur.execute(vertices_query, {"o": ont, "c": consumer})
        data = self.cur.fetchall()
        vertice_cost_dict = {t[0]: t[1] for t in data if t[0] in consumer or t[0] in connection}

        # Find unreachable buildings (no route via road network).
        # Strict mode: do not inject synthetic straight-line distances.
        all_vertices = set(consumer + connection)
        reachable_vertices = set(vertice_cost_dict.keys())
        unreachable_vertices = all_vertices - reachable_vertices

        if unreachable_vertices:
            self.logger.warning(
                "Found %s unreachable vertices for PLZ %s, KCID %s, BCID %s; skipping synthetic distance fallback.",
                len(unreachable_vertices),
                plz,
                kcid,
                bcid,
            )

        return vertice_cost_dict, ont

    def get_ont_info_from_bc(
        self,
        plz: int,
        kcid: int,
        bcid: int,
        country_code: str | None = None,
    ) -> dict | None:

        query = """SELECT ont_vertice_id, transformer_rated_power
                   FROM grid_result
                   WHERE version_id = %(v)s
                     AND kcid = %(k)s
                     AND bcid = %(b)s
                     AND plz = %(p)s"""
        params = {"v": VERSION_ID, "p": plz, "k": kcid, "b": bcid}
        if country_code:
            query += "\n                     AND country_code = %(cc)s"
            params["cc"] = country_code
        query += "; "
        self.cur.execute(query, params)
        info = self.cur.fetchall()
        if not info:
            self.logger.debug(f"found no ont information for kcid {kcid}, bcid {bcid}")
            return None

        return {"ont_vertice_id": info[0][0], "transformer_rated_power": info[0][1]}

    def get_ont_geom_from_bcid(self, plz: int, kcid: int, bcid: int, country_code: str | None = None):
        query = """SELECT ST_X(ST_Transform(geom, 4326)), ST_Y(ST_Transform(geom, 4326))
                   FROM transformer_positions tp
                            JOIN grid_result gr
                                 ON tp.grid_result_id = gr.grid_result_id
                   WHERE gr.version_id = %(v)s
                     AND plz = %(p)s
                     AND kcid = %(k)s
                     AND bcid = %(b)s"""
        params = {"v": VERSION_ID, "p": plz, "k": kcid, "b": bcid}
        if country_code:
            query += "\n                     AND gr.country_code = %(cc)s"
            params["cc"] = country_code
        query += ";"
        self.cur.execute(query, params)
        geo = self.cur.fetchone()

        return geo

    def get_transformer_rated_power_from_bcid(
        self,
        plz: int,
        kcid: int,
        bcid: int,
        country_code: str | None = None,
    ) -> int:
        query = """SELECT transformer_rated_power
                   FROM grid_result
                   WHERE version_id = %(v)s
                     AND plz = %(p)s
                     AND kcid = %(k)s
                     AND bcid = %(b)s"""
        params = {"v": VERSION_ID, "p": plz, "k": kcid, "b": bcid}
        if country_code:
            query += "\n                     AND country_code = %(cc)s"
            params["cc"] = country_code
        query += ";"
        self.cur.execute(query, params)
        transformer_rated_power = self.cur.fetchone()[0]

        return transformer_rated_power

    def set_transformer_rated_power_exact(
        self,
        plz: int,
        kcid: int,
        bcid: int,
        transformer_rated_power: int,
        country_code: str | None = None,
    ) -> None:
        """Persist an exact transformer rating chosen during electrical validation."""
        query = """UPDATE grid_result
                   SET transformer_rated_power = %(rating)s
                   WHERE version_id = %(v)s
                     AND plz = %(p)s
                     AND kcid = %(k)s
                     AND bcid = %(b)s"""
        params = {"v": VERSION_ID, "p": plz, "k": kcid, "b": bcid, "rating": int(transformer_rated_power)}
        if country_code:
            query += "\n                     AND country_code = %(cc)s"
            params["cc"] = country_code
        query += ";"
        self.cur.execute(
            query,
            params,
        )

    def get_node_geom(self, vid: int):
        query = """SELECT ST_X(ST_Transform(geom, 4326)), ST_Y(ST_Transform(geom, 4326))
                   FROM ways_tem_vertices_pgr
                   WHERE id = %(id)s;"""
        self.cur.execute(query, {"id": vid})
        geo = self.cur.fetchone()

        return geo

    def get_nodes_geom_batch(self, vids: list[int]) -> dict[int, tuple[float, float]]:
        """Batch-fetch node geometries for a list of vertex IDs."""
        if not vids:
            return {}
        unique_vids = list(dict.fromkeys(int(v) for v in vids))
        query = """SELECT id, ST_X(ST_Transform(geom, 4326)), ST_Y(ST_Transform(geom, 4326))
                   FROM ways_tem_vertices_pgr
                   WHERE id = ANY(%(ids)s::bigint[]);"""
        self.cur.execute(query, {"ids": unique_vids})
        rows = self.cur.fetchall()
        return {int(vid): (float(x), float(y)) for vid, x, y in rows}

    def get_vertices_from_connection_points(self, connection: list) -> list:
        query = """SELECT vertice_id
                   FROM buildings_tem
                   WHERE connection_point IN %(c)s
                     AND type != 'Transformer';"""
        self.cur.execute(query, {"c": tuple(connection)})
        data = self.cur.fetchall()
        return [t[0] for t in data]

    def get_paths_to_bus(self, vertices: list, ont: int) -> dict:
        """Batch routing: find shortest paths from multiple vertices to the ont in one pgr_Dijkstra call.

        Args:
            vertices: list of source vertex IDs
            ont: target vertex ID (transformer)

        Returns:
            dict mapping each start_vid to its ordered list of path nodes
        """
        if not vertices:
            return {}
        query = """SELECT start_vid, node, seq
                   FROM pgr_Dijkstra(
                           'SELECT way_id as id, source, target, cost, reverse_cost FROM ways_tem',
                           %(v)s::integer[], %(o)s,
                           false)
                   ORDER BY start_vid, seq;"""
        self.cur.execute(query, {"v": list(map(int, vertices)), "o": ont})
        data = self.cur.fetchall()
        paths = {}
        for start_vid, node, seq in data:
            paths.setdefault(start_vid, []).append(node)
        return paths

    def get_path_to_bus(self, vertice: int, ont: int) -> list:
        """routing problem: find the shortest path from vertice to the ont (ortsnetztrafo)"""
        query = """SELECT node
                   FROM pgr_Dijkstra(
                           'SELECT way_id as id, source, target, cost, reverse_cost FROM ways_tem', %(v)s, %(o)s,
                           false);"""
        """query = WITH
                    dijkstra AS(
                        SELECT * FROM pgr_Dijkstra(
                                        'SELECT way_id, source, target, cost, reverse_cost FROM ways_tem', %(v)s, %(o)s, false)
                    ),
                        get_geom AS(
                            SELECT dijkstra. *,
                            -- adjusting directionality
                                CASE
                                    WHEN dijkstra.node = ways.source THEN geom
                                    ELSE ST_Reverse(geom)
                                END AS route_geom
                            FROM dijkstra JOIN ways ON(edge=way_id)
                            ORDER BY seq)
                        SELECT seq, cost,
                        degrees(ST_azimuth(ST_StartPoint(route_geom), ST_EndPoint(route_geom))) AS azimuth,
                        ST_AsText(route_geom),
                        route_geom
                    FROM get_geom
                    ORDER BY seq;"""
        self.cur.execute(query, {"o": ont, "v": vertice})
        data = self.cur.fetchall()
        way_list = [t[0] for t in data]

        return way_list

    def _get_grid_result_id(self, plz, kcid, bcid, country_code: str | None = None):
        """Fetch and cache grid_result_id for a (version, country, plz, kcid, bcid) tuple."""
        key = (VERSION_ID, country_code or "", str(plz), int(kcid), int(bcid))
        if key not in self._grid_result_id_cache:
            query = """SELECT grid_result_id FROM grid_result
                   WHERE version_id = %(v)s AND plz = %(plz)s AND kcid = %(kcid)s AND bcid = %(bcid)s"""
            params = {"v": key[0], "plz": key[2], "kcid": key[3], "bcid": key[4]}
            if country_code:
                query += " AND country_code = %(country_code)s"
                params["country_code"] = country_code
            self.cur.execute(query, params)
            self._grid_result_id_cache[key] = self.cur.fetchone()[0]
        return self._grid_result_id_cache[key]

    def insert_lines(self, geom: list, plz, bcid: int, kcid: int, line_name: str, std_type: str, from_bus: int,
            to_bus: int, length_km: float, country_code: str | None = None) -> None:
        """Buffers a line insertion. Call flush_lines() to write all buffered lines to the database."""
        grid_result_id = self._get_grid_result_id(plz, kcid, bcid, country_code)
        self._lines_buffer.append((
            grid_result_id,
            LineString(geom).wkb_hex,
            line_name,
            std_type,
            int(from_bus),
            int(to_bus),
            length_km,
        ))

    def flush_lines(self) -> None:
        """Bulk-insert all buffered lines into lines_result using execute_values."""
        if not self._lines_buffer:
            return
        execute_values(
            self.cur,
            """INSERT INTO lines_result
               (grid_result_id, geom, line_name, std_type, from_bus, to_bus, length_km)
               VALUES %s""",
            self._lines_buffer,
            template="(%s, ST_Transform(ST_SetSRID(%s::geometry, 4326), 3035), %s, %s, %s, %s, %s)",
            page_size=500,
        )
        self._lines_buffer.clear()

    def is_grid_generated(self, plz: int, country_code: str | None = None):
        """
        Check if grid exists.

        Args:
            plz: Postal code to be checked

        Returns:
            bool: True if record exists, False otherwise
        """
        query = """
            SELECT 1
            FROM grid_result
            WHERE version_id = %(version_id)s
              AND plz = %(plz)s
        """
        params = {"version_id": VERSION_ID, "plz": plz}
        if country_code:
            query += " AND country_code = %(country_code)s"
            params["country_code"] = country_code
        query += " LIMIT 1;"

        self.cur.execute(query, params)
        result = self.cur.fetchone()
        return result is not None
