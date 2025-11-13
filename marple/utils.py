import os
import tempfile


def to_hex(data):
    out_str = ""
    for each_byte in data:
        out_str += "{:02x}".format(each_byte)
    return out_str


def export_file_to_temp(file_object, temp_base_dir=None, maintain_structure=True):
    """
    Export a file from a disk image to a temporary directory.

    Args:
        file_object: FileItem object from disk image
        temp_base_dir: Base directory for temp exports. If None, uses system temp dir
        maintain_structure: If True, maintains the subfolder structure from the disk image

    Returns:
        str: Full path to the exported file

    Example:
        # For a file at '/Windows/System32/config/SAM'
        # Returns: '/tmp/mdp_export_xyz/Windows/System32/config/SAM'
        temp_path = export_file_to_temp(file_obj)
    """
    # Create base temp directory if not provided
    if temp_base_dir is None:
        temp_base_dir = tempfile.mkdtemp(prefix='mdp_export_')
    elif not os.path.exists(temp_base_dir):
        os.makedirs(temp_base_dir, exist_ok=True)

    if maintain_structure:
        # Normalize the path: remove leading slashes and convert to OS-appropriate separators
        relative_path = file_object.full_path.lstrip('/')
        # Replace any path separators with OS-appropriate ones
        relative_path = relative_path.replace('\\', os.sep).replace('/', os.sep)

        # Construct full export path
        export_path = os.path.join(temp_base_dir, relative_path)

        # Create parent directories if they don't exist
        export_dir = os.path.dirname(export_path)
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)
    else:
        # Just use the filename without directory structure
        filename = os.path.basename(file_object.full_path)
        export_path = os.path.join(temp_base_dir, filename)

    # Write the file
    with open(export_path, 'wb') as f:
        f.write(file_object.read())

    return export_path


def export_folder_to_temp(folder_path, file_list, temp_base_dir=None):
    """
    Export all files from a specific folder path recursively to a temporary directory.

    Args:
        folder_path: Folder path to export (e.g., '/Windows/System32' or 'Windows\\System32')
        file_list: List of FileItem objects from disk image
        temp_base_dir: Base directory for temp exports. If None, uses system temp dir

    Returns:
        dict: Dictionary with:
            - 'temp_dir': Base temporary directory path
            - 'exported_files': List of exported file paths
            - 'file_count': Number of files exported

    Example:
        # Export all files under /Windows/System32
        result = export_folder_to_temp('/Windows/System32', disk_image.files)
        # Returns: {
        #     'temp_dir': '/tmp/mdp_export_xyz',
        #     'exported_files': ['/tmp/mdp_export_xyz/Windows/System32/config/SAM', ...],
        #     'file_count': 42
        # }
    """
    import re

    # Create base temp directory if not provided
    if temp_base_dir is None:
        temp_base_dir = tempfile.mkdtemp(prefix='mdp_export_')
    elif not os.path.exists(temp_base_dir):
        os.makedirs(temp_base_dir, exist_ok=True)

    # Normalize the folder path for matching (handle both forward and backward slashes)
    normalized_folder = folder_path.replace('\\', '/').strip('/')

    # Build regex pattern to match folder and all subfolders
    # Match patterns:
    # - /folder, /folder/, /folder/anything
    # - P_123456/folder, P_123456/folder/, P_123456/folder/anything (with partition prefix)
    pattern = re.compile(f'^(P_\\d+/)?/?{re.escape(normalized_folder)}(/.*)?$', re.IGNORECASE)

    exported_files = []

    for file_obj in file_list:
        # Normalize file path for comparison
        normalized_file_path = file_obj.full_path.replace('\\', '/')

        # Check if file is in the target folder or subfolder
        if pattern.match(normalized_file_path):
            try:
                export_path = export_file_to_temp(file_obj, temp_base_dir=temp_base_dir, maintain_structure=True)
                exported_files.append(export_path)
            except Exception as e:
                print(f"Warning: Failed to export {file_obj.full_path}: {e}")
                continue

    return {
        'temp_dir': temp_base_dir,
        'exported_files': exported_files,
        'file_count': len(exported_files)
    }


