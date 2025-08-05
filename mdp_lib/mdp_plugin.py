import datetime
import pprint
from abc import ABC, abstractmethod
from typing import Any

from mdp_lib.disk_image_info import TargetDiskImage


class MDPResult(object):

    def __init__(self, source_file: str, plugin_name: str, description: str):
        self.source_file = source_file
        self.plugin_name = plugin_name
        self.desc = description
        self.results = {}
        self.include_in_data_table = True
        self.time_created = str(datetime.datetime.now())

    def __str__(self):
        output = {'results': self.results,
                  'source_file': self.source_file,
                  'plugin': self.plugin_name,
                  'description': self.desc,
                  'time_created': self.time_created}

        return "{}".format(pprint.pformat(output))


class MDPPlugin(ABC):
    name: str
    description: str
    expected_results: list[str]
    include_in_data_table: bool = True

    def __init__(self):
        if not hasattr(self, 'name') or not hasattr(self, 'description') or not hasattr(self, 'expected_results'):
            raise NotImplementedError("Plugin must define 'name', 'description', and 'expected_results'.")

    def create_result(self, target_disk_image: TargetDiskImage) -> MDPResult:
        """Initialize MDPResult"""

        res = MDPResult(
            source_file=target_disk_image.image_path,
            plugin_name=self.name,
            description=self.description
        )

        res.results = {result_key: None for result_key in self.expected_results}

        res.include_in_data_table = self.include_in_data_table

        return res

    def set_results(self, result_obj: MDPResult, values: dict[str, Any]):
        """Add values for multiple results in an MDPResult (matching the defined expected_results_list)"""
        for key, value in values.items():
            self.set_result(result_obj, key, value)

    def set_result(self, result_obj: MDPResult, key: str, value: Any):
        """Add a value for one result in an MDPResult (matching the defined expected_results_list)"""
        if key not in self.expected_results:
            raise ValueError(f"Unexpected result key '{key}' in plugin '{self.name}'")
        result_obj.results[key] = value

    @abstractmethod
    def process_disk(self, target_disk_image: TargetDiskImage) -> MDPResult | None:
        """
            Method *must* be implemented by each MDP Plugin.
            -> analyzes the given disk image and returns an MDP result (containing values for the plugin's expected results)

            Typical implementation could look like this:

                val_a = compute_something()
                val_b = compute_something_else()

                result = self.create_result(target_disk_image)
                self.set_results(result, {"a": val_a, "b": val_b})  # where the plugin's expected_results = ["a", "b"]

                return result

            Note:
                - You should always use self.create_result(...) to initialize the MDP result object.
                - For most plugins you should use self.set_results(...) or self.set_result(...) to populate the fields defined in the plugin's expected_results.
                    -> Exception being dynamic plugins (e.g., plaso plugin) that create their result list dynamically
            """
        pass
