"""
Comments to version:
- Uses tissue maps from tissue detector. Therefore, slides should be processed by tissue detector firstly.
- Consider adding color schema if you use the tool for a new entity
"""
from wsi_colors import colors_QC7 as colors
import torch
import argparse
from openslide import open_slide
from PIL import Image
import os
from wsi_slide_info import slide_info
from wsi_process import slide_process_single, mask_to_geojson
from wsi_maps import make_overlay
import numpy as np
import timeit
import cv2
Image.MAX_IMAGE_PIXELS = 1000000000


# DEVICE
DEVICE = 'cuda:0'
'''
'cuda:0' - NVIDIA GPU card
'mps'    - APPLE Silicon
'''

# Input parameter
parser = argparse.ArgumentParser()
parser.add_argument('--slide_folder', dest='slide_folder', help='path to WSIs', type=str)
parser.add_argument('--output_dir', dest='output_dir', help='path to output folder', type=str)
parser.add_argument('--fic_dir', dest='fic_dir', help='path to FIC folder', type=str, default=None)
parser.add_argument('--create_geojson', dest='create_geojson', help='create geojson for QC or not', default="Y", type=str)
parser.add_argument('--start', dest='start', default=0,  help='start num of WSIs', type=int)
parser.add_argument('--mpp_model', dest='MPP_MODEL', default=1.5,
                    help='MPP of the training model, should only be 1.0, 1.5, 2.0', type=float)
parser.add_argument('--end', dest='end', default=-1, help='end num of WSIs', type=int)
parser.add_argument('--ol_factor', dest='ol_factor', default=10,
                    help='reduction factor of the overlay compared to dimensions of original WSI', type=int)

args = parser.parse_args()

MPP_MODEL = args.MPP_MODEL
start = args.start
end = args.end
create_geojson = args.create_geojson
SLIDE_DIR = args.slide_folder
OUTPUT_DIR = args.output_dir
FIC_DIR = args.fic_dir
OVERLAY_FACTOR = args.ol_factor

# MODEL(S)
MODEL_QC_DIR = './models/qc/'
if MPP_MODEL == 1.5:
    MODEL_QC_NAME = 'GrandQC_MPP15.pth'
elif MPP_MODEL == 1.0:
    MODEL_QC_NAME = 'GrandQC_MPP1.pth'
elif MPP_MODEL == 2.0:
    MODEL_QC_NAME = 'GrandQC_MPP2.pth'
else:
    raise Exception("mpp of the model can only be 1.0, 1.5, 2.0")
M_P_S_MODEL = 512
ENCODER_MODEL = 'timm-efficientnet-b0'
ENCODER_MODEL_WEIGHTS = 'imagenet'

# CLASSES
BACK_CLASS = 7

if end == -1:
    end = len(os.listdir(SLIDE_DIR))

if create_geojson == "Y":
    geojson_root = os.path.join(OUTPUT_DIR, "geojson_qc")
    os.makedirs(geojson_root, exist_ok=True)

case_name = os.path.basename(OUTPUT_DIR)
REPORT_FILE_NAME = f'report_{case_name}_' + str(start) + '_' + str(end)     # File name, ".txt" will be added in the end
REPORT_OUTPUT_DIR = OUTPUT_DIR # where to save the text report


# =============================================================================
# LOAD MODELS
# =============================================================================
model_prim = torch.load(MODEL_QC_DIR + MODEL_QC_NAME, map_location=DEVICE)

# ====================================================================
# PREPARE REPORT FILE, OUTPUT FOLDERS
# =============================================================================

# Prepare report file header
path_result = os.path.join(REPORT_OUTPUT_DIR, REPORT_FILE_NAME + "_stats_per_slide.txt")
output_header = "slide_name" + "\t" + "obj_power" + "\t" + "mpp" + "\t"
output_header = output_header + "patch_n_h_l0" + "\t" + "patch_n_w_l0" + "\t"
output_header = output_header + "patch_overall" + "\t"
output_header = output_header + "height" + "\t" + "width" + "\t"
output_header = output_header + "time"
output_header = output_header + "\n"
results = open(path_result, "a+")
results.write(output_header)
results.close()

maps_dir = os.path.join(OUTPUT_DIR, 'maps_qc')
overlay_dir = os.path.join(OUTPUT_DIR, 'overlays_qc')
mask_dir = os.path.join(OUTPUT_DIR, 'mask_qc')

try:
    os.mkdir(maps_dir)
    os.mkdir(overlay_dir)
    os.mkdir(mask_dir)
except Exception as e:
    print('The target folders are already there ..')

# ====================================================================
# MAIN SCRIPT
# =============================================================================

# Read in slide names
slide_names = sorted(os.listdir(SLIDE_DIR))
# Start analysis loop

for slide_name in slide_names[start:end]:
    if slide_name.split(".")[-1].lower() not in ['svs', 'tif', 'tiff', 'ndpi', 'vms', 'vmu', 'mrxs']:
        continue

    else:
#    try:
        # Register start time
        start = timeit.default_timer()

        print("")
        print("Processing:", slide_name)

        # Open slide
        path_slide = os.path.join(SLIDE_DIR, slide_name)
        slide = open_slide(path_slide)

        # GET SLIDE INFO
        p_s, patch_n_w_l0, patch_n_h_l0, mpp, w_l0, h_l0, obj_power = slide_info(slide, M_P_S_MODEL, MPP_MODEL, FIC_DIR, slide_name)

        # LOAD TISSUE DETECTION MAP
        tis_det_map = Image.open(os.path.join(OUTPUT_DIR, 'tis_det_mask', slide_name + '_MASK.png'))
        print("Tissue detection map opened")
        '''
        Tissue detection map is generated on MPP = 10
        This map is used for on-fly control of the necessity of model inference.
        Two variants: reduced version with perfect correlation or full version scaled to working MPP of the tumor detection model
        Classes: 0 - tissue, 1 - background
        '''

        tis_det_map_mpp = np.array(tis_det_map.resize((int(w_l0 * mpp / MPP_MODEL), int(h_l0 * mpp / MPP_MODEL)), Image.Resampling.LANCZOS))
        map, full_mask = slide_process_single(model_prim, tis_det_map_mpp, slide, patch_n_w_l0, patch_n_h_l0, p_s,
                                              M_P_S_MODEL, colors, ENCODER_MODEL,
                                              ENCODER_MODEL_WEIGHTS, DEVICE, BACK_CLASS, MPP_MODEL, mpp, w_l0, h_l0)

        # Timer stop
        stop = timeit.default_timer()

        map_path = os.path.join(maps_dir, slide_name + "_map_QC.png")
        map.save(map_path)

        mask_path = os.path.join(mask_dir, slide_name + "_mask.png")
        cv2.imwrite(mask_path, full_mask)
        if create_geojson == "Y":
            geojson_path = os.path.join(geojson_root, slide_name + '.geojson')
            factor = MPP_MODEL / mpp
            mask_to_geojson(mask_path, geojson_path, factor)

        del full_mask

        # =============================================================================
        # 8. MAKE AND SAVE OVERLAY for C8: HEATMAP ON REDUCED AND CROPPED SLIDE CLON
        # =============================================================================
        overlay = make_overlay(slide, map, p_s, patch_n_w_l0, patch_n_h_l0, OVERLAY_FACTOR)

        del map

        # Save overlaid image
        overlay_im = Image.fromarray(overlay)
        overlay_im_name = os.path.join(overlay_dir, slide_name + "_overlay_QC.jpg")
        overlay_im.save(overlay_im_name)

        del overlay

        # Write down per slide result
        # Basic data about slide (size, pixel size, objective power, height, width)
        output_temp = slide_name + "\t" + str(obj_power) + "\t" + str(mpp) + "\t"
        output_temp = output_temp + str(patch_n_h_l0) + "\t" + str(patch_n_w_l0) + "\t"
        output_temp = output_temp + str(patch_n_h_l0 * patch_n_w_l0) + "\t"
        output_temp = output_temp + str(patch_n_h_l0 * p_s) + "\t" + str(patch_n_w_l0 * p_s) + "\t"

        output_temp = output_temp + str(round((stop - start) / 60, 1))

        output_temp = output_temp + "\n"

        results = open(path_result, "a+")
        results.write(output_temp)
        results.close()
 #   except Exception as e:
 #       print(f"There was some problem with the slide. The error is: {e}")
