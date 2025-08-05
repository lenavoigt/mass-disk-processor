# Mass Disk Processor

The Mass Disk Processor (MDP) is a tool that automates the collection of metrics from large sets of disk images by running code and programs against disk image datasets and summarising the results.

MDP was created in the scope of our 📄 [academic paper](https://www.sciencedirect.com/science/article/pii/S2666281725000137) that was presented at [DFRWS EU 2025](https://dfrws.org/conferences/dfrws-eu-2025/). Our paper can be cited as:
> Voigt, L., Freiling, F., & Hargreaves, C.J. (2025). A metrics-based look at disk images: Insights and applications. Forensic Science International: Digital Investigation, 52, 301874. https://doi.org/10.1016/j.fsidi.2025.301874

In our paper, we collected metrics for publicly available, synthetic, scenario-based disk images. You can find a list of disk images considered, a metric summary table as well as individual datasheets for the disk images in [our data repository](https://github.com/lenavoigt/mass-disk-processor-data).

Also, in [our FAUbox drive](https://faubox.rrze.uni-erlangen.de/getlink/fiSyw7S4EbaxZLqQgCArbQ/), we provide **Plaso timelines** for these disk images.

# Table of Contents:

This README is structured to guide you through:
1. [Run MDP](#1-run-mdp): How to execute the tool on disk image datasets
2. [Preparation](#2-preparation): Setting up the MDP Python environment, preparing the target disk image folder(s), configuring the project, selecting plugins, and (*optionally*) preparing separate environments for external tools (e.g., Plaso) executed by MDP plugins.
3. [Results](#3-results): Outputs produced by MDP produces and where they're stored 
4. [Creating New Plugins](#4-creating-new-plugins): How to write, register, and select your own plugins for an MDP metric collection
5. [Calling External Programs from Plugins](#5-calling-external-programs-from-plugins): How to use external tools (e.g., Plaso) within an MDP plugin



# 1. Run MDP

To retrieve metrics from disk image datasets using MDP, use the following command **in your project's virtual environment** (after following the steps outlined in [Preparation](#Preparation)):

```
$ python mdp.py target_folder_of_disk_images
```

We have provided two (very simple) test disks in the Testdisks/ folder. If you'd like to test running MDP, you can try:

```
$ python mdp.py TestDisks
```

You can also provide an absolute path to the target folder containing the disk image dataset.

# 2. Preparation

Before you can run MDP, you need to:

0. Set up a virtual environment and install the dependencies from `requirements.txt`.
1. Put your disk image dataset in the required folder structure.
2. Create a configuration file `config.py`. *(Optionally)* Modify the configuration.
3. Select the plugins you'd like to include in your metric collection.
4. *(Optionally)* Prepare a Plaso environment.

These steps are detailed below.

**Note**: MDP was developed and tested on macOS Sequoia and Ubuntu 22.04 using Python 3.10. The instructions below refer to this environment.

## 2.0. Virtual Environment Setup and Dependency Installation

We recommend setting up a virtual environment to use MDP and installing the dependencies with the following commands:

```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```
Alternatively, you can use an IDE (e.g. PyCharm), which can handle environment setup and dependency installation.

## 2.1. Required Folder Structure for the Disk Image Dataset

The target folder containing the disk images to be processed must follow this structure:
```
target_folder_of_disk_images/
│── folder_of_case-1/
│   ├── data/
│   │   └── disk_image.dd
│
│── folder_of_case-2/
│   ├── data/
│   │   ├── another_disk_image_1.e01
│   │   ├── another_disk_image_2.e01
│   │   └── ...
│
│── ...
```
Each case folder (folder_of_case-1, folder_of_case-2, etc.) must contain a data subfolder, which holds disk image files of type .dd or EWF (.e01, etc.).
*Note*: 
- Currently, MDP does not support split dd files. 
- MDP does support split EWF (.e01, .e02, etc.) files.

## 2.2. Creation and Modification of `config.py`

The file `config_example.py` is provided as a template. Before you can run MDP you need to copy it to `config.py`:
```
$ cp config/config_example.py config/config.py
```

Afterwards, the default configuration in `config.py` can be modified if you want to customize processing options. You can modify the following settings:
- Absolute path to a National Software Reference Library (NSRL) Reference Data Set (RDS): Without this option, the non-NSRL file count plugin is not available.
- Preprocessing options:
    - Enable/disable population of file signatures (True/False): Without this option, the file signature mismatch count plugin is not available.
    - Enable/disable file hash computation (True/False): Without this option, the non-NSRL file count plugin is not available.
    - Set maximum file size for hashing
- Parameters required for using Plaso (see below)

## 2.3. Selecting Plugins for an MDP Run

To control which plugins are executed during an MDP run, edit the `enabled_plugins` list in `config/plugin_config.py`. 

To exclude a plugin for a run, you can simply comment it out in the list:
```
enabled_plugins = [
    # "disk_size",    # currently disabled plugin
    "file_types",     # enabled plugin
    "chrome_history", # enabled plugin
    ...
]
```

Each string in this list should match a key from the `plugin_registry` dictionary in `plugin_registry.py`.

*Note:  Plugins are executed in the order they appear in this list.*

## 2.4. _(Optional)_ Enabling the Usage of External Tools (e.g., Plaso)

> ⚠️ The MDP Plaso plugin relies on commands that will only work on POSIX-based systems.

MDP plugins can use external tools to retrieve metrics. For some of these tools, it might be necessary to create a (preferably separate) virtual environment for the external tool. One currently implemented example for this is MDP's Plaso plugin.

In MDP's current version, to use Plaso, you need to configure it in a virtual environment and specify its path in the `config.py` file. In `config.py`, set the following two parameters:
- `path_to_venv_python`: Path to the virtual environment’s `python3` executable.
- `path_to_plaso_scripts`: Path to the Plaso scripts.

One way to do this is by setting up Plaso in a **separate environment within the MDP project** to avoid dependency conflicts:
```
$ python3 -m venv plaso-venv
$ source plaso-venv/bin/activate
$ pip install plaso
```
*Note: If you prefer, you can [install Plaso from source](https://github.com/log2timeline/plaso) instead of using pip.*

Then, you can set the following values in MDP's `config.py`:
```
path_to_venv_python = '<absolute-path-tp-MDP>/plaso-venv/bin/python3'
path_to_plaso_scripts = '<absolute-path-tp-MDP>/plaso-venv/lib/python3.10/site-packages/plaso/scripts'
```
*Note: If you're using a different Python version, adjust the path to match the version you're using.*

You can then activate the Plaso Plugin by uncommenting it in the `plugin_classes` list in `mdp.py`.

# 3. Results

MDP produces the following results:
1. In the MDP project root
   - `output/` folder is created (if it doesn't yet exist), containing a set of overall result files (with a timestamp) for each run:
     - `{timestamp}_summary_dict.json`: full plugin results of all disk images in dictionary form
     - `{timestamp}_data_table.tsv`: tabular summary with one row per disk image, including only the plugins flagged for inclusion in the summary table.
     - `{timestamp}.log`: corresponding log file.
2. Inside each case folder (containing a `data/` folder with disk images)
   - `results/` folder is created containing:
     - `results_<plugin-name>.txt`: detailed plugin result file per plugin (including plugin name, description, source file path, creation timestamp, result values)
3. For the Plaso plugin: `plaso-output/` subfolder is created in each case folder, containing several Plaso result files for each disk image in the case's `data/` folder.

# 4. Creating new Plugins

To create a new plugin it’s easiest to copy an existing one from the `mdp_plugins/` directory (e.g., `disk_size.py`) and adapt it to your needs.

To include the plugin in your metric collection runs, you need to:
1. **Create the new plugin**: Add the new file (e.g., `new_plugin.py`) to `mdp_plugins/`. Your plugin class should:
   - Inherit from `MDPPlugin`
   - Define the required class attributes:
     ```
      name = "new_plugin"
      description = "Short description of what this plugin does"
      expected_results = ["value_a", "value_b", ...]
      ``` 
   - Implement the `process_disk()` method, using:
     - `self.create_result(...)` to create an MDPResult object
     - `self.set_results(...)` or `self.set_result(...)` to set values for fields listed in `expected_results`
   
    Example Plugin:
    ```
    from mdp_lib.mdp_plugin import MDPPlugin 
    from mdp_lib.disk_image_info import TargetDiskImage
    
    class NewPlugin(MDPPlugin):
        name = "new_plugin"
        description = "This is an example plugin."
        expected_results = ["example_value"]
    
        def process_disk(self, target_disk_image: TargetDiskImage):
            result = self.create_result(target_disk_image)
            example_value = analyze_stuff(target_disk_image)   
            self.set_result(result, "example_value", example_value)
            return result
    ```

2. **Register the plugin in the `plugin_registry.py`**:
   - Import your plugin at the top (grouped by category)
   - Add it to the `plugin_registry` dictionary, e.g.:
     ```
      plugin_registry = {
         ...
         "new_plugin": new_plugin.NewPlugin,
      } 
      ``` 
3. **Enable the plugin for an MDP run**:  
   - In `config/plugin_config.py`, add the name of your plugin (as added to the plugin registry dict) to the `enabled_plugins` list: 
     ```
      enabled_plugins = [
        ...
        "new_plugin",
      ]
      ```
   - *Note: Plugins not listed in enabled_plugins will not run, even if they are imported and registered in the plugin registry*

> You should make sure that your plugin always returns the same result fields (returning None for each field where no value was retrieved). This ensures consistent column ordering across all disk image results. 
> This is achieved by defining the `expected_results` list in your plugin and using the base class’s result-handling methods (`create_result()`, `set_result()`, and `set_results()`) exclusively to initialize and populate result fields.

# 5. Calling External Programs from Plugins

It's also possible that a plugin invokes external tools and parses their output as part of the metric collection process.
The `mdp_plugins/external_program_demo.py` plugin demonstrates how to run a simple external command using Python’s subprocess module.
A more complex example is shown in `mdp_plugins/plaso.py`, where several external scripts from Plaso are executed (i.e., `log2timeline.py`, `psort.py`, and `pinfo.py`). In this plugin, the resulting logs and output files are stored and parsed to extract metric data.