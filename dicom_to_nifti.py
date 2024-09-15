import os
import re
import csv
import argparse
import subprocess

from glob import glob
from tqdm import tqdm


def clear_cache():
    """Clears the Linux filesystem cache (PageCache, Dentries, and Inodes)"""
    # Sync to ensure all buffers are flushed
    subprocess.run(['sudo', 'sync'])
    
    # Clear PageCache, Dentries, and Inodes
    subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])
    print("Cleared filesystem cache")


def dicom_to_nifti(args):
    # if error_log.txt already exists, remove it
    if os.path.exists('error_log.txt'):
        os.remove('error_log.txt')
        
    iterations = 0
    error_case_list = []
    patient_dirs = sorted(glob(f'{args.dicom_dir}/*'), key=lambda x: int(os.path.basename(x)))

    if len(glob(f'{args.nifti_dir}/*')) == 0:
        nifti_before = 0
    else:
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
                    patient_num = patient_dir.split('/')[-1]
                    subject_num = subject_dir.split('/')[-1].split('_')[1]
                    session_num = session_dir.split('/')[-1].split('_')[1]
                    case_num = case_dir.split('/')[-1]
                    
                    nifti_save_path = f'{args.nifti_dir}/{patient_num}'
                    os.makedirs(f'{nifti_save_path}', exist_ok=True)
                    nifti_file_name = f'{patient_num}_Subject{subject_num}_Session{session_num}_{case_num}'
                    nifti_file_path = f'{nifti_save_path}/{nifti_file_name}.nii.gz'

                    # if the NIfTI file already exists, skip this case
                    if os.path.exists(nifti_file_path):
                        print(f'NIfTI file already exists: {nifti_file_path}')
                    else:
                        try:
                            iterations += 1
                            subprocess.run(['dcm2niix', '-o', nifti_save_path, '-f', nifti_file_name, '-z', 'y', case_dir])

                        except Exception as e:
                            # Save the error in a text file
                            print(f'Error processing {case_dir}: {str(e)}')
                            error_log_path = 'error_log.txt'
                            with open(error_log_path, 'a') as f:
                                f.write(f'Error processing {case_dir}: {str(e)}\n')
                            error_case_list.append(case_dir)
                    
                    if iterations == 50:
                        # clear_cache()
                        iterations = 0
    
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
