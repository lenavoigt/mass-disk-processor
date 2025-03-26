# Mass Disk Processor

MDP is a tool that automates the collection of metrics from large sets of disk images by running code and programs against disk image datasets and summarising the results.

MDP will be presented at [DFRWS EU 2025](https://dfrws.org/conferences/dfrws-eu-2025/).

If you'd like to use MDP, please cite it as:
> Voigt, L., Freiling, F., & Hargreaves, C.J. (2025). A metrics-based look at disk images: Insights and applications. Forensic Science International: Digital Investigation, 52, 301874. https://doi.org/10.1016/j.fsidi.2025.301874

In our paper, we collected metrics for publicly available, synthetic, scenario-based disk images. You can find a list of disk images considered, a metric summary table as well as individual datasheets for the disk images in [our data repository](https://github.com/lenavoigt/mass-disk-processor-data).

Also, in [our FAUbox drive](https://faubox.rrze.uni-erlangen.de/getlink/fiSyw7S4EbaxZLqQgCArbQ/), we provide **Plaso timelines** for these disk images.

# Run MDP

To retrieve metrics from disk image datasets using MDP, use the following command in your project's virtual environment:

```
$ python mdp.py target_folder_of_disk_images
```

We have provided two (very simple) test disks in the Testdisks/ folder. If you'd like to test running MDP, you can try:

```
$ python mdp.py TestDisks
```

You can also provide an absolute path to the target folder containing the disk image dataset.

# Preparation

Before you can run MDP, you need to:

0. Set up a virtual environment and install the dependencies from `requirements.txt`.
1. Put your disk image dataset in the required folder structure.
2. Create a configuration file `config.py`. *(Optionally)* Modify the configuration.
3. *(Optionally)* Prepare a Plaso environment.

These steps are detailed below.

**Note**: MDP was developed and tested on Ubuntu 22.04 using Python 3.10. The instructions below refer to this environment.

## Virtual Environment Setup and Dependency Installation

We recommend setting up a virtual environment to use MDP and installing the dependencies with the following commands:

```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```
Alternatively, you can use an IDE (e.g. PyCharm), which can handle environment setup and dependency installation.

## Required Folder Structure for the Disk Image Dataset

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

## Creation and Modification of `config.py`

The file `config_example.py` is provided as a template. Before you can run MDP you need to copy it to `config.py`:
```
$ cp mdp_lib/config_example.py mdp_lib/config.py
```

Afterwards, the default configuration in `config.py` can be modified if you want to customize processing options. You can modify the following settings:
- Absolute path to a National Software Reference Library (NSRL) Reference Data Set (RDS): Without this option, the non-NSRL file count plugin is not available.
- Preprocessing options:
    - Enable/disable population of file signatures (True/False): Without this option, the file signature mismatch count plugin is not available.
    - Enable/disable file hash computation (True/False): Without this option, the non-NSRL file count plugin is not available.
    - Set maximum file size for hashing
- Parameters required for using Plaso (see below)

## Enabling the Usage of Plaso

In MDP's current version, to use Plaso, you need to configure it in a virtual environment and specify its path in the `config.py` file. In `config.py`, set the following two parameters:
- `path_to_venv_python`: Path to the virtual environment’s `activate` script.
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
path_to_venv_python = '<absolute-path-tp-MDP>/plaso-venv/bin/activate'
path_to_plaso_scripts = '<absolute-path-tp-MDP>/plaso-venv/lib/python3.10/site-packages/plaso/scripts'
```
*Note: If you're using a different Python version, adjust the path to match the version you're using.*

You can then activate the Plaso Plugin by uncommenting it in the `plugin_classes` list in `mdp.py`.

# Results

MDP produces the following results:
- `data_table.tsv` and `summary_dict.json` containing the results for each disk image in the dataset of any plugin flagged for inclusion in the summary.
- `results_<plugin-name>.txt` containing more detailed results (including plugin name, plugin description, full path of the source disk image file, and creation time) of each plugin within the disk image folders.

# Creating new Plugins

To create a new plugin it is best to copy one of the existing ones.

To include the plugin in your metric collection runs, in `mdp.py` you need to:
- import the new plugin 
- add it to the list named `plugin_classes`, referring to the name of the class within the plugin Python file. 

> You should make sure that your plugin always returns the same result fields (returning None for each field where no value was retrieved).

# Specifying a Plugin Order for Metric Collection Runs

If you'd like to run MDP plugins in a specific order, you need to specify the plugin order in the `plugin_order_config.py` (using the specified plugin names).

