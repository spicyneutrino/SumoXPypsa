"""
Agentic Tools Module — OpenAI Function Calling Definitions + Executor

This module defines:
1. TOOL_DEFINITIONS: JSON schemas for OpenAI's function calling API
2. ToolExecutor: Maps tool names to actual system method calls

The LLM sees the schemas and decides which tools to call.
Your code uses ToolExecutor to execute the calls and return results.
"""

import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional


# =============================================================================
# 1. TOOL DEFINITIONS — OpenAI Function Calling Schemas
# =============================================================================

TOOL_DEFINITIONS = [
    # -------------------------------------------------------------------------
    # SUBSTATION CONTROL
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "fail_substation",
            "description": "Simulate a failure at a substation, taking it offline. This causes cascading effects: connected traffic lights go to caution mode and EV charging stations lose power. Use this to test grid resilience.",
            "parameters": {
                "type": "object",
                "properties": {
                    "substation": {
                        "type": "string",
                        "description": "Name of the substation to fail (e.g. 'Times Square', 'Penn Station')"
                    }
                },
                "required": ["substation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restore_substation",
            "description": "Restore a failed substation back to operational status. This brings connected traffic lights and EV stations back online, and automatically disables any active V2G sessions for that substation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "substation": {
                        "type": "string",
                        "description": "Name of the substation to restore"
                    }
                },
                "required": ["substation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restore_all_substations",
            "description": "Restore ALL failed substations at once. Use when multiple substations are down and the user wants to reset the grid.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    # -------------------------------------------------------------------------
    # V2G (Vehicle-to-Grid) CONTROL
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "enable_v2g",
            "description": "Enable Vehicle-to-Grid (V2G) energy trading for a FAILED substation. EVs near the substation will feed power back to the grid to partially restore service. The substation must be failed/offline for V2G to be activated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "substation": {
                        "type": "string",
                        "description": "Name of the failed substation to enable V2G for"
                    }
                },
                "required": ["substation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disable_v2g",
            "description": "Disable V2G energy trading for a substation and release all participating vehicles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "substation": {
                        "type": "string",
                        "description": "Name of the substation to disable V2G for"
                    }
                },
                "required": ["substation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_v2g_status",
            "description": "Get the current V2G system status including active sessions, total capacity, energy delivered, and participating vehicles.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    # -------------------------------------------------------------------------
    # SIMULATION CONTROL (SUMO)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "start_simulation",
            "description": "Start the SUMO traffic simulation with vehicles on Manhattan streets. You can specify the number of vehicles and EV percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_count": {
                        "type": "integer",
                        "description": "Number of vehicles to spawn (default: 50, max: 500)",
                        "default": 50
                    },
                    "ev_percentage": {
                        "type": "integer",
                        "description": "Percentage of vehicles that are electric (0-100, default: 70)",
                        "default": 70
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_simulation",
            "description": "Stop the SUMO traffic simulation. All vehicles will be removed from the map.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_vehicles",
            "description": "Spawn additional vehicles into the running simulation. The simulation must be running first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of additional vehicles to spawn (default: 50)",
                        "default": 50
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_simulation_speed",
            "description": "Set the simulation speed multiplier. 1.0 = real-time, 2.0 = 2x speed, 0.5 = half speed. Range: 0.1 to 10.0.",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "number",
                        "description": "Speed multiplier (0.1 to 10.0)"
                    }
                },
                "required": ["speed"]
            }
        }
    },

    # -------------------------------------------------------------------------
    # SCENARIO CONTROL (Time, Temperature, Scenarios)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "set_time",
            "description": "Set the simulation time of day. This affects power load patterns (morning rush, evening peak, etc.), lighting, and grid stress levels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hour": {
                        "type": "number",
                        "description": "Hour of day (0-23, e.g. 8 for 8 AM, 20 for 8 PM)"
                    },
                    "minute": {
                        "type": "integer",
                        "description": "Minute (0-59, default: 0)",
                        "default": 0
                    }
                },
                "required": ["hour"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_temperature",
            "description": "Set the ambient temperature in Fahrenheit. Extreme temperatures (>90°F or <30°F) increase grid load due to AC/heating demand and can trigger substation overloads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {
                        "type": "number",
                        "description": "Temperature in degrees Fahrenheit (e.g. 72 for normal, 98 for heatwave, 15 for extreme cold)"
                    }
                },
                "required": ["temperature"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_scenario",
            "description": "Run a predefined test scenario that sets time, temperature, and vehicle count to simulate specific conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "enum": [
                            "rush_hour_stress_test",
                            "evening_peak_v2g",
                            "winter_emergency",
                            "summer_heatwave",
                            "late_night_low_load"
                        ],
                        "description": "Name of the scenario to run"
                    }
                },
                "required": ["scenario"]
            }
        }
    },

    # -------------------------------------------------------------------------
    # EV CONFIGURATION
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "configure_ev",
            "description": "Configure EV (Electric Vehicle) parameters for the simulation: what percentage of vehicles are electric and their battery SOC (State of Charge) range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ev_percentage": {
                        "type": "integer",
                        "description": "Percentage of vehicles that are electric (0-100)",
                        "default": 70
                    },
                    "battery_min_soc": {
                        "type": "integer",
                        "description": "Minimum battery state of charge percentage (1-100)",
                        "default": 20
                    },
                    "battery_max_soc": {
                        "type": "integer",
                        "description": "Maximum battery state of charge percentage (1-100)",
                        "default": 90
                    }
                },
                "required": []
            }
        }
    },

    # -------------------------------------------------------------------------
    # SYSTEM STATUS & QUERIES
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get comprehensive system status: substations (online/offline, load levels), SUMO simulation state, vehicle counts, and scenario info.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_scenario_status",
            "description": "Get current scenario state including time of day, temperature, load levels per substation, and any active warnings or failures.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_substation_details",
            "description": "Get detailed information about a specific substation including load level, capacity, operational status, connected EV stations, and traffic lights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "substation": {
                        "type": "string",
                        "description": "Name of the substation to get details for"
                    }
                },
                "required": ["substation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_load_forecast",
            "description": "Get a load forecast for the next N hours showing predicted power demand across all substations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to forecast (default: 6)",
                        "default": 6
                    }
                },
                "required": []
            }
        }
    },

    # -------------------------------------------------------------------------
    # MAP CONTROL
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "focus_map",
            "description": "Focus the map view on a specific location, substation, or EV station. The map will fly to and highlight the location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name to focus on (e.g. 'Times Square', 'Penn Station', 'Central Park', 'Grand Central')"
                    }
                },
                "required": ["location"]
            }
        }
    },

    # -------------------------------------------------------------------------
    # TEST SCENARIOS
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "run_ev_rush_test",
            "description": "Run an EV rush hour test: spawns many low-battery EVs to stress the charging infrastructure. Requires SUMO to be running.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_v2g_test",
            "description": "Run a complete V2G test scenario: fails a substation, enables V2G, and monitors the restoration process.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]


# =============================================================================
# 2. TOOL EXECUTOR — Maps tool names to actual system calls
# =============================================================================

class ToolExecutor:
    """
    Executes tool calls by mapping tool names to internal system methods.
    All calls are direct Python method invocations (same process, no HTTP).
    """

    def __init__(self, integrated_system, v2g_manager, sumo_manager,
                 power_grid, system_state, scenario_controller=None,
                 current_ev_config=None, vehicle_spawn_queue=None):
        self.integrated_system = integrated_system
        self.v2g_manager = v2g_manager
        self.sumo_manager = sumo_manager
        self.power_grid = power_grid
        self.system_state = system_state
        self.scenario_controller = scenario_controller
        self.current_ev_config = current_ev_config or {}
        self.vehicle_spawn_queue = vehicle_spawn_queue

        # Map tool names → handler methods
        self.handlers = {
            # Substation Control
            "fail_substation": self._fail_substation,
            "restore_substation": self._restore_substation,
            "restore_all_substations": self._restore_all_substations,
            # V2G Control
            "enable_v2g": self._enable_v2g,
            "disable_v2g": self._disable_v2g,
            "get_v2g_status": self._get_v2g_status,
            # Simulation Control
            "start_simulation": self._start_simulation,
            "stop_simulation": self._stop_simulation,
            "spawn_vehicles": self._spawn_vehicles,
            "set_simulation_speed": self._set_simulation_speed,
            # Scenario Control
            "set_time": self._set_time,
            "set_temperature": self._set_temperature,
            "run_scenario": self._run_scenario,
            # EV Configuration
            "configure_ev": self._configure_ev,
            # Status & Queries
            "get_system_status": self._get_system_status,
            "get_scenario_status": self._get_scenario_status,
            "get_substation_details": self._get_substation_details,
            "get_load_forecast": self._get_load_forecast,
            # Map Control
            "focus_map": self._focus_map,
            # Test Scenarios
            "run_ev_rush_test": self._run_ev_rush_test,
            "run_v2g_test": self._run_v2g_test,
        }

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool by name. Returns a result dict."""
        handler = self.handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            result = handler(**arguments)
            print(f"[TOOL EXECUTOR] {tool_name}({arguments}) → success={result.get('success', 'N/A')}")
            return result
        except Exception as e:
            print(f"[TOOL EXECUTOR] {tool_name}({arguments}) → ERROR: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SUBSTATION CONTROL
    # =========================================================================

    def _fail_substation(self, substation: str) -> dict:
        """Take a substation offline — mirrors /api/fail/<substation>"""
        # Validate
        if substation not in self.integrated_system.substations:
            available = list(self.integrated_system.substations.keys())
            return {"success": False, "error": f"Substation '{substation}' not found. Available: {available}"}

        sub_data = self.integrated_system.substations[substation]
        if not sub_data.get('operational', True):
            return {"success": False, "error": f"{substation} is already offline"}

        # Execute failure
        impact = self.integrated_system.simulate_substation_failure(substation)
        self.power_grid.trigger_failure('substation', substation)

        # Update SUMO traffic lights if running
        if self.system_state.get('sumo_running') and self.sumo_manager.running:
            self.sumo_manager.update_traffic_lights()
            if hasattr(self.sumo_manager, 'handle_blackout_traffic_lights'):
                self.sumo_manager.handle_blackout_traffic_lights([substation])

            # Update affected EV stations
            for ev_id, ev_station in self.integrated_system.ev_stations.items():
                if ev_station['substation'] == substation:
                    ev_station['operational'] = False
                    if ev_id in getattr(self.sumo_manager, 'ev_stations_sumo', {}):
                        self.sumo_manager.ev_stations_sumo[ev_id]['available'] = 0
                    if hasattr(self.sumo_manager, 'station_manager') and self.sumo_manager.station_manager:
                        if ev_id in self.sumo_manager.station_manager.stations:
                            self.sumo_manager.station_manager.stations[ev_id]['operational'] = False
                            self.sumo_manager.station_manager.handle_blackout(substation)

        return {
            "success": True,
            "substation": substation,
            "action": "failed",
            "traffic_lights_affected": impact.get('traffic_lights_affected', 0),
            "ev_stations_affected": impact.get('ev_stations_affected', 0),
            "load_lost_mw": impact.get('load_lost_mw', 0),
            "map_action": {
                "type": "highlight_failure",
                "location": substation,
                "coords": sub_data.get('coords', sub_data.get('location', []))
            }
        }

    def _restore_substation(self, substation: str) -> dict:
        """Restore a substation — mirrors /api/restore/<substation>"""
        if substation not in self.integrated_system.substations:
            available = list(self.integrated_system.substations.keys())
            return {"success": False, "error": f"Substation '{substation}' not found. Available: {available}"}

        sub_data = self.integrated_system.substations[substation]
        if sub_data.get('operational', True):
            return {"success": False, "error": f"{substation} is already operational"}

        success = self.integrated_system.restore_substation(substation)
        if not success:
            return {"success": False, "error": f"Failed to restore {substation}"}

        self.power_grid.restore_component('substation', substation)
        self.v2g_manager.disable_v2g_for_substation(substation)

        lights_restored = 0
        ev_stations_restored = 0

        if self.system_state.get('sumo_running') and self.sumo_manager.running:
            self.sumo_manager.update_traffic_lights()
            for ev_id, ev_station in self.integrated_system.ev_stations.items():
                if ev_station['substation'] == substation:
                    ev_station['operational'] = True
                    ev_stations_restored += 1
                    if ev_id in getattr(self.sumo_manager, 'ev_stations_sumo', {}):
                        self.sumo_manager.ev_stations_sumo[ev_id]['available'] = ev_station['chargers']

        return {
            "success": True,
            "substation": substation,
            "action": "restored",
            "lights_restored": lights_restored,
            "ev_stations_restored": ev_stations_restored,
            "map_action": {
                "type": "highlight_restore",
                "location": substation,
                "coords": sub_data.get('coords', sub_data.get('location', []))
            }
        }

    def _restore_all_substations(self) -> dict:
        """Restore all failed substations"""
        restored = []
        already_online = []
        for name, sub_data in self.integrated_system.substations.items():
            if not sub_data.get('operational', True):
                result = self._restore_substation(name)
                if result.get('success'):
                    restored.append(name)
            else:
                already_online.append(name)

        if not restored:
            return {"success": True, "message": "All substations are already online", "restored": []}

        return {
            "success": True,
            "restored": restored,
            "count": len(restored),
            "already_online": already_online
        }

    # =========================================================================
    # V2G CONTROL
    # =========================================================================

    def _enable_v2g(self, substation: str) -> dict:
        """Enable V2G for a failed substation"""
        if substation not in self.integrated_system.substations:
            return {"success": False, "error": f"Substation '{substation}' not found"}

        sub_data = self.integrated_system.substations[substation]
        if sub_data.get('operational', True):
            return {"success": False, "error": f"{substation} is operational — V2G is only for failed substations"}

        success = self.v2g_manager.enable_v2g_for_substation(substation)
        if not success:
            return {"success": False, "error": f"Failed to enable V2G for {substation}"}

        power_needed = sub_data.get('load_mw', 0)
        rate = self.v2g_manager.get_current_rate(substation)
        energy_needed = self.v2g_manager.substation_energy_required.get(substation, 50)

        return {
            "success": True,
            "substation": substation,
            "action": "v2g_enabled",
            "power_needed_mw": power_needed,
            "energy_needed_kwh": energy_needed,
            "rate_per_kwh": rate,
            "vehicles_needed": max(2, int(energy_needed / 30) + 1)
        }

    def _disable_v2g(self, substation: str) -> dict:
        """Disable V2G for a substation"""
        if substation not in self.integrated_system.substations:
            return {"success": False, "error": f"Substation '{substation}' not found"}

        self.v2g_manager.disable_v2g_for_substation(substation)
        return {"success": True, "substation": substation, "action": "v2g_disabled"}

    def _get_v2g_status(self) -> dict:
        """Get V2G dashboard data"""
        try:
            v2g_data = self.v2g_manager.get_v2g_dashboard_data()
            status = self.v2g_manager.get_v2g_status()
            return {
                "success": True,
                "active_sessions": status.get('active_sessions', 0),
                "total_v2g_capacity_kw": status.get('total_v2g_capacity_kw', 0),
                "total_energy_delivered_kwh": status.get('total_energy_delivered_kwh', 0),
                "substations_with_v2g": status.get('substations_with_v2g', []),
                "dashboard": v2g_data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SIMULATION CONTROL
    # =========================================================================

    def _start_simulation(self, vehicle_count: int = 50, ev_percentage: int = 70) -> dict:
        """Start SUMO traffic simulation"""
        if self.system_state.get('sumo_running'):
            return {"success": False, "error": "Simulation is already running"}

        try:
            vehicle_count = max(1, min(500, vehicle_count))
            ev_pct = max(0, min(100, ev_percentage)) / 100.0

            success = self.sumo_manager.start(
                vehicle_count=vehicle_count,
                ev_percentage=ev_pct
            )

            if success:
                self.system_state['sumo_running'] = True
                return {
                    "success": True,
                    "vehicle_count": vehicle_count,
                    "ev_percentage": ev_percentage,
                    "message": f"Simulation started with {vehicle_count} vehicles ({ev_percentage}% electric)"
                }
            else:
                return {"success": False, "error": "SUMO failed to start"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _stop_simulation(self) -> dict:
        """Stop SUMO simulation"""
        if not self.system_state.get('sumo_running'):
            return {"success": False, "error": "Simulation is not running"}

        try:
            self.sumo_manager.stop()
            self.system_state['sumo_running'] = False
            return {"success": True, "message": "Simulation stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _spawn_vehicles(self, count: int = 50) -> dict:
        """Spawn additional vehicles into running simulation"""
        if not self.system_state.get('sumo_running'):
            return {"success": False, "error": "Simulation is not running. Start it first."}

        count = max(1, min(500, count))

        # Use the spawn queue (async, non-blocking)
        if self.vehicle_spawn_queue is not None:
            self.vehicle_spawn_queue.append({
                'count': count,
                'timestamp': datetime.now().isoformat()
            })
            return {"success": True, "count": count, "message": f"Queued {count} vehicles for spawning"}
        else:
            # Direct spawn
            try:
                self.sumo_manager.spawn_vehicles(count)
                return {"success": True, "count": count, "message": f"Spawned {count} vehicles"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _set_simulation_speed(self, speed: float) -> dict:
        """Set simulation speed multiplier"""
        speed = max(0.1, min(10.0, speed))
        self.system_state['simulation_speed'] = speed
        return {"success": True, "speed": speed, "message": f"Simulation speed set to {speed}x"}

    # =========================================================================
    # SCENARIO CONTROL
    # =========================================================================

    def _set_time(self, hour: float, minute: int = 0) -> dict:
        """Set simulation time of day"""
        if not self.scenario_controller:
            return {"success": False, "error": "Scenario controller not available"}

        try:
            hour = max(0, min(23.99, hour))
            minute = max(0, min(59, minute))
            result = self.scenario_controller.set_time(hour, minute, 0)
            return {
                "success": True,
                "hour": hour,
                "minute": minute,
                "time_description": result.get('description', f"{int(hour):02d}:{minute:02d}"),
                **{k: v for k, v in result.items() if k != 'description'}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _set_temperature(self, temperature: float) -> dict:
        """Set ambient temperature"""
        if not self.scenario_controller:
            return {"success": False, "error": "Scenario controller not available"}

        try:
            result = self.scenario_controller.set_temperature(temperature)
            warning = None
            if temperature > 90:
                warning = "High temperature! AC demand will increase grid load."
            elif temperature < 30:
                warning = "Low temperature! Heating demand will increase grid load."

            return {
                "success": True,
                "temperature": temperature,
                "warning": warning,
                **result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_scenario(self, scenario: str) -> dict:
        """Run a predefined test scenario"""
        if not self.scenario_controller:
            return {"success": False, "error": "Scenario controller not available"}

        try:
            result = self.scenario_controller.run_scenario(scenario)
            return {"success": True, "scenario": scenario, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # EV CONFIGURATION
    # =========================================================================

    def _configure_ev(self, ev_percentage: int = 70,
                      battery_min_soc: int = 20,
                      battery_max_soc: int = 90) -> dict:
        """Configure EV parameters"""
        ev_percentage = max(0, min(100, ev_percentage))
        battery_min_soc = max(1, min(100, battery_min_soc))
        battery_max_soc = max(1, min(100, battery_max_soc))
        if battery_min_soc >= battery_max_soc:
            battery_min_soc = battery_max_soc - 1

        # Update global config
        self.current_ev_config.update({
            'ev_percentage': ev_percentage,
            'battery_min_soc': battery_min_soc,
            'battery_max_soc': battery_max_soc,
            'updated_at': datetime.now().isoformat()
        })

        # Update SUMO manager if running
        if self.sumo_manager and self.sumo_manager.running:
            self.sumo_manager.ev_percentage = ev_percentage / 100
            self.sumo_manager.battery_min_soc = battery_min_soc / 100
            self.sumo_manager.battery_max_soc = battery_max_soc / 100

        return {
            "success": True,
            "ev_percentage": ev_percentage,
            "battery_min_soc": battery_min_soc,
            "battery_max_soc": battery_max_soc,
        }

    # =========================================================================
    # STATUS & QUERIES
    # =========================================================================

    def _get_system_status(self) -> dict:
        """Get comprehensive system status"""
        try:
            substations = {}
            failed_list = []
            for name, sub in self.integrated_system.substations.items():
                operational = sub.get('operational', True)
                substations[name] = {
                    "operational": operational,
                    "load_mw": round(sub.get('load_mw', 0), 1),
                    "capacity_mva": sub.get('capacity_mva', 0),
                }
                if not operational:
                    failed_list.append(name)

            vehicle_stats = {}
            if self.system_state.get('sumo_running') and self.sumo_manager.running:
                vehicles = self.sumo_manager.get_vehicle_positions_for_visualization()
                vehicle_stats = {
                    "total": len(vehicles),
                    "evs": sum(1 for v in vehicles if v.get('is_ev')),
                    "charging": sum(1 for v in vehicles if v.get('is_charging')),
                }

            return {
                "success": True,
                "substations_online": len(self.integrated_system.substations) - len(failed_list),
                "substations_total": len(self.integrated_system.substations),
                "failed_substations": failed_list,
                "substations": substations,
                "sumo_running": self.system_state.get('sumo_running', False),
                "simulation_speed": self.system_state.get('simulation_speed', 1.0),
                "vehicles": vehicle_stats,
                "ev_stations": len(self.integrated_system.ev_stations),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_scenario_status(self) -> dict:
        """Get current scenario state"""
        if not self.scenario_controller:
            return {"success": False, "error": "Scenario controller not available"}
        try:
            status = self.scenario_controller.get_system_status()
            return {"success": True, **status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_substation_details(self, substation: str) -> dict:
        """Get detailed info about a specific substation"""
        if substation not in self.integrated_system.substations:
            available = list(self.integrated_system.substations.keys())
            return {"success": False, "error": f"Substation '{substation}' not found. Available: {available}"}

        sub = self.integrated_system.substations[substation]

        # Find connected EV stations
        connected_ev = []
        for ev_id, ev_data in self.integrated_system.ev_stations.items():
            if ev_data.get('substation') == substation:
                connected_ev.append({
                    "id": ev_id,
                    "name": ev_data.get('name', ev_id),
                    "operational": ev_data.get('operational', True),
                    "chargers": ev_data.get('chargers', 0)
                })

        # Find connected traffic lights
        connected_lights = sum(
            1 for tl in self.integrated_system.traffic_lights.values()
            if tl.get('substation') == substation
        )

        return {
            "success": True,
            "name": substation,
            "operational": sub.get('operational', True),
            "load_mw": round(sub.get('load_mw', 0), 1),
            "capacity_mva": sub.get('capacity_mva', 0),
            "location": sub.get('coords', sub.get('location', [])),
            "connected_ev_stations": connected_ev,
            "connected_traffic_lights": connected_lights,
            "v2g_active": substation in self.v2g_manager.get_v2g_status().get('substations_with_v2g', [])
        }

    def _get_load_forecast(self, hours: int = 6) -> dict:
        """Get load forecast"""
        if not self.scenario_controller:
            return {"success": False, "error": "Scenario controller not available"}
        try:
            forecast = self.scenario_controller.get_load_forecast(hours)
            return {"success": True, "hours": hours, "forecast": forecast}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MAP CONTROL
    # =========================================================================

    # Known locations for map focus
    LOCATIONS = {
        'times square': {'name': 'Times Square', 'coords': [-73.9857, 40.7580], 'zoom': 17},
        'penn station': {'name': 'Penn Station', 'coords': [-73.9937, 40.7505], 'zoom': 17},
        'grand central': {'name': 'Grand Central', 'coords': [-73.9772, 40.7527], 'zoom': 17},
        'columbus circle': {'name': 'Columbus Circle', 'coords': [-73.9819, 40.7681], 'zoom': 17},
        'union square': {'name': 'Union Square', 'coords': [-73.9903, 40.7359], 'zoom': 17},
        'washington square': {'name': 'Washington Square', 'coords': [-73.9973, 40.7308], 'zoom': 17},
        'brooklyn bridge': {'name': 'Brooklyn Bridge', 'coords': [-73.9969, 40.7061], 'zoom': 16},
        'wall street': {'name': 'Wall Street', 'coords': [-74.0090, 40.7068], 'zoom': 17},
        'central park': {'name': 'Central Park', 'coords': [-73.9654, 40.7829], 'zoom': 14},
        'manhattan': {'name': 'Manhattan', 'coords': [-73.9712, 40.7831], 'zoom': 12},
        'murray hill': {'name': 'Murray Hill', 'coords': [-73.9785, 40.7488], 'zoom': 17},
        'turtle bay': {'name': 'Turtle Bay', 'coords': [-73.9680, 40.7527], 'zoom': 17},
        'hells kitchen': {"name": "Hell's Kitchen", 'coords': [-73.9934, 40.7638], 'zoom': 17},
        "hell's kitchen": {"name": "Hell's Kitchen", 'coords': [-73.9934, 40.7638], 'zoom': 17},
        'midtown east': {'name': 'Midtown East', 'coords': [-73.9712, 40.7551], 'zoom': 17},
        'midtown': {'name': 'Midtown', 'coords': [-73.9845, 40.7549], 'zoom': 15},
        'upper east': {'name': 'Upper East Side', 'coords': [-73.9565, 40.7736], 'zoom': 15},
    }

    def _focus_map(self, location: str) -> dict:
        """Focus map on a location"""
        loc_key = location.lower().strip()
        loc_data = self.LOCATIONS.get(loc_key)

        # Also check substations
        if not loc_data:
            for name, sub in self.integrated_system.substations.items():
                if name.lower() == loc_key or loc_key in name.lower():
                    coords = sub.get('coords', sub.get('location', []))
                    loc_data = {'name': name, 'coords': coords, 'zoom': 17}
                    break

        if not loc_data:
            available = list(self.LOCATIONS.keys()) + list(self.integrated_system.substations.keys())
            return {"success": False, "error": f"Location '{location}' not found. Try: {', '.join(available[:10])}"}

        return {
            "success": True,
            "location": loc_data['name'],
            "map_action": {
                "type": "focus_and_highlight",
                "location": loc_data['name'],
                "name": loc_data['name'],
                "coordinates": loc_data['coords'],
                "zoom": loc_data.get('zoom', 17),
                "highlight": True,
                "showConnections": True
            }
        }

    # =========================================================================
    # TEST SCENARIOS
    # =========================================================================

    def _run_ev_rush_test(self) -> dict:
        """Run EV rush hour test"""
        if not self.system_state.get('sumo_running'):
            return {"success": False, "error": "Simulation must be running first"}
        try:
            count = 30
            if self.vehicle_spawn_queue is not None:
                self.vehicle_spawn_queue.append({'count': count, 'force_low_battery': True})
            return {"success": True, "message": f"EV rush test started — spawning {count} low-battery EVs"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_v2g_test(self) -> dict:
        """Run V2G test scenario"""
        # Pick a substation to fail
        target = None
        for name, sub in self.integrated_system.substations.items():
            if sub.get('operational', True):
                target = name
                break

        if not target:
            return {"success": False, "error": "No operational substations to test with"}

        # Fail it
        fail_result = self._fail_substation(target)
        if not fail_result.get('success'):
            return fail_result

        # Enable V2G
        v2g_result = self._enable_v2g(target)

        return {
            "success": True,
            "test_substation": target,
            "failure_result": fail_result,
            "v2g_result": v2g_result,
            "message": f"V2G test started: {target} failed and V2G enabled. Monitor V2G status for restoration progress."
        }
