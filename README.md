# COCO to FathomNet Database CSV Converter

 Converts a local COCO-style JSON annotation file into the CSV format expected by [FathomNet Database](https://www.fathomnet.org/post/how-to-submit-localized-image-annotations-to-the-fathomnet-database), with optional image-level and object-level metadata from CSV files.

## Features

- Reads a local COCO JSON dataset
- Converts annotations to FathomNet Database-ready CSV rows
- Include optional image-level and object-level metadata through additional CSVs
- Writes output to a default `output/fathomnet_upload.csv` path or a custom destination

## Usage

```bash
python create_fathomnet_csv.py \
  --input /path/to/dataset.json \
  --output /path/to/output.csv \
  --image-metadata-file /path/to/image_metadata.csv \
  --object-metadata-file /path/to/object_metadata.csv \
  --derive-occlusion 0.5
```

## Inputs

### COCO JSON
The input JSON must be COCO-formatted and include at least:

- `images`
- `categories`
- `annotations`

### Image metadata CSV
A CSV file keyed by `filename`, for example:

```csv
filename,url,latitude,longitude,timestamp,depth,temperature
example_001.jpg,https://example.com/images/example_001.jpg,-64.1,12.3,2023-01-01T12:34:56Z,120,4.5
```

Image-level metadata FathomNet accepts is:
- `altitude` or `altitudemeters` or `altitude_meters`
- `depth` or `depthmeters` or `depth_meters`
- `imagingtype` or `imaging_type`
- `latitude`
- `longitude`
- `oxygen` or `oxygenmll` or `oxygen_ml_l` or `o2`
- `pressure` or `pressuredbar` or `pressure_dbar`
- `salinity`
- `temperature` or `temperaturecelsius` or `temperature_celsius`
- `timestamp`

### Object metadata CSV
A CSV file keyed by `annotation_id`, for example:

```csv
annotation_id,groupof,occluded,truncated,userdefinedkey
101,true,false,false,custom-tag-1
```

Object-level metadata FathomNet accepts is:
- `altconcept` or `alt_concept` or `concept2` or `class2` or `name2`
- `groupof` or `group_of`
- `observer`
- `occluded`
- `truncated`
- `userdefinedkey`

If you wish, `occluded` can be determined programmatically from the COCO JSON. This can be done by calling the `--derive-occlusion` flag, optionally with a float value between 0 and 1 as the threshold. The default is 0.5, meaning that if more than 50% of an object overlaps with another object, it will be marked as occluded. NOTE: If `occluded` is present in the object metadata CSV and the flag is set, the CSV values will take precedence.

## Output

The script writes a CSV with the required base columns:

- `concept`
- `image_url`
- `x`
- `y`
- `width`
- `height`

It also appends any additional metadata fields discovered in the CSV metadata files.

## Tests

Example fixtures are provided under `input/`. Tests can be found in `tests/` and ran with:

```bash
python -m unittest discover -s tests -v
```
