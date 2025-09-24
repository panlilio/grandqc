#!/bin/bash

# Parse flags

usage() {
    echo "Usage: $0 -s <SOURCE_DIR> -d <DEST_DIR> [-f <FIC_DIR> ] [-t TISSUE_ONLY ] [-g NO_GEOJSON ] [-m QC_MPP_MODEL]" 1>&2;
}

FIC_DIR="$PWD"
GEOJSON=Y
QC_MPP_MODEL=1.5

while getopts ":s:d:f:tgm:" o; do
    case "${o}" in
        s)
            SRC_DIR=${OPTARG}
            ;;
        d)
            DEST_DIR=${OPTARG}
            ;;

        f)  FIC_DIR=${OPTARG}
            ;;

        t)
            TISSUE=true
            ;;

        g)  GEOJSON=N
            ;;
        
        m)  QC_MPP_MODEL=${OPTARG}
            ;;

        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

echo "Source directory: $SRC_DIR"
echo "Destination directory: $DEST_DIR"

if [ -z "${SRC_DIR}" ] || [ -z "${DEST_DIR}" ]; then
    usage
fi


echo "FIC directory: $FIC_DIR"

cd "$(dirname "$0")"

cd "01_WSI_inference_OPENSLIDE_QC/"

echo "$(date) : Starting tissue segmentation..."
python3 wsi_tis_detect.py --slide_folder "$SRC_DIR" --output_dir "$DEST_DIR" --fic_dir "$FIC_DIR"
echo "$(date) : Tissue segmentation completed."

if [ -z $TISSUE ]; then
    echo "$(date) : Starting quality control analysis..."
    python3 main.py --slide_folder "$SRC_DIR" --output_dir "$DEST_DIR" --fic_dir "$FIC_DIR" --create_geojson "$GEOJSON" --mpp_model "$QC_MPP_MODEL"
    echo "$(date) : Quality control analysis completed."
fi
