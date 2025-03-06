#!/bin/bash
# setting
SLIDE_FOLDER="/home/zhilong/dr_pusher/Projects/GrandQC/additional_step_geojson/test_WSIs/"
OUTPUT_DIR="/home/zhilong/dr_pusher/Projects/GrandQC/additional_step_geojson/test_output/"
QC_MPP_MODEL=1.5
CREATE_GEOJSON="Y"

python wsi_tis_detect.py --slide_folder "$SLIDE_FOLDER" --output_dir "$OUTPUT_DIR"

python main.py --slide_folder "$SLIDE_FOLDER" --output_dir "$OUTPUT_DIR" --create_geojson "$CREATE_GEOJSON" --mpp_model "$QC_MPP_MODEL"

echo "All processes completed!"
