import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_fathomnet_csv import convert_dataset_to_csv, load_json_file, parse_args

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "input"


class FathomNetCsvConversionTests(unittest.TestCase):
    def test_core_json_fields_only(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "core_output.csv"
            row_count = convert_dataset_to_csv(dataset, output_path)

            self.assertEqual(row_count, 4)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 4)
            self.assertEqual(set(rows[0].keys()), {"concept", "image_url", "x", "y", "width", "height"})
            self.assertEqual(rows[0]["concept"], "Acanthaster planci")
            self.assertEqual(rows[0]["image_url"], "")
            self.assertEqual(rows[0]["x"], "12")
            self.assertEqual(rows[0]["y"], "34")
            self.assertEqual(rows[0]["width"], "45")
            self.assertEqual(rows[0]["height"], "67")

    def test_optional_metadata_csvs_are_merged(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")
        image_metadata_path = EXAMPLES_DIR / "image_metadata.csv"
        object_metadata_path = EXAMPLES_DIR / "object_metadata.csv"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "optional_output.csv"
            row_count = convert_dataset_to_csv(
                dataset,
                output_path,
                image_metadata_path=image_metadata_path,
                object_metadata_path=object_metadata_path,
            )

            self.assertEqual(row_count, 4)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["image_url"], "https://example.com/images/example_001.jpg")
            self.assertEqual(rows[0]["latitude"], "-64.1")
            self.assertEqual(rows[0]["longitude"], "12.3")
            self.assertEqual(rows[0]["timestamp"], "2023-01-01T12:34:56Z")
            self.assertEqual(rows[0]["depth"], "120")
            self.assertEqual(rows[0]["temperature"], "4.5")
            self.assertEqual(rows[0]["groupof"], "true")
            self.assertEqual(rows[0]["occluded"], "false")
            self.assertEqual(rows[0]["userdefinedkey"], "custom-tag-1")
            self.assertEqual(rows[1]["groupof"], "false")
            self.assertEqual(rows[1]["truncated"], "true")
            self.assertEqual(rows[2]["image_url"], "https://example.com/images/example_002.jpg")
            self.assertEqual(rows[2]["imagingtype"], "video")
            self.assertEqual(rows[2]["observer"], "observer_02")
            self.assertEqual(rows[3]["userdefinedkey"], "custom-tag-4")

    def test_output_csv_is_formatted_for_all_supported_fields(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")
        image_metadata_path = EXAMPLES_DIR / "image_metadata.csv"
        object_metadata_path = EXAMPLES_DIR / "object_metadata.csv"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "formatted_output.csv"
            convert_dataset_to_csv(
                dataset,
                output_path,
                image_metadata_path=image_metadata_path,
                object_metadata_path=object_metadata_path,
            )

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)

            expected_fieldnames = [
                "concept",
                "image_url",
                "x",
                "y",
                "width",
                "height",
                "latitude",
                "longitude",
                "timestamp",
                "depth",
                "temperature",
                "imagingtype",
                "observer",
                "oxygen",
                "pressure",
                "salinity",
                "groupof",
                "occluded",
                "truncated",
                "userdefinedkey",
            ]

            self.assertEqual(fieldnames, expected_fieldnames)
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(set(row.keys()), set(expected_fieldnames))
                self.assertTrue(row["concept"])
                self.assertTrue(row["image_url"] in {"", "https://example.com/images/example_001.jpg", "https://example.com/images/example_002.jpg", "https://example.com/images/example_003.jpg"})
                self.assertTrue(row["x"])
                self.assertTrue(row["y"])
                self.assertTrue(row["width"])
                self.assertTrue(row["height"])

    def test_derive_occlusion_single_flag_accepts_optional_threshold(self):
        with patch.object(sys, "argv", [
            "create_fathomnet_csv.py",
            "--input",
            "dataset.json",
            "--derive-occlusion",
        ]):
            args = parse_args()
            self.assertEqual(args.derive_occlusion, 0.5)
            self.assertEqual(args.occlusion_threshold, 0.5)

        with patch.object(sys, "argv", [
            "create_fathomnet_csv.py",
            "--input",
            "dataset.json",
            "--derive-occlusion",
            "0.75",
        ]):
            args = parse_args()
            self.assertEqual(args.derive_occlusion, 0.75)
            self.assertEqual(args.occlusion_threshold, 0.5)

    def test_derive_occlusion_from_box_overlap(self):
        dataset = {
            "images": [{"id": 1, "file_name": "example_001.jpg"}],
            "categories": [{"id": 10, "name": "Acanthaster planci"}],
            "annotations": [
                {"id": 101, "image_id": 1, "category_id": 10, "bbox": [0, 0, 10, 10]},
                {"id": 102, "image_id": 1, "category_id": 10, "bbox": [0, 0, 10, 10]},
                {"id": 103, "image_id": 1, "category_id": 10, "bbox": [50, 50, 10, 10]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "derived_occlusion.csv"
            convert_dataset_to_csv(dataset, output_path, derive_occlusion=True)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["occluded"], "true")
            self.assertEqual(rows[1]["occluded"], "true")
            self.assertEqual(rows[2]["occluded"], "false")

            output_path_2 = Path(tmp_dir) / "derived_occlusion_threshold.csv"
            convert_dataset_to_csv(dataset, output_path_2, derive_occlusion=True, occlusion_threshold=0.75)

            with output_path_2.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["occluded"], "true")
            self.assertEqual(rows[1]["occluded"], "true")
            self.assertEqual(rows[2]["occluded"], "false")

            object_metadata_path = Path(tmp_dir) / "object_metadata.csv"
            object_metadata_path.write_text("annotation_id,occluded\n101,false\n", encoding="utf-8")
            convert_dataset_to_csv(
                dataset,
                output_path,
                object_metadata_path=object_metadata_path,
                derive_occlusion=True,
            )

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["occluded"], "false")


if __name__ == "__main__":
    unittest.main()
