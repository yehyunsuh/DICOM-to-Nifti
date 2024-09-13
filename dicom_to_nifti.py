import os
import re
import csv
import pydicom
import argparse
import subprocess
import numpy as np
import nibabel as nib
from glob import glob
from tqdm import tqdm


# Function to convert DICOM files to a 3D numpy array
def dicom_to_numpy(dicom_file_paths):
    # Read the first DICOM file to get metadata and dimensions
    dicom_sample = pydicom.dcmread(dicom_file_paths[0])
    
    # Get image dimensions from the DICOM file
    dimensions = (int(dicom_sample.Rows), int(dicom_sample.Columns), len(dicom_file_paths))

    # Initialize an empty numpy array to hold the pixel data
    pixel_array = np.zeros(dimensions, dtype=dicom_sample.pixel_array.dtype)

    # Loop through the DICOM files and stack them into the numpy array
    for i, dicom_file_path in enumerate(dicom_file_paths):
        dicom = pydicom.dcmread(dicom_file_path)
        pixel_array[:, :, i] = dicom.pixel_array
    
    return pixel_array, dicom_sample


# Convert the numpy array to NIfTI and save it as a .nii.gz file
def save_as_nifti(pixel_array, dicom_sample, output_path):
    # Convert DICOM affine transformation to NIfTI affine matrix
    affine = np.eye(4)
    affine[0, 0] = float(dicom_sample.PixelSpacing[0])
    affine[1, 1] = float(dicom_sample.PixelSpacing[1])
    affine[2, 2] = float(dicom_sample.SliceThickness)

    # Create a NIfTI image
    nifti_img = nib.Nifti1Image(pixel_array, affine)

    # Save the NIfTI image
    nib.save(nifti_img, output_path)


def clear_cache():
    """Clears the Linux filesystem cache (PageCache, Dentries, and Inodes)"""
    # Sync to ensure all buffers are flushed
    subprocess.run(['sudo', 'sync'])
    
    # Clear PageCache, Dentries, and Inodes
    subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])
    # print("Cleared filesystem cache")


def dicom_to_nifti(args):
    # if error_log.txt already exists, remove it
    if os.path.exists('error_log.txt'):
        os.remove('error_log.txt')
        
    iterations = 0
    error_case_list = []
    patient_dirs = sorted(glob(f'{args.dicom_dir}/*'), key=lambda x: int(os.path.basename(x)))
    nifti_before = int(sorted(glob(f'{args.nifti_dir}/*'), key=lambda x: int(os.path.basename(x)))[-1].split('/')[-1])
    for patient_dir in tqdm(patient_dirs):
        if int(patient_dir.split('/')[-1]) < nifti_before:
            continue
        subject_dirs = sorted(glob(f'{patient_dir}/*'), key=lambda x: int(re.search(r'Subject_(\d+)', os.path.basename(x)).group(1)))
        for subject_dir in subject_dirs:
            session_dirs = sorted(glob(f'{subject_dir}/*'), key=lambda x: int(re.search(r'Session_(\d+)', os.path.basename(x)).group(1)))
            for session_dir in session_dirs:
                case_dirs = sorted(glob(f'{session_dir}/*'))
                for case_dir in case_dirs:
                    dicom_file_path_list = sorted(glob(f'{case_dir}/*.dcm'), key=lambda x: int(os.path.basename(x).split('.')[0]))
                    patient_num = patient_dir.split('/')[-1]
                    subject_num = subject_dir.split('/')[-1].split('_')[1]
                    session_num = session_dir.split('/')[-1].split('_')[1]
                    case_num = case_dir.split('/')[-1]
                    
                    nifti_file_name = f'{patient_num}_Subject{subject_num}_Session{session_num}_{case_num}.nii.gz'
                    os.makedirs(f'{args.nifti_dir}/{patient_num}', exist_ok=True)
                    nifti_save_path = f'{args.nifti_dir}/{patient_num}/{nifti_file_name}'

                    # if the NIfTI file already exists, skip this case
                    if os.path.exists(nifti_save_path):
                        print(f'NIfTI file already exists: {nifti_save_path}')
                    else:
                        try:
                            # Convert the DICOM files to a numpy array
                            pixel_array, dicom_sample = dicom_to_numpy(dicom_file_path_list)

                            # Save the numpy array as a NIfTI file
                            save_as_nifti(pixel_array, dicom_sample, nifti_save_path)
                            print(f'{iterations+1} Saved NIfTI file: {nifti_save_path}')
                            del pixel_array, dicom_sample
                            
                            # Clear cache after each case processing to free memory
                            clear_cache()
                            iterations += 1

                        except Exception as e:
                            # Save the error in a text file
                            print(f'Error processing {case_dir}: {str(e)}')
                            error_log_path = 'error_log.txt'
                            with open(error_log_path, 'a') as f:
                                f.write(f'Error processing {case_dir}: {str(e)}\n')
                            error_case_list.append(case_dir)
                    
                    if iterations == 50:
                        exit()
    
    # Save the error case list in csv file
    error_case_csv_path = 'error_case_list.csv'
    with open(error_case_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Case'])
        for case in error_case_list:
            writer.writerow([case])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert DICOM files to NIfTI format')
    parser.add_argument('--dicom_dir', type=str, help='Path to the directory containing DICOM files')
    parser.add_argument('--nifti_dir', type=str, help='Path to the directory to save NIfTI files')
    args = parser.parse_args()

    dicom_to_nifti(args)
