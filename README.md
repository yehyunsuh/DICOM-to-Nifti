# DICOM-to-Nifti
```
conda create -n dicom_to_nifti -y
conda activate dicom_to_nifti
pip3 install nibabel pydicom numpy python-gdcm
python3 dicom_to_nifti.py --dicom_dir "path_to_dicom_directory" --nifti_dir "path_to_nifti_directory"
```