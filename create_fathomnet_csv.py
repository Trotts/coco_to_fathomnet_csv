"""Create a CSV file to upload a COCO-formatted dataset to FathomNet.

This script expects a local COCO dataset JSON file and optional image/object
metadata CSV files. The final output CSV contains the required FathomNet fields
plus any optional metadata columns supplied in the CSV files.

The CSV output will contain the following base fields:

- concept: The name of the organism morphotype
- image_url: The URL of the image
- x: The x coordinate of the organism in the image
- y: The y coordinate of the organism in the image
- width: The width of the bounding box around the organism
- height: The height of the bounding box around the organism

The CSV output may also contain additional optional metadata columns.
Available optionals can be found at https://www.fathomnet.org/post/how-to-submit-localized-image-annotations-to-the-fathomnet-database

Image-level metadata can be supplied in a CSV file with columns as:
filename,url,latitude,longitude,timestamp,depth,temperature,...,

Object-level metadata can be supplied in a CSV file with columns as:
annotation_id,groupof,occluded,truncated,userdefinedkey,...,

Usage:
    python create_fathomnet_csv.py --input path/to/dataset.json --output path/to/output.csv --image-metadata-file path/to/image_metadata.csv --object-metadata-file path/to/object_metadata.csv
"""
import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterator

BASE_FIELDNAMES = [
    "concept",
    "image_url",
    "x",
    "y",
    "width",
    "height",
]

FIELD_ALIASES = {
    "image_url": "image_url",
    "imageurl": "image_url",
    "url": "image_url",
    "latitude": "latitude",
    "longitude": "longitude",
    "timestamp": "timestamp",
    "depth": "depth",
    "depthmeters": "depth",
    "depth_meters": "depth",
    "groupof": "groupof",
    "group_of": "groupof",
    "imagingtype": "imagingtype",
    "imaging_type": "imagingtype",
    "observer": "observer",
    "occluded": "occluded",
    "oxygen": "oxygen",
    "oxygenmll": "oxygen",
    "oxygen_ml_l": "oxygen",
    "o2": "oxygen",
    "pressure": "pressure",
    "pressuredbar": "pressure",
    "pressure_dbar": "pressure",
    "salinity": "salinity",
    "temperature": "temperature",
    "temperaturecelsius": "temperature",
    "temperature_celsius": "temperature",
    "truncated": "truncated",
    "userdefinedkey": "userdefinedkey",
    "user_defined_key": "userdefinedkey",
    "filename": "filename",
    "filename_": "filename",
    "image": "filename",
    "imagename": "filename",
    "annotationid": "annotationid",
    "annotation_id": "annotationid",
    "annotation": "annotationid",
    "object_id": "annotationid",
    "id": "annotationid",
}

EXCLUDED_METADATA_KEYS = {
    "filename",
    "image",
    "annotationid",
}


def load_json_file(path: str | Path) -> dict[str, Any]:
    """Load a local JSON file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonicalize_key(key: str) -> str:
    """Normalize a metadata key to a compare-friendly canonical form."""
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch == "_")
    normalized = normalized.replace("_", "")
    return FIELD_ALIASES.get(normalized, normalized)


class FathomNetCsvConverter:
    """Convert a COCO-style dataset JSON file into FathomNet CSV rows."""

    def __init__(
        self,
        dataset: dict[str, Any],
        image_metadata_path: str | Path | None = None,
        object_metadata_path: str | Path | None = None,
    ):
        self.dataset = dataset
        self.image_metadata_path = Path(image_metadata_path) if image_metadata_path else None
        self.object_metadata_path = Path(object_metadata_path) if object_metadata_path else None
        self.image_by_id = {image.get("id"): image for image in dataset.get("images", []) if "id" in image}
        self.category_by_id = {
            category.get("id"): category for category in dataset.get("categories", []) if "id" in category
        }
        self.image_metadata = self._load_image_metadata()
        self.object_metadata = self._load_object_metadata()
        self.optional_columns = self._discover_optional_columns()
        self.warned_missing_image_meta: set[str] = set()
        self.warned_missing_object_meta: set[str] = set()

    def _load_image_metadata(self) -> dict[str, dict[str, str]]:
        """Load image metadata keyed by filename from an image CSV file."""
        if self.image_metadata_path is None:
            return {}

        metadata: dict[str, dict[str, str]] = {}
        with self.image_metadata_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                filename = next((row.get(key) for key in ("filename", "file_name", "image", "image_name") if row.get(key)), None)
                if filename is None:
                    continue
                normalized_row: dict[str, str] = {}
                for key, value in row.items():
                    if key is None or value is None:
                        continue
                    canonical = canonicalize_key(key)
                    if canonical in EXCLUDED_METADATA_KEYS:
                        continue
                    if canonical and value not in ("", None):
                        normalized_row[canonical] = str(value).strip()
                metadata[str(filename).strip()] = normalized_row
        return metadata

    def _load_object_metadata(self) -> dict[str, dict[str, str]]:
        """Load object metadata keyed by annotation_id from an object CSV file."""
        if self.object_metadata_path is None:
            return {}

        metadata: dict[str, dict[str, str]] = {}
        with self.object_metadata_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                annotation_id = next(
                    (row.get(key) for key in ("annotation_id", "annotationid", "id", "object_id", "annotation")), None
                )
                if annotation_id is None:
                    continue
                normalized_row: dict[str, str] = {}
                for key, value in row.items():
                    if key is None or value is None:
                        continue
                    canonical = canonicalize_key(key)
                    if canonical in EXCLUDED_METADATA_KEYS:
                        continue
                    if canonical and value not in ("", None):
                        normalized_row[canonical] = str(value).strip()
                metadata[str(annotation_id).strip()] = normalized_row
        return metadata

    def _discover_optional_columns(self) -> list[str]:
        """Discover optional metadata columns from the supplied CSV metadata files."""
        columns: list[str] = []
        for metadata_map in (self.image_metadata, self.object_metadata):
            for row in metadata_map.values():
                for key in row:
                    if key in BASE_FIELDNAMES or key in columns or key in EXCLUDED_METADATA_KEYS:
                        continue
                    columns.append(key)
        return columns

    def _resolve_image_filename(self, image: dict[str, Any] | None) -> str | None:
        if image is None:
            return None
        filename = image.get("filename") or image.get("file_name") or image.get("image_name")
        return str(filename).strip() if filename else None

    def _resolve_image_metadata(self, image: dict[str, Any] | None) -> dict[str, str]:
        filename = self._resolve_image_filename(image)
        if filename is None:
            return {}
        metadata = self.image_metadata.get(filename, {})
        if self.image_metadata_path is not None and not metadata:
            warning_key = f"image:{filename}"
            if warning_key not in self.warned_missing_image_meta:
                print(f"Warning: no image metadata found for '{filename}'")
                self.warned_missing_image_meta.add(warning_key)
        return metadata

    def _resolve_object_metadata(self, annotation: dict[str, Any]) -> dict[str, str]:
        annotation_id = annotation.get("id") or annotation.get("annotation_id") or annotation.get("annotationid")
        if annotation_id is None:
            return {}
        metadata = self.object_metadata.get(str(annotation_id), {})
        if self.object_metadata_path is not None and not metadata:
            warning_key = f"object:{annotation_id}"
            if warning_key not in self.warned_missing_object_meta:
                print(f"Warning: no object metadata found for annotation '{annotation_id}'")
                self.warned_missing_object_meta.add(warning_key)
        return metadata

    def resolve_concept(self, category_id: Any) -> str:
        """Map a COCO category id to the concept label used by FathomNet."""
        category = self.category_by_id.get(category_id)
        if category is None:
            return ""
        return str(category.get("name", ""))

    def resolve_image_url(self, image: dict[str, Any] | None) -> str:
        """Return the image URL from image metadata CSV, if available."""
        image_meta = self._resolve_image_metadata(image)
        if "image_url" in image_meta:
            return str(image_meta["image_url"])
        return ""

    def resolve_latitude(self, image: dict[str, Any] | None) -> str:
        """Return the latitude from image metadata CSV, if available."""
        image_meta = self._resolve_image_metadata(image)
        if "latitude" in image_meta:
            return str(image_meta["latitude"])
        return ""

    def resolve_longitude(self, image: dict[str, Any] | None) -> str:
        """Return the longitude from image metadata CSV, if available."""
        image_meta = self._resolve_image_metadata(image)
        if "longitude" in image_meta:
            return str(image_meta["longitude"])
        return ""

    def resolve_timestamp(self, image: dict[str, Any] | None) -> str:
        """Return the timestamp from image metadata CSV, if available."""
        image_meta = self._resolve_image_metadata(image)
        if "timestamp" in image_meta:
            return str(image_meta["timestamp"])
        return ""

    def iter_rows(self) -> Iterator[dict[str, Any]]:
        """Yield one row per annotation in FathomNet CSV format."""
        for annotation in self.dataset.get("annotations", []):
            image_id = annotation.get("image_id")
            image = self.image_by_id.get(image_id)
            bbox = annotation.get("bbox") or [0, 0, 0, 0]

            if len(bbox) != 4:
                continue

            x, y, width, height = bbox
            image_meta = self._resolve_image_metadata(image)
            object_meta = self._resolve_object_metadata(annotation)
            merged_meta = {**image_meta, **object_meta}

            row: dict[str, Any] = {
                "concept": self.resolve_concept(annotation.get("category_id")),
                "image_url": self.resolve_image_url(image),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }

            for field in self.optional_columns:
                row[field] = merged_meta.get(field, "")

            yield row

    def write_csv(self, output_path: str | Path) -> int:
        """Write all rows to a CSV file and return the number of rows written."""
        rows = list(self.iter_rows())
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = BASE_FIELDNAMES + [field for field in self.optional_columns if field not in BASE_FIELDNAMES]

        with output_file.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return len(rows)


def convert_dataset_to_csv(
    dataset: dict[str, Any],
    output_path: str | Path,
    image_metadata_path: str | Path | None = None,
    object_metadata_path: str | Path | None = None,
) -> int:
    """Convert a COCO JSON payload into a FathomNet CSV file."""
    converter = FathomNetCsvConverter(
        dataset,
        image_metadata_path=image_metadata_path,
        object_metadata_path=object_metadata_path,
    )
    return converter.write_csv(output_path)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_output_dir = script_dir / "output"
    default_output_path = default_output_dir / "fathomnet_upload.csv"

    parser = argparse.ArgumentParser(
        description=(
            "Convert a COCO-formatted dataset JSON and optional metadata CSV files "
            "into a FathomNet CSV upload file."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the local COCO-formatted JSON file to convert.",
    )
    parser.add_argument(
        "--output",
        default=str(default_output_path),
        help="Destination CSV path. Defaults to a script-local output/fathomnet_upload.csv file.",
    )
    parser.add_argument(
        "--image-metadata-file",
        default=None,
        help=(
            "Optional CSV file with columns such as filename,url,latitude,longitude,timestamp,depth,... "
            "This file provides image-level metadata."
        ),
    )
    parser.add_argument(
        "--object-metadata-file",
        default=None,
        help=(
            "Optional CSV file with columns such as annotation_id,groupof,occluded,truncated,userdefinedkey,... "
            "This file provides object-level metadata."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_path = Path(args.output)
    if output_path.parent.exists() is False:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = load_json_file(args.input)
    row_count = convert_dataset_to_csv(
        dataset,
        output_path,
        image_metadata_path=args.image_metadata_file,
        object_metadata_path=args.object_metadata_file,
    )
    print(f"Wrote {row_count} rows to {output_path}")


if __name__ == "__main__":
    main()


