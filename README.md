# Mass Disk Processor

MDP is a tool that automates the collection of metrics from large sets of disk images by running code and programs 
against disk image datasets and summarising the results.

MDP will be presented at [DFRWS EU 2025](https://dfrws.org/conferences/dfrws-eu-2025/).

If you'd like to use MDP, please cite it as:
> Voigt, L., Freiling, F., & Hargreaves, C.J. (2025). A metrics-based look at disk images: Insights and applications. Forensic Science International: Digital Investigation, XX, 301874. https://doi.org/10.1016/j.fsidi.2025.301874

In our paper, we collected metrics for publicly available, synthetic, scenario-based disk images. You can find a list of disk images considered, a metric summary table as well as individual datasheets for the disk images [in our FAUbox drive](TODO).

In the drive, we also provide **Plaso timelines** for these disk images.

# Run MDP

To retrieve metrics from disk image datasets using MDP, use the following command:

```
mdp.py target_folder_of_disk_images
```

We have provided two (very simple) test disks in the Testdisks/ folder. If you'd like to test running MDP, you can try:

```
mdp.py Testdisks
```

You can also provide an absolute path to the target folder containing the disk image dataset.

# Preparation

Before you can run MDP you need to:

1. Put your disk image dataset in the required folder structure.
2. Create a config.py.
3. Optionally: Prepare a Plaso environment.

These steps are detailed below.

## Required Folder Structure for the Disk Image Dataset

The target folder needs to have a specific format. 

```
root_folder_supplied
- folder1
    - data
        - disk_image.dd
- folder2
    - data
        - another_disk_image_1.e01
        - another_disk_image_2.e01
        ...
...
```

## Modification of `config.py`

The file `config_example.py` is provided. Before you can run MDP you need to copy it to `config.py` and adjust the values.
You can select:
- a path to an National Software Reference Library (NSRL) Reference Data Set (RDS)
- preprocessing options: 
  - population of file signatures (True/False)
  - computation of file hashes (True/False), maximum file size to be hashed

## Enabling the Usage of Plaso

To use Plaso you will need to configure Plaso in a virtual environment, and provide in the `config.py` file where that environment is (`path_to_venv_python`) along with the Plaso scripts (`path_to_plaso_scripts`).

# Results

MDP produces the following results:
- `data_table.tsv` and `summary_dict.json` containing the results for each disk image in the dataset of any plugin flagged for inclusion in the summary.
- `results_<plugin-name>.txt` containing more detailed results (including plugin name, plugin description, full path of the source disk image file, and creation time) of each plugin within the disk image folders.


# Creating new Plugins

To create a new plugin it is best to copy one of the existing ones.

To include the plugin in your metric collection runs, in `mdp.py` you need to:
- import the new plugin 
- add it to the list named `plugin_classes`, referring to the name of the class within the plugin python file. 

> You should make sure that your plugins always returns the same result fields (returning None for each field where no value was retrieved).

# Specifying a Plugin Order for Metric Collection Runs

If you'd like to run MDP plugins in a specific oder, you need to specify the plugin order in the `plugin_order_config.py` (using the specified plugin names).

