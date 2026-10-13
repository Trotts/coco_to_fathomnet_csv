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
  --object-metadata-file /path/to/object_metadata.csv
```

## Inputs

### COCO JSON
The input JSON must be COCO-formatted and include at least:

- `images`
- `categories`
- `annotations`

### Image metadata CSV
A CSV file keyed by image filename, for example:

```csv
filename,url,latitude,longitude,timestamp,depth,temperature
example_001.jpg,https://example.com/images/example_001.jpg,-64.1,12.3,2023-01-01T12:34:56Z,120,4.5
```

### Object metadata CSV
A CSV file keyed by annotation ID, for example:

```csv
annotation_id,groupof,occluded,truncated,userdefinedkey
101,true,false,false,custom-tag-1
```

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
