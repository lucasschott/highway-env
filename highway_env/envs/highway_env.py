import numpy as np
from typing import Dict, Tuple
from gym.envs.registration import register

from highway_env import utils
from highway_env.envs.common.abstract import AbstractEnv
from highway_env.road.road import Road, RoadNetwork
from highway_env.vehicle.controller import MDPVehicle


class HighwayEnv(AbstractEnv):
    """
        A highway driving environment.

        The vehicle is driving on a straight highway with several lanes, and is rewarded for reaching a high speed,
        staying on the rightmost lanes and avoiding collisions.
    """

    RIGHT_LANE_REWARD: float = 0.1
    """ The reward received when driving on the right-most lanes, linearly mapped to zero for other lanes."""
    HIGH_SPEED_REWARD: float = 1
    """ The reward received when driving at full speed, linearly mapped to zero for lower speeds."""
    LANE_CHANGE_REWARD: float = -0
    """ The reward received at each lane change action."""

    def default_config(self) -> dict:
        config = super().default_config()
        config.update({
            "observation": {
                "type": "Kinematics"
            },
            "lanes_count": 4,
            "vehicles_count": 50,
            "duration": 40,  # [s]
            "initial_spacing": 50,
            "spacing": 30,
            "collision_reward": -1  # The reward received when colliding with a vehicle.
        })
        return config

    def reset(self) -> np.ndarray:
        self._create_road()
        self._create_vehicles()
        self.steps = 0
        return super().reset()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        self.steps += 1
        return super().step(action)

    def _create_road(self) -> None:
        """
            Create a road composed of straight adjacent lanes.
        """
        self.road = Road(network=RoadNetwork.straight_road_network(self.config["lanes_count"]),
                         np_random=self.np_random, record_history=self.config["show_trajectories"])

    def _create_vehicles(self):
        """
            Create some new random vehicles of a given type, and add them on the road.
        """
        self.vehicle = MDPVehicle.create_random(self.road, 25, spacing=self.config["initial_spacing"])
        self.road.vehicles.append(self.vehicle)

        vehicles_type = utils.class_from_path(self.config["other_vehicles_type"])
        for _ in range(self.config["vehicles_count"]):
            self.road.vehicles.append(vehicles_type.create_random(self.road, spacing=self.config["spacing"]))

    def _reward(self, action):
        """
        The reward is defined to foster driving at high speed, on the rightmost lanes, and to avoid collisions.
        :param action: the last action performed
        :return: the corresponding reward
        """
        crash_reward = - self.vehicle.crashed * self.HIGH_SPEED_REWARD
        speed_reward = self.HIGH_SPEED_REWARD * (self.vehicle.speed_index / (self.vehicle.SPEED_COUNT - 1))**2
        if crash_reward != 0:
            state_reward = crash_reward
        else:
            state_reward = speed_reward
        return utils.lmap(state_reward, [0,self.HIGH_SPEED_REWARD], [0, 1])


    def _is_terminal(self) -> bool:
        """
            The episode is over if the ego vehicle crashed or the time is out.
        """
        return self.vehicle.crashed# or self.steps >= self.config["duration"]

    def _cost(self, action: int) -> float:
        """
            The cost signal is the occurrence of collision
        """
        return float(self.vehicle.crashed)


register(
    id='highway-v0',
    entry_point='highway_env.envs:HighwayEnv',
)
