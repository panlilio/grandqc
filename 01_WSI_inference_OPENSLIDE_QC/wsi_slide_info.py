# EXTRACTION OF META-DATA FROM SLIDE

from PIL import Image
from wsi_stain_norm import standardizer
import numpy as np
from fic_parser import fic_parser
import os

def slide_info(slide, m_p_s, mpp_model, fic_dir=None, slide_name=""):
    # Objective power
    try:
        obj_power = slide.properties["openslide.objective-power"]
    except:
        obj_power = 99

    print(f"FIC_DIR: {fic_dir}, slide_name: {slide_name}")

    # Microne per pixel
    if "openslide.mpp-x" in slide.properties:
        mpp = round(float(slide.properties["openslide.mpp-x"]), 4)
    elif fic_dir is not None:
        matches = []
        for fic_name in os.listdir(fic_dir):
            if fic_name[-4:] == '.fic':
                k = next((i for i, (a,b) in enumerate(zip(slide_name,fic_name)) if a != b), None)
                if k is not None and k > 0:
                    matches.append((fic_name, k))
        if len(matches) > 0:
            k = max([m[1] for m in matches])
            fic_name = [m[0] for m in matches if m[1] == k][0]
            fic_path = os.path.join(fic_dir, fic_name)
            print("Matching FIC file found:", fic_path)
            mpp = fic_parser(fic_path)
        else:
            print("No matching FIC file found. Assuming mpp = 0.25")
            mpp = 0.25
    else:
        print("No metadata of microns per pixel found. Assuming mpp = 0.25")
        mpp = 0.25

    p_s = int(mpp_model / mpp * m_p_s)

    # Vendor
    vendor = slide.properties["openslide.vendor"]

    # Extract and save dimensions of level [0]
    dim_l0 = slide.level_dimensions[0]
    w_l0 = dim_l0[0]
    h_l0 = dim_l0[1]

    # Calculate number of patches to process
    patch_n_w_l0 = int(w_l0 / p_s)
    patch_n_h_l0 = int(h_l0 / p_s)

    # Number of levels
    num_level = slide.level_count

    # Level downsamples
    down_levels = slide.level_downsamples

    # Output BASIC DATA
    print("")
    print("Basic data about processed whole-slide image")
    print("")
    print("Vendor: ", vendor)
    print("Scan magnification: ", obj_power)
    print("Number of levels: ", num_level)
    print("Level downsamples: ", down_levels)
    print("Microns per pixel (slide):", mpp)
    print("Height: ", h_l0)
    print("Width: ", w_l0)
    print("Model patch size at slide MPP: ", p_s, "x", p_s)
    print("Width - number of patches: ", patch_n_w_l0)
    print("Height - number of patches: ", patch_n_h_l0)
    print("Overall number of patches / slide (without tissue detection): ", patch_n_w_l0 * patch_n_h_l0)

    return p_s, patch_n_w_l0, patch_n_h_l0, mpp, w_l0, h_l0, obj_power
